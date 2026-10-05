import asyncio
import json
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import Article, MonitoringCheck, Website
from app.services.detectors.direct_page_detector import DirectPageDetector
from app.services.detectors.rss_detector import RSSDetector
from app.services.detectors.sitemap_detector import SitemapDetector
from app.services.extractor.article_extractor import ArticleExtractor


class MonitoringEngine:
    """Runs one monitoring check for a website."""

    def __init__(
        self,
        max_retries: int = 2,
        retry_delay_seconds: float = 2.0,
    ):
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        self.rss_detector = RSSDetector()
        self.sitemap_detector = SitemapDetector()
        self.direct_page_detector = DirectPageDetector()
        self.article_extractor = ArticleExtractor()

    async def check_website(
        self,
        db: Session,
        website: Website,
    ) -> MonitoringCheck:

        start_time = time.perf_counter()

        check = MonitoringCheck(
            website_id=website.id,
            checked_at=datetime.utcnow(),
            success=False,
            strategy_used=website.strategy,
            articles_found=0,
            new_articles=0,
            response_time_ms=0.0,
            error_message=None,
        )

        db.add(check)
        db.commit()
        db.refresh(check)

        try:

            # Direct-page monitoring needs content-hash based
            # change detection.
            if website.strategy == "direct_page":

                new_articles = await self._check_direct_page_with_hash(
                    db,
                    website,
                )

                check.articles_found = 1
                check.new_articles = new_articles
                check.success = True

                website.last_checked_at = datetime.utcnow()
                website.last_success_at = datetime.utcnow()
                website.last_error = None

            else:

                detected_items = await self._detect_with_retries(
                    website
                )

                check.articles_found = len(detected_items)

                # The first successful check establishes the existing
                # articles as the monitoring baseline. They are stored,
                # but they are not counted as newly detected articles.
                baseline = (
                    db.query(Article)
                    .filter(Article.website_id == website.id)
                    .count()
                    == 0
                )

                new_articles = 0

                for item in detected_items:

                    article_url = item.get("url")

                    if not article_url:
                        continue

                    existing = (
                        db.query(Article)
                        .filter(Article.url == article_url)
                        .first()
                    )

                    if existing:
                        continue

                    try:

                        extracted = await self.article_extractor.extract(
                            article_url
                        )

                        if extracted["success"]:

                            article = self._build_article(
                                website,
                                extracted,
                                item,
                            )

                            if baseline:
                                article.detection_delay_seconds = None
                            else:
                                new_articles += 1

                            db.add(article)

                    except Exception:
                        # One bad article must not stop
                        # monitoring of the entire website.
                        continue

                check.new_articles = new_articles
                check.success = True

                website.last_checked_at = datetime.utcnow()
                website.last_success_at = datetime.utcnow()
                website.last_error = None

        except Exception as exc:

            error_message = str(exc).strip()

            if not error_message:
                error_message = (
                    f"{type(exc).__name__}: monitoring check failed"
                )

            check.success = False
            check.error_message = error_message

            website.last_checked_at = datetime.utcnow()
            website.last_error = error_message

        finally:

            elapsed_ms = (
                time.perf_counter() - start_time
            ) * 1000

            check.response_time_ms = elapsed_ms

            db.commit()
            db.refresh(check)

        return check

    async def _check_direct_page_with_hash(
        self,
        db: Session,
        website: Website,
    ) -> int:

        result = await self._detect_direct_page_with_retries(
            website
        )

        current_hash = result["content_hash"]
        previous_hash = website.last_content_hash

        # Save the latest observed hash.
        website.last_content_hash = current_hash

        # First observation establishes the baseline.
        if previous_hash is None:

            extracted = await self._extract_direct_page_article(
                website.url
            )

            if not extracted["success"]:
                raise RuntimeError(
                    extracted["error"]
                    or "Direct-page article extraction failed"
                )

            existing = (
                db.query(Article)
                .filter(
                    Article.website_id == website.id,
                    Article.url == website.url,
                )
                .first()
            )

            if existing is None:

                article = self._build_article(
                    website,
                    extracted,
                    result,
                )

                # First observation is only the baseline.
                # It must not be counted as a newly detected article
                # and must not contribute a historical detection delay.
                article.detection_delay_seconds = None
                db.add(article)

                return 0

            return 0

        # No content change.
        if previous_hash == current_hash:
            return 0

        # Content changed.
        extracted = await self._extract_direct_page_article(
            website.url
        )

        if not extracted["success"]:
            raise RuntimeError(
                extracted["error"]
                or "Direct-page article extraction failed"
            )

        existing = (
            db.query(Article)
            .filter(
                Article.website_id == website.id,
                Article.url == website.url,
            )
            .first()
        )

        if existing is None:

            article = self._build_article(
                website,
                extracted,
                result,
            )

            db.add(article)

        else:

            # Article.url is globally unique, so a changed
            # direct page updates the existing article instead
            # of creating a duplicate row.
            existing.canonical_url = extracted.get(
                "canonical_url"
            )

            existing.title = (
                extracted.get("title")
                or "Untitled"
            )

            existing.author = extracted.get("author")
            existing.published_at = extracted.get(
                "published_at"
            )

            existing.detected_at = datetime.utcnow()
            if existing.published_at and existing.published_at <= existing.detected_at:
                existing.detection_delay_seconds = (
                    existing.detected_at - existing.published_at
                ).total_seconds()
            else:
                existing.detection_delay_seconds = None

            existing.body = extracted.get("body")

            existing.image_urls = json.dumps(
                extracted.get("image_urls", [])
            )

            existing.categories = json.dumps(
                extracted.get("categories", [])
            )

            existing.tags = json.dumps(
                extracted.get("tags", [])
            )

            existing.metadata_json = extracted.get(
                "metadata_json"
            )

        return 1

    async def _extract_direct_page_article(
        self,
        article_url: str,
    ) -> dict:

        return await self.article_extractor.extract(
            article_url
        )

    async def _detect_direct_page_with_retries(
        self,
        website: Website,
    ) -> dict:

        last_error = None

        for attempt in range(
            self.max_retries + 1
        ):

            try:

                result = await self.direct_page_detector.detect(
                    website.url
                )

                if not result["success"]:

                    raise RuntimeError(
                        result["error"]
                        or "Direct-page detection failed"
                    )

                return result

            except Exception as exc:

                last_error = exc

                if attempt >= self.max_retries:
                    break

                await asyncio.sleep(
                    self.retry_delay_seconds
                )

        raise last_error

    async def _detect_with_retries(
        self,
        website: Website,
    ) -> list[dict]:

        last_error = None

        for attempt in range(
            self.max_retries + 1
        ):

            try:

                return await self._detect(
                    website
                )

            except Exception as exc:

                last_error = exc

                if attempt >= self.max_retries:
                    break

                await asyncio.sleep(
                    self.retry_delay_seconds
                )

        raise last_error

    async def _detect(
        self,
        website: Website,
    ) -> list[dict]:

        if website.strategy == "rss":
            return await self._check_rss(website)

        if website.strategy == "sitemap":
            return await self._check_sitemap(website)

        if website.strategy == "direct_page":
            return await self._check_direct_page(website)

        raise ValueError(
            f"Unsupported monitoring strategy: "
            f"{website.strategy}"
        )

    async def _check_rss(
        self,
        website: Website,
    ) -> list[dict]:

        feed_url = (
            website.source_url
            or website.url
        )

        return self.rss_detector.detect(
            feed_url
        )

    async def _check_sitemap(
        self,
        website: Website,
    ) -> list[dict]:

        return await self.sitemap_detector.detect(
            website.source_url
            or website.url
        )

    async def _check_direct_page(
        self,
        website: Website,
    ) -> list[dict]:

        result = await self.direct_page_detector.detect(
            website.url
        )

        if not result["success"]:

            raise RuntimeError(
                result["error"]
                or "Direct-page detection failed"
            )

        return [
            {
                "url": website.url,
                "title": result["title"],
                "summary": result["content"],
            }
        ]

    @staticmethod
    def _build_article(
        website: Website,
        extracted: dict,
        detected_item: dict,
    ) -> Article:

        published_at = (
            extracted.get("published_at")
            or detected_item.get("published_at")
        )

        detected_at = datetime.utcnow()

        detection_delay = None

        if (
            published_at
            and published_at <= detected_at
        ):

            detection_delay = (
                detected_at - published_at
            ).total_seconds()

        return Article(
            website_id=website.id,
            url=extracted["url"],
            canonical_url=extracted.get(
                "canonical_url"
            ),
            title=(
                extracted.get("title")
                or detected_item.get("title")
                or "Untitled"
            ),
            author=extracted.get("author"),
            published_at=published_at,
            detected_at=detected_at,
            detection_delay_seconds=detection_delay,
            body=extracted.get("body"),
            image_urls=json.dumps(
                extracted.get(
                    "image_urls",
                    [],
                )
            ),
            categories=json.dumps(
                extracted.get(
                    "categories",
                    [],
                )
            ),
            tags=json.dumps(
                extracted.get(
                    "tags",
                    [],
                )
            ),
            metadata_json=extracted.get(
                "metadata_json"
            ),
        )