from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app.api.websites import router as websites_router
from app.database.database import SessionLocal, create_tables
from app.models.models import Article, MonitoringCheck, Website
from app.services.monitoring.scheduler import MonitoringScheduler


scheduler = MonitoringScheduler(interval_minutes=5)


templates = Jinja2Templates(
    directory="app/templates"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()

    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="Competitor Blog Spy",
    description="Real-time competitor content monitoring system",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(websites_router)


@app.get("/")
def dashboard(request: Request):

    db = SessionLocal()

    try:

        active_websites = (
            db.query(Website)
            .filter(Website.active.is_(True))
            .order_by(Website.id)
            .all()
        )

        # Only count monitoring checks belonging to
        # currently active websites.
        active_checks = (
            db.query(MonitoringCheck)
            .join(
                Website,
                MonitoringCheck.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True)
            )
        )

        total_checks = active_checks.count()

        successful_checks = (
            active_checks
            .filter(
                MonitoringCheck.success.is_(True)
            )
            .count()
        )

        failed_checks = (
            active_checks
            .filter(
                MonitoringCheck.success.is_(False)
            )
            .count()
        )

        # Only count articles belonging to currently
        # active websites.
        articles_detected = (
            db.query(Article)
            .join(
                Website,
                Article.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True)
            )
            .count()
        )

        # Count actual new-article detection events
        # recorded by monitoring checks.
        new_articles = (
            db.query(
                func.coalesce(
                    func.sum(
                        MonitoringCheck.new_articles
                    ),
                    0,
                )
            )
            .select_from(MonitoringCheck)
            .join(
                Website,
                MonitoringCheck.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True)
            )
            .scalar()
            or 0
        )

        # Calculate detection statistics only for
        # currently active websites and articles detected
        # within the last 24 hours.
        recent_cutoff = (
            datetime.utcnow()
            - timedelta(hours=24)
        )

        average_detection_delay = (
            db.query(
                func.avg(
                    Article.detection_delay_seconds
                )
            )
            .select_from(Article)
            .join(
                Website,
                Article.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True),
                Article.detection_delay_seconds.isnot(None),
                Article.detected_at >= recent_cutoff,
            )
            .scalar()
        )

        fastest_detection_delay = (
            db.query(
                func.min(
                    Article.detection_delay_seconds
                )
            )
            .select_from(Article)
            .join(
                Website,
                Article.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True),
                Article.detection_delay_seconds.isnot(None),
                Article.detected_at >= recent_cutoff,
            )
            .scalar()
        )

        slowest_detection_delay = (
            db.query(
                func.max(
                    Article.detection_delay_seconds
                )
            )
            .select_from(Article)
            .join(
                Website,
                Article.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True),
                Article.detection_delay_seconds.isnot(None),
                Article.detected_at >= recent_cutoff,
            )
            .scalar()
        )

        # Latest detected articles from currently active websites.
        latest_article_rows = (
            db.query(
                Article,
                Website.name.label("website_name"),
                Website.strategy.label("strategy"),
            )
            .join(
                Website,
                Article.website_id == Website.id,
            )
            .filter(
                Website.active.is_(True)
            )
            .order_by(
                Article.detected_at.desc()
            )
            .limit(10)
            .all()
        )

        latest_articles = []

        for article, website_name, strategy in latest_article_rows:

            latest_articles.append(
                {
                    "title": article.title,
                    "website_name": website_name,
                    "url": article.url,
                    "published_at": article.published_at,
                    "detected_at": article.detected_at,
                    "detection_delay_seconds": (
                        article.detection_delay_seconds
                    ),
                    "strategy": strategy,
                }
            )

        # Show recent checks only for currently active
        # monitoring websites.
        recent_rows = (
            db.query(
                MonitoringCheck,
                Website.name.label(
                    "website_name"
                ),
            )
            .join(
                Website,
                MonitoringCheck.website_id
                == Website.id,
            )
            .filter(
                Website.active.is_(True)
            )
            .order_by(
                MonitoringCheck.checked_at.desc()
            )
            .limit(20)
            .all()
        )

        recent_checks = []

        for check, website_name in recent_rows:

            recent_checks.append(
                {
                    "website_name": website_name,
                    "checked_at": check.checked_at,
                    "strategy_used": check.strategy_used,
                    "articles_found": check.articles_found,
                    "new_articles": check.new_articles,
                    "response_time_ms": check.response_time_ms,
                    "success": check.success,
                    "error_message": check.error_message,
                }
            )

        stats = {
            "active_websites": len(
                active_websites
            ),
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "failed_checks": failed_checks,
            "articles_detected": articles_detected,
            "new_articles": new_articles,
            "average_detection_delay": (
                average_detection_delay
            ),
            "fastest_detection_delay": (
                fastest_detection_delay
            ),
            "slowest_detection_delay": (
                slowest_detection_delay
            ),
        }

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "stats": stats,
                "websites": active_websites,
                "latest_articles": latest_articles,
                "recent_checks": recent_checks,
            },
        )

    finally:

        db.close()


@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }