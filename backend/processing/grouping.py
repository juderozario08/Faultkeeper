"""Fingerprinting: decide which events are "the same bug" (ARCHITECTURE.md §5)."""

import hashlib
import re
from typing import Any
from urllib.parse import urlsplit

from .normalize import message_of

GROUPING_CONFIG = "faultkeeper:2026-11"
DEFAULT_PLACEHOLDER = "{{ default }}"

_MESSAGE_PATTERNS = [
    (
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
        "<uuid>",
    ),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<email>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"\b(?:0x)?[0-9a-f]{8,}\b", re.I), "<hex>"),
    (re.compile(r"(['\"])(?:(?!\1).){0,200}\1"), "<str>"),
    (re.compile(r"\b\d+(?:\.\d+)?\b"), "<int>"),
]

# `index-BzX3a1Qe.js`, `app.3f2a9c1d.js`, `chunk-ABCD1234.mjs` -> `index.js`, `app.js`, ...
_FILENAME_HASH = re.compile(r"[.-](?=[A-Za-z0-9_]*\d)[A-Za-z0-9_]{8,}(?=\.\w+$)")


def normalize_message(message: str) -> str:
    for pattern, placeholder in _MESSAGE_PATTERNS:
        message = pattern.sub(placeholder, message)
    return message.strip()


def normalize_filename(filename: str) -> str:
    """Drop origin, query string, fragment, and cache-busting hashes."""
    if "://" in filename:
        filename = urlsplit(filename).path
    filename = filename.split("?", 1)[0].split("#", 1)[0]
    return _FILENAME_HASH.sub("", filename)


def _frames(exception: dict[str, Any]) -> list[dict[str, Any]]:
    stacktrace = exception.get("stacktrace")
    if not isinstance(stacktrace, dict):
        return []
    return [f for f in stacktrace.get("frames") or [] if isinstance(f, dict)]


def _app_frames(exception: dict[str, Any]) -> list[dict[str, Any]]:
    frames = _frames(exception)
    in_app = [f for f in frames if f.get("in_app")]
    return in_app or frames


def _frame_location(frame: dict[str, Any]) -> str:
    if frame.get("module"):
        return str(frame["module"])
    return normalize_filename(str(frame.get("filename") or frame.get("abs_path") or "?"))


def default_components(event: dict[str, Any]) -> list[str]:
    exceptions = (event.get("exception") or {}).get("values") or []
    if exceptions:
        components: list[str] = []
        for exc in exceptions:
            components.append(f"type:{exc.get('type')}")
            frames = _app_frames(exc)
            if frames:
                for frame in frames:
                    components.append(
                        f"frame:{_frame_location(frame)}:{frame.get('function') or '?'}"
                    )
            else:
                components.append(f"value:{normalize_message(str(exc.get('value') or ''))}")
        return components

    message = message_of(event)
    if message:
        return [f"message:{normalize_message(message)}"]
    return ["fallback:no-data"]


def grouping_components(event: dict[str, Any]) -> list[str]:
    fingerprint = event.get("fingerprint")
    if isinstance(fingerprint, list) and fingerprint and fingerprint != [DEFAULT_PLACEHOLDER]:
        components: list[str] = []
        for part in fingerprint:
            if str(part) == DEFAULT_PLACEHOLDER:
                components.extend(default_components(event))
            else:
                components.append(f"custom:{part}")
        return components
    return default_components(event)


def grouping_hash(event: dict[str, Any]) -> str:
    joined = "\n".join([GROUPING_CONFIG, *grouping_components(event)])
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def event_title(event: dict[str, Any]) -> str:
    exceptions = (event.get("exception") or {}).get("values") or []
    if exceptions:
        exc = exceptions[-1]  # the outermost / most recently raised
        value = str(exc.get("value") or "").strip()
        title = f"{exc.get('type')}: {value}" if value else str(exc.get("type"))
    else:
        title = message_of(event).strip().splitlines()[0] if message_of(event).strip() else ""
    return (title or "<unlabeled event>")[:200]


def event_culprit(event: dict[str, Any]) -> str:
    exceptions = (event.get("exception") or {}).get("values") or []
    for exc in reversed(exceptions):
        frames = _app_frames(exc)
        if frames:
            frame = frames[-1]  # most recent call
            return f"{_frame_location(frame)} in {frame.get('function') or '?'}"[:255]
    return str(event.get("transaction") or event.get("logger") or "")[:255]
