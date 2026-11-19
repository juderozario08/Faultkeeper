"""Single-process mode (DEPLOY_MODE=single): a background thread replaces Celery.

Used for the free hosted demo, where running a separate worker and Redis isn't possible.
"""

import logging
import queue
import threading
from typing import Any

from django.db import close_old_connections

from .pipeline import process_event

logger = logging.getLogger(__name__)

_queue: "queue.Queue[tuple[int, dict[str, Any], str]]" = queue.Queue(maxsize=10_000)
_started = False
_lock = threading.Lock()


def _worker() -> None:
    while True:
        project_id, payload, received_at = _queue.get()
        try:
            close_old_connections()
            process_event(project_id, payload, received_at)
        except Exception:
            logger.exception("in-process event processing failed")
        finally:
            close_old_connections()
            _queue.task_done()


def _ensure_started() -> None:
    global _started
    with _lock:
        if not _started:
            threading.Thread(target=_worker, name="faultkeeper-worker", daemon=True).start()
            _started = True


def submit(project_id: int, payload: dict[str, Any], received_at: str) -> None:
    _ensure_started()
    _queue.put_nowait((project_id, payload, received_at))
