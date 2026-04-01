"""APScheduler configuration — runs inside the FastAPI process, no Redis needed."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def setup_scheduler() -> None:
    """Register all background jobs with their triggers.

    Jobs run inside the same process as FastAPI (AsyncIOScheduler).
    For a single-server portfolio deployment this is the correct approach.
    In production with multiple instances, use Celery + Redis + distributed lock.
    """
    from app.scheduler.jobs import (
        daily_stock_check_job,
        dose_reminder_job,
        missed_dose_detection_job,
    )

    scheduler.add_job(
        dose_reminder_job,
        trigger="interval",
        minutes=1,
        id="dose_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_dose_detection_job,
        trigger="interval",
        minutes=5,
        id="missed_dose",
        replace_existing=True,
    )
    scheduler.add_job(
        daily_stock_check_job,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_stock",
        replace_existing=True,
    )
