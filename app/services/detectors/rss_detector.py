from datetime import datetime, timezone

import feedparser


class RSSDetector:
    """Detects articles from RSS or Atom feeds."""

    def detect(self, feed_url: str) -> list[dict]:
        feed = feedparser.parse(feed_url)

        articles = []

        for entry in feed.entries:
            url = entry.get("link")

            if not url:
                continue

            published_at = self._get_published_time(entry)

            articles.append(
                {
                    "url": url,
                    "title": entry.get("title", "Untitled"),
                    "author": entry.get("author"),
                    "published_at": published_at,
                    "summary": entry.get("summary"),
                }
            )

        return articles

    @staticmethod
    def _get_published_time(entry) -> datetime | None:
        published = entry.get("published_parsed") or entry.get(
            "updated_parsed"
        )

        if not published:
            return None

        return datetime(
            published.tm_year,
            published.tm_mon,
            published.tm_mday,
            published.tm_hour,
            published.tm_min,
            published.tm_sec,
            tzinfo=timezone.utc,
        ).replace(tzinfo=None)