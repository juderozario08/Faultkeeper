from typing import Any

from celery import shared_task

from .pipeline import process_event


@shared_task(name="processing.process_event", acks_late=True)
def process_event_task(project_id: int, payload: dict[str, Any], received_at: str) -> str:
    result = process_event(project_id, payload, received_at)
    return str(result.event.event_id)
