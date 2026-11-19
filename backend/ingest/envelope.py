"""Parser for the Sentry envelope format (see docs/PROTOCOL.md §4).

    <envelope header JSON>\\n
    <item header JSON>\\n<payload>\\n
    ...

An item's payload is exactly `length` bytes when the header has `length`;
otherwise it runs to the next newline (or end of input).
"""

import json
from dataclasses import dataclass, field
from typing import Any


class EnvelopeError(ValueError):
    pass


@dataclass
class EnvelopeItem:
    headers: dict[str, Any]
    payload: bytes

    @property
    def type(self) -> str:
        return str(self.headers.get("type", ""))

    def json(self) -> Any:
        try:
            return json.loads(self.payload)
        except (ValueError, UnicodeDecodeError) as exc:
            raise EnvelopeError(f"item of type {self.type!r} is not valid JSON") from exc


@dataclass
class Envelope:
    headers: dict[str, Any]
    items: list[EnvelopeItem] = field(default_factory=list)


def _parse_json_line(raw: bytes, what: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise EnvelopeError(f"{what} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise EnvelopeError(f"{what} must be a JSON object")
    return value


def _read_line(body: bytes, pos: int) -> tuple[bytes, int]:
    end = body.find(b"\n", pos)
    if end == -1:
        return body[pos:], len(body)
    return body[pos:end], end + 1


def parse_envelope(body: bytes) -> Envelope:
    if not body.strip():
        raise EnvelopeError("empty envelope")

    header_line, pos = _read_line(body, 0)
    envelope = Envelope(headers=_parse_json_line(header_line, "envelope header"))

    while pos < len(body):
        item_header_line, pos = _read_line(body, pos)
        if not item_header_line.strip():
            continue  # tolerate blank lines / trailing newline
        headers = _parse_json_line(item_header_line, "item header")
        if "type" not in headers:
            raise EnvelopeError("item header is missing 'type'")

        length = headers.get("length")
        if length is not None:
            if not isinstance(length, int) or length < 0:
                raise EnvelopeError("item 'length' must be a non-negative integer")
            if pos + length > len(body):
                raise EnvelopeError("item 'length' exceeds envelope size")
            payload = body[pos : pos + length]
            pos += length
            if pos < len(body) and body[pos : pos + 1] == b"\n":
                pos += 1
        else:
            payload, pos = _read_line(body, pos)

        envelope.items.append(EnvelopeItem(headers=headers, payload=payload))

    return envelope
