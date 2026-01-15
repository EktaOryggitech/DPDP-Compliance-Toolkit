"""
DPDP GUI Compliance Scanner - Celery Application Configuration
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "dpdp_scanner",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.scan_tasks",
        "app.workers.tasks.report_tasks",
        "app.workers.tasks.schedule_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=settings.SCAN_TIMEOUT_SECONDS + 300,  # Add buffer
    task_soft_time_limit=settings.SCAN_TIMEOUT_SECONDS,

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for long-running scans
    worker_concurrency=settings.MAX_CONCURRENT_SCANS,

    # Result backend settings
    result_expires=86400 * 7,  # 7 days

    # Task routing
    task_routes={
        "app.workers.tasks.scan_tasks.*": {"queue": "scans"},
        "app.workers.tasks.report_tasks.*": {"queue": "reports"},
        "app.workers.tasks.schedule_tasks.*": {"queue": "schedules"},
    },

    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-scans": {
            "task": "app.workers.tasks.schedule_tasks.check_scheduled_scans",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-old-evidence": {
            "task": "app.workers.tasks.schedule_tasks.cleanup_old_evidence",
            "schedule": 86400.0,  # Daily
        },
    },
)

# Optional: Configure task retry policy
celery_app.conf.task_default_retry_delay = 60  # 1 minute
celery_app.conf.task_max_retries = 3
