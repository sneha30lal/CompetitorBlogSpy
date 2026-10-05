# Competitor Blog Spy

Competitor Blog Spy is a real-time competitor content monitoring system built with Python and FastAPI.

The system investigates a website when it is added, identifies an available monitoring source, continuously checks the source for new or changed content, extracts article information, prevents duplicate detections, records monitoring history, and displays monitoring statistics through a web dashboard.

## Features

- Automatic website source investigation
- RSS/Atom feed monitoring
- XML sitemap monitoring
- Direct-page change monitoring
- Article metadata extraction
- Canonical URL extraction
- Author and publication date extraction
- Article body extraction
- Image URL extraction
- Category and tag extraction
- Duplicate article prevention
- Monitoring check history
- Retry handling for failed checks
- Failure isolation between websites
- Controlled concurrent monitoring
- Detection delay measurement
- Web dashboard for monitoring status and statistics
- Demo websites for RSS, sitemap, and direct-page testing

## Technology Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- HTTPX
- BeautifulSoup
- lxml
- feedparser
- APScheduler
- Jinja2
- HTML/CSS/JavaScript

## Project Structure

`	ext
CompetitorBlogSpy/
+-- app/
¦   +-- api/
¦   +-- database/
¦   +-- models/
¦   +-- services/
¦   ¦   +-- analyzer/
¦   ¦   +-- detectors/
¦   ¦   +-- extractor/
¦   ¦   +-- monitoring/
¦   +-- templates/
¦   +-- main.py
+-- demo_site/
¦   +-- direct_page_only/
¦   +-- rss_demo/
¦   +-- sitemap_demo/

+-- requirements.txt
+-- README.md
+-- .gitignore
