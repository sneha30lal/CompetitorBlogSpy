import hashlib

import httpx
from bs4 import BeautifulSoup


class DirectPageDetector:
    """Detects changes on a directly monitored web page."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def detect(self, page_url: str) -> dict:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "CompetitorBlogSpy/1.0"
                },
            ) as client:
                response = await client.get(page_url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove elements that normally do not represent article content.
            for element in soup(
                ["script", "style", "noscript", "iframe"]
            ):
                element.decompose()

            content = soup.get_text(" ", strip=True)

            content_hash = hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()

            return {
                "success": True,
                "url": page_url,
                "title": soup.title.get_text(strip=True)
                if soup.title
                else None,
                "content": content,
                "content_hash": content_hash,
                "error": None,
            }

        except httpx.HTTPError as exc:
            return {
                "success": False,
                "url": page_url,
                "title": None,
                "content": None,
                "content_hash": None,
                "error": str(exc),
            }

        except Exception as exc:
            return {
                "success": False,
                "url": page_url,
                "title": None,
                "content": None,
                "content_hash": None,
                "error": str(exc),
            }