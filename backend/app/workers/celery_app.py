"""Celery application configuration."""

from celery import Celery

from app.config import settings

# Create Celery app
celery_app = Celery(
    "sales_forecasting",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.training",
        "app.workers.tasks.optimization",
        "app.workers.tasks.reports",
        "app.workers.tasks.forecasting",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Task routing
    task_routes={
        "app.workers.tasks.training.*": {"queue": "ml"},
        "app.workers.tasks.optimization.*": {"queue": "ml"},
        "app.workers.tasks.forecasting.*": {"queue": "ml"},
        "app.workers.tasks.reports.*": {"queue": "default"},
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-reports": {
            "task": "app.workers.tasks.reports.process_scheduled_reports",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)
