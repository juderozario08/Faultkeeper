from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Event


@shared_task(name="issues.cleanup_old_events")
def cleanup_old_events() -> int:
    """Delete events past the retention window. Issues are kept."""
    cutoff = timezone.now() - timedelta(days=settings.EVENT_RETENTION_DAYS)
    deleted, _ = Event.objects.filter(timestamp__lt=cutoff).delete()
    return deleted
