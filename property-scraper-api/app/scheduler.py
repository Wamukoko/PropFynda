import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import SCRAPE_INTERVAL_MINUTES
from app.database import SessionLocal
from app.scraper.runner import scrape_all_active_platforms

logger = logging.getLogger("scheduler")

scheduler = BackgroundScheduler()


def _scheduled_scrape_job():
    db = SessionLocal()
    try:
        results = scrape_all_active_platforms(db)
        for r in results:
            logger.info("Scrape result: %s", r)
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        _scheduled_scrape_job,
        "interval",
        minutes=SCRAPE_INTERVAL_MINUTES,
        id="scrape_all_platforms",
        replace_existing=True,
        next_run_time=None,  # first run is triggered manually / via API, not on startup
    )
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
