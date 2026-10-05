import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database.database import SessionLocal
from app.models.models import Website
from app.services.monitoring.monitor import MonitoringEngine


class MonitoringScheduler:
    """Runs periodic monitoring checks with controlled concurrency."""

    def __init__(
        self,
        interval_minutes: int = 5,
        max_concurrent_checks: int = 10,
    ):
        self.interval_minutes = interval_minutes
        self.max_concurrent_checks = max_concurrent_checks

        self.scheduler = AsyncIOScheduler()
        self.engine = MonitoringEngine()

        # Prevent overlapping monitoring runs.
        self._run_lock = asyncio.Lock()

    async def _check_one_website(
        self,
        website_id: int,
        semaphore: asyncio.Semaphore,
    ):
        async with semaphore:

            db = SessionLocal()

            try:
                website = (
                    db.query(Website)
                    .filter(Website.id == website_id)
                    .first()
                )

                if website is None:
                    return

                await self.engine.check_website(
                    db,
                    website,
                )

            except Exception:
                # A failed website must not stop
                # monitoring of other websites.
                pass

            finally:
                db.close()

    async def run_checks(self):
        # Prevent a second monitoring cycle from running
        # while the previous cycle is still active.
        if self._run_lock.locked():
            return

        async with self._run_lock:

            db = SessionLocal()

            try:
                website_ids = [
                    website.id
                    for website in (
                        db.query(Website)
                        .filter(
                            Website.active.is_(True)
                        )
                        .all()
                    )
                ]

            finally:
                db.close()

            semaphore = asyncio.Semaphore(
                self.max_concurrent_checks
            )

            tasks = [
                self._check_one_website(
                    website_id,
                    semaphore,
                )
                for website_id in website_ids
            ]

            if tasks:
                await asyncio.gather(
                    *tasks,
                    return_exceptions=True,
                )

    def start(self):
        self.scheduler.add_job(
            self.run_checks,
            "interval",
            minutes=self.interval_minutes,
            id="website_monitor",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        self.scheduler.start()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(
                wait=False
            )