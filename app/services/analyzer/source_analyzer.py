from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class SourceAnalyzer:
    """Investigates a website and determines available monitoring sources."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def analyze(self, website_url: str) -> dict:
        website_url = website_url.rstrip("/")

        result = {
            "website_url": website_url,
            "rss_feeds": [],
            "sitemaps": [],
            "direct_page": website_url,
            "recommended_strategy": "direct_page",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "CompetitorBlogSpy/1.0"
                },
            ) as client:
                response = await client.get(website_url)
                response.raise_for_status()

                html = response.text

            soup = BeautifulSoup(html, "html.parser")

            # Look for RSS / Atom feeds declared in the page.
            for link in soup.find_all("link"):
                rel = link.get("rel", [])
                link_type = link.get("type", "")
                href = link.get("href")

                if not href:
                    continue

                if "alternate" in rel and link_type in {
                    "application/rss+xml",
                    "application/atom+xml",
                }:
                    feed_url = urljoin(website_url + "/", href)

                    if feed_url not in result["rss_feeds"]:
                        result["rss_feeds"].append(feed_url)

            # Check the conventional robots.txt file for sitemap declarations.
            parsed = urlparse(website_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = urljoin(base_url, "/robots.txt")

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={
                        "User-Agent": "CompetitorBlogSpy/1.0"
                    },
                ) as client:
                    robots_response = await client.get(robots_url)

                if robots_response.is_success:
                    for line in robots_response.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()

                            if sitemap_url and sitemap_url not in result["sitemaps"]:
                                result["sitemaps"].append(sitemap_url)

            except httpx.HTTPError:
                pass

            # Check the conventional /sitemap.xml location.
            conventional_sitemap = urljoin(base_url, "/sitemap.xml")

            if conventional_sitemap not in result["sitemaps"]:
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout,
                        follow_redirects=True,
                        headers={
                            "User-Agent": "CompetitorBlogSpy/1.0"
                        },
                    ) as client:
                        sitemap_response = await client.get(conventional_sitemap)

                    if sitemap_response.is_success:
                        content_type = sitemap_response.headers.get(
                            "content-type",
                            ""
                        ).lower()

                        if (
                            "xml" in content_type
                            or "<urlset" in sitemap_response.text.lower()
                            or "<sitemapindex" in sitemap_response.text.lower()
                        ):
                            result["sitemaps"].append(conventional_sitemap)

                except httpx.HTTPError:
                    pass

            # Select the preferred strategy.
            if result["rss_feeds"]:
                result["recommended_strategy"] = "rss"
            elif result["sitemaps"]:
                result["recommended_strategy"] = "sitemap"
            else:
                result["recommended_strategy"] = "direct_page"

            result["success"] = True
            result["error"] = None

        except httpx.HTTPError as exc:
            result["success"] = False
            result["error"] = str(exc)

        except Exception as exc:
            result["success"] = False
            result["error"] = str(exc)

        return result