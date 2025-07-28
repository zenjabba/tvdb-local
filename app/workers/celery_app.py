"""Celery application configuration."""
import structlog
from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "tvdb_proxy",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.sync_tasks",
        "app.workers.cache_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    # Full database sync every 6 hours
    "full-sync": {
        "task": "app.workers.sync_tasks.full_sync",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Incremental updates every 15 minutes
    "incremental-sync": {
        "task": "app.workers.sync_tasks.incremental_sync",
        "schedule": crontab(minute="*/15"),
    },
    # Cache cleanup every hour
    "cache-cleanup": {
        "task": "app.workers.cache_tasks.cleanup_expired_cache",
        "schedule": crontab(minute=0),
    },
    # Popular content prefetch every 30 minutes
    "popular-content-prefetch": {
        "task": "app.workers.cache_tasks.prefetch_popular_content",
        "schedule": crontab(minute="*/30"),
    },
    # Static data sync daily
    "static-data-sync": {
        "task": "app.workers.sync_tasks.sync_static_data",
        "schedule": crontab(minute=0, hour=2),  # 2 AM daily
    },
}
