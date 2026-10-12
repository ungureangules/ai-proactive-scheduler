from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    timezone="UTC",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule_filename="/tmp/celerybeat-schedule",
    beat_schedule={
        # Runs hourly; each business is synced every hour and contacted at
        # OUTREACH_LOCAL_HOUR in its own timezone.
        "hourly-sync-and-outreach": {
            "task": "app.tasks.tasks.run_outreach_cycle",
            "schedule": crontab(minute=0),
        },
    },
)
