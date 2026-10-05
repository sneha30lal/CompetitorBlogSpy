import json
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


class ArticleExtractor:
    """Extracts article information from an article webpage."""

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def extract(self, article_url: str) -> dict:
        try:
            async with httpx.AsyncClient(
    follow_redirects=True,
    timeout=self.timeout
) as client:
                response = await client.get(article_url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            canonical_url = self._extract_canonical(soup, article_url)
            title = self._extract_title(soup)
            author = self._extract_author(soup)
            published_at = self._extract_date(soup)
            body = self._extract_body(soup)
            images = self._extract_images(soup, article_url)
            categories = self._extract_categories(soup)
            tags = self._extract_tags(soup)
            metadata = self._extract_metadata(soup)

            return {
                "success": True,
                "url": article_url,
                "canonical_url": canonical_url,
                "title": title,
                "author": author,
                "published_at": published_at,
                "body": body,
                "image_urls": images,
                "categories": categories,
                "tags": tags,
                "metadata_json": json.dumps(metadata),
                "error": None,
            }

        except httpx.HTTPError as exc:
            return self._error_result(article_url, str(exc))

        except Exception as exc:
            return self._error_result(article_url, str(exc))

    @staticmethod
    def _extract_canonical(soup: BeautifulSoup, article_url: str) -> str:
        canonical = soup.find(
            "link",
            rel=lambda value: value and "canonical" in value
        )

        if canonical and canonical.get("href"):
            return urljoin(article_url, canonical["href"])

        return article_url

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        og_title = soup.find(
            "meta",
            property="og:title"
        )

        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        if soup.title:
            return soup.title.get_text(strip=True)

        heading = soup.find("h1")

        if heading:
            return heading.get_text(" ", strip=True)

        return None

    @staticmethod
    def _extract_author(soup: BeautifulSoup) -> str | None:
        author_meta = soup.find(
            "meta",
            attrs={"name": "author"}
        )

        if author_meta and author_meta.get("content"):
            return author_meta["content"].strip()

        author_element = soup.find(
            attrs={"class": lambda value: value and "author" in str(value).lower()}
        )

        if author_element:
            return author_element.get_text(" ", strip=True)

        return None

    @staticmethod
    def _extract_date(soup: BeautifulSoup) -> datetime | None:
        date_meta_names = [
            "article:published_time",
            "datePublished",
            "date",
            "pubdate",
        ]

        for meta_name in date_meta_names:
            element = soup.find(
                "meta",
                attrs={"property": meta_name}
            ) or soup.find(
                "meta",
                attrs={"name": meta_name}
            )

            if element and element.get("content"):
                parsed = ArticleExtractor._parse_date(
                    element["content"]
                )

                if parsed:
                    return parsed

        time_element = soup.find("time")

        if time_element:
            date_value = time_element.get("datetime")

            if date_value:
                parsed = ArticleExtractor._parse_date(date_value)

                if parsed:
                    return parsed

        return None

    @staticmethod
    def _parse_date(value: str) -> datetime | None:
        try:
            cleaned = value.strip().replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)

            if parsed.tzinfo:
                parsed = parsed.replace(tzinfo=None)

            return parsed

        except ValueError:
            return None

    @staticmethod
    def _extract_body(soup: BeautifulSoup) -> str | None:
        article = soup.find("article")

        if article:
            return article.get_text(" ", strip=True)

        paragraphs = soup.find_all("p")

        if paragraphs:
            return " ".join(
                paragraph.get_text(" ", strip=True)
                for paragraph in paragraphs
            )

        return None

    @staticmethod
    def _extract_images(
        soup: BeautifulSoup,
        article_url: str
    ) -> list[str]:
        images = []

        article = soup.find("article") or soup

        for image in article.find_all("img"):
            source = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-lazy-src")
            )

            if source:
                images.append(urljoin(article_url, source))

        return list(dict.fromkeys(images))

    @staticmethod
    def _extract_categories(soup: BeautifulSoup) -> list[str]:
        categories = []

        for element in soup.find_all(
            attrs={
                "class": lambda value:
                value and "categor" in str(value).lower()
            }
        ):
            value = element.get_text(" ", strip=True)

            if value:
                categories.append(value)

        return list(dict.fromkeys(categories))

    @staticmethod
    def _extract_tags(soup: BeautifulSoup) -> list[str]:
        tags = []

        # Common semantic tag containers
        selectors = [
            '[rel="tag"]',
            '.post-tags a',
            '.article-tags a',
            '.tags a',
            'a[aria-label*="tag" i]',
        ]

        for selector in selectors:
            for element in soup.select(selector):
                value = element.get_text(" ", strip=True)

                if value and len(value) <= 100:
                    tags.append(value)

        return list(dict.fromkeys(tags))

    @staticmethod
    def _extract_metadata(soup: BeautifulSoup) -> dict:
        metadata = {}

        for meta in soup.find_all("meta"):
            name = (
                meta.get("name")
                or meta.get("property")
                or meta.get("itemprop")
            )

            content = meta.get("content")

            if name and content:
                metadata[name] = content

        return metadata

    @staticmethod
    def _error_result(article_url: str, error: str) -> dict:
        return {
            "success": False,
            "url": article_url,
            "canonical_url": None,
            "title": None,
            "author": None,
            "published_at": None,
            "body": None,
            "image_urls": [],
            "categories": [],
            "tags": [],
            "metadata_json": None,
            "error": error,
        }