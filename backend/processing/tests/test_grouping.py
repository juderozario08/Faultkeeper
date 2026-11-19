from typing import Any

import pytest

from processing.grouping import (
    event_culprit,
    event_title,
    grouping_hash,
    normalize_filename,
    normalize_message,
)


def exc_event(
    type_: str = "TypeError",
    value: str = "Cannot read properties of undefined (reading 'price')",
    frames: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    if frames is None:
        frames = [
            {"filename": "/node_modules/react-dom.js", "function": "commit", "in_app": False},
            {
                "filename": "http://localhost:5174/src/Cart.tsx?t=1",
                "function": "checkout",
                "lineno": 42,
                "in_app": True,
            },
        ]
    return {
        "exception": {
            "values": [{"type": type_, "value": value, "stacktrace": {"frames": frames}}]
        },
        **extra,
    }


def with_line(event: dict[str, Any], lineno: int) -> dict[str, Any]:
    frames = event["exception"]["values"][0]["stacktrace"]["frames"]
    return exc_event(frames=[{**f, "lineno": lineno} for f in frames])


def test_same_bug_different_line_numbers_and_messages_group_together() -> None:
    a = exc_event(value="x is undefined")
    b = with_line(exc_event(value="y is undefined"), 99)
    assert grouping_hash(a) == grouping_hash(b)


def test_different_function_is_different_issue() -> None:
    other = exc_event(
        frames=[{"filename": "src/Cart.tsx", "function": "applyCoupon", "in_app": True}]
    )
    assert grouping_hash(exc_event()) != grouping_hash(other)


def test_different_exception_type_is_different_issue() -> None:
    assert grouping_hash(exc_event()) != grouping_hash(exc_event(type_="RangeError"))


def test_library_frames_do_not_affect_grouping() -> None:
    base = exc_event()
    frames = [
        {"filename": "/node_modules/other-lib.js", "function": "x", "in_app": False},
        *base["exception"]["values"][0]["stacktrace"]["frames"],
    ]
    assert grouping_hash(base) == grouping_hash(exc_event(frames=frames))


def test_origin_and_bundle_hash_do_not_affect_grouping() -> None:
    dev = exc_event(
        frames=[
            {
                "filename": "http://localhost:5174/assets/index-BzX3a1Qe.js",
                "function": "checkout",
                "in_app": True,
            }
        ]
    )
    prod = exc_event(
        frames=[
            {
                "filename": "https://shop.example.com/assets/index-Q9w8E7r6.js",
                "function": "checkout",
                "in_app": True,
            }
        ]
    )
    assert grouping_hash(dev) == grouping_hash(prod)


def test_exception_without_frames_uses_normalized_value() -> None:
    a = exc_event(value="Order 1234 not found", frames=[])
    b = exc_event(value="Order 5678 not found", frames=[])
    c = exc_event(value="Customer 1234 not found", frames=[])
    assert grouping_hash(a) == grouping_hash(b) != grouping_hash(c)


def test_message_events() -> None:
    a = {"logentry": {"formatted": "User a@b.com failed login from 10.0.0.1"}}
    b = {"logentry": {"formatted": "User c@d.org failed login from 192.168.1.20"}}
    assert grouping_hash(a) == grouping_hash(b)


def test_custom_fingerprint() -> None:
    a = exc_event(fingerprint=["payment-timeout"])
    b = exc_event(type_="RangeError", fingerprint=["payment-timeout"])
    assert grouping_hash(a) == grouping_hash(b)
    assert grouping_hash(exc_event(fingerprint=["{{ default }}"])) == grouping_hash(exc_event())
    extended = exc_event(fingerprint=["{{ default }}", "tenant-a"])
    assert grouping_hash(extended) != grouping_hash(exc_event())


def test_chained_exceptions_all_count() -> None:
    single = exc_event()
    chained = exc_event()
    chained["exception"]["values"].insert(0, {"type": "KeyError", "value": "'id'"})
    assert grouping_hash(single) != grouping_hash(chained)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Order 42 failed", "Order <int> failed"),
        ("id 550e8400-e29b-41d4-a716-446655440000 missing", "id <uuid> missing"),
        ("hash deadbeefcafe0001 bad", "hash <hex> bad"),
        ("key 'abc' missing", "key <str> missing"),
    ],
)
def test_normalize_message(raw: str, expected: str) -> None:
    assert normalize_message(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("http://localhost:5174/src/Cart.tsx?t=1700000000", "/src/Cart.tsx"),
        ("/assets/index-BzX3a1Qe.js", "/assets/index.js"),
        ("app.3f2a9c1d.js", "app.js"),
        ("src/my-component.js", "src/my-component.js"),
    ],
)
def test_normalize_filename(raw: str, expected: str) -> None:
    assert normalize_filename(raw) == expected


def test_title_and_culprit() -> None:
    event = exc_event()
    assert event_title(event) == "TypeError: Cannot read properties of undefined (reading 'price')"
    assert event_culprit(event) == "/src/Cart.tsx in checkout"
    assert event_title({"logentry": {"formatted": "line one\nline two"}}) == "line one"
    assert event_title({}) == "<unlabeled event>"


def synthetic_message(text: str, fn: str = "message") -> dict[str, Any]:
    return {
        "logentry": {"formatted": text},
        "exception": {
            "values": [
                {
                    "type": "Error",
                    "value": text,
                    "mechanism": {"type": "generic", "synthetic": True},
                    "stacktrace": {
                        "frames": [{"filename": "src/main.ts", "function": fn, "in_app": True}]
                    },
                }
            ]
        },
    }


def test_synthetic_exception_uses_message_title_and_ignores_type() -> None:
    event = synthetic_message("Inventory sync is lagging")
    assert event_title(event) == "Inventory sync is lagging"
    renamed = synthetic_message("Inventory sync is lagging")
    renamed["exception"]["values"][0]["type"] = "SyntheticError"
    assert grouping_hash(event) == grouping_hash(renamed)


def test_culprit_prefers_named_function() -> None:
    event = exc_event(
        frames=[
            {"filename": "src/main.ts", "function": "cartTotal", "in_app": True},
            {"filename": "src/main.ts", "function": "<anonymous>", "in_app": True},
        ]
    )
    assert event_culprit(event) == "src/main.ts in cartTotal"
