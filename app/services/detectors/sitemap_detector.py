import httpx
from lxml import etree


class SitemapDetector:
    """Detects article URLs from XML sitemaps and sitemap indexes."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def detect(self, sitemap_url: str) -> list[dict]:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "CompetitorBlogSpy/1.0"
            },
        ) as client:
            response = await client.get(sitemap_url)
            response.raise_for_status()

        root = etree.fromstring(response.content)
        root_tag = etree.QName(root).localname

        if root_tag == "sitemapindex":
            return await self._process_sitemap_index(root)

        if root_tag == "urlset":
            return self._process_urlset(root)

        raise ValueError(
            f"Unsupported sitemap XML root element: {root_tag}"
        )

    async def _process_sitemap_index(self, root) -> list[dict]:
        sitemap_urls = []

        for element in root:
            if etree.QName(element).localname != "sitemap":
                continue

            for child in element:
                if etree.QName(child).localname == "loc":
                    if child.text:
                        sitemap_urls.append(child.text.strip())

        articles = []

        for sitemap_url in sitemap_urls:
            articles.extend(
                await self._detect_child_sitemap(sitemap_url)
            )

        return articles

    async def _detect_child_sitemap(
        self,
        sitemap_url: str
    ) -> list[dict]:

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "CompetitorBlogSpy/1.0"
            },
        ) as client:
            response = await client.get(sitemap_url)
            response.raise_for_status()

        root = etree.fromstring(response.content)

        if etree.QName(root).localname == "urlset":
            return self._process_urlset(root)

        raise ValueError(
            f"Unsupported child sitemap XML root element: "
            f"{etree.QName(root).localname}"
        )

    def _process_urlset(self, root) -> list[dict]:
        articles = []

        for url_element in root:
            if etree.QName(url_element).localname != "url":
                continue

            article_url = None
            last_modified = None

            for child in url_element:
                tag = etree.QName(child).localname

                if tag == "loc" and child.text:
                    article_url = child.text.strip()

                elif tag == "lastmod" and child.text:
                    last_modified = child.text.strip()

            if article_url:
                articles.append(
                    {
                        "url": article_url,
                        "title": None,
                        "author": None,
                        "published_at": None,
                        "last_modified": last_modified,
                        "summary": None,
                    }
                )

        return articles