"""Hand events from ingest to the processing pipeline (the "event bus")."""

from typing import Any

from django.conf import settings


def enqueue_event(project_id: int, payload: dict[str, Any], received_at: str) -> None:
    if settings.DEPLOY_MODE == "single":
        from processing.inprocess import submit

        submit(project_id, payload, received_at)
        return

    from processing.tasks import process_event_task

    process_event_task.delay(project_id, payload, received_at)
