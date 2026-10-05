import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Website
from app.services.analyzer.source_analyzer import SourceAnalyzer


router = APIRouter(
    prefix="/api/websites",
    tags=["Websites"],
)

analyzer = SourceAnalyzer()


class WebsiteCreate(BaseModel):
    name: str
    url: HttpUrl


@router.post("")
async def add_website(
    website_data: WebsiteCreate,
    db: Session = Depends(get_db),
):
    url = str(website_data.url).rstrip("/")

    existing = (
        db.query(Website)
        .filter(Website.url == url)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Website is already being monitored.",
        )

    analysis = await analyzer.analyze(url)

    if not analysis.get("success"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to investigate website: "
                + str(analysis.get("error"))
            ),
        )

    strategy = analysis["recommended_strategy"]

    if strategy == "rss":
        source_url = analysis["rss_feeds"][0]

    elif strategy == "sitemap":
        source_url = analysis["sitemaps"][0]

    else:
        source_url = url

    website = Website(
        name=website_data.name,
        url=url,
        strategy=strategy,
        source_url=source_url,
        source_details=json.dumps(
            {
                "rss_feeds": analysis["rss_feeds"],
                "sitemaps": analysis["sitemaps"],
                "direct_page": analysis["direct_page"],
            }
        ),
        active=True,
    )

    db.add(website)
    db.commit()
    db.refresh(website)

    return {
        "id": website.id,
        "name": website.name,
        "url": website.url,
        "strategy": website.strategy,
        "source_url": website.source_url,
        "active": website.active,
        "message": "Website added successfully.",
    }


@router.get("")
def list_websites(
    db: Session = Depends(get_db),
):
    websites = (
        db.query(Website)
        .order_by(Website.created_at.desc())
        .all()
    )

    return [
        {
            "id": website.id,
            "name": website.name,
            "url": website.url,
            "strategy": website.strategy,
            "source_url": website.source_url,
            "active": website.active,
            "last_checked_at": website.last_checked_at,
            "last_success_at": website.last_success_at,
            "last_error": website.last_error,
        }
        for website in websites
    ]