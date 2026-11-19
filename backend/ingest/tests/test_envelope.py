import json

import pytest

from ingest.envelope import EnvelopeError, parse_envelope


def test_items_with_and_without_length() -> None:
    event = json.dumps({"message": "hi"}).encode()
    body = (
        b'{"event_id":"9ec79c33ec9942ab8353589fcb2e04dc"}\n'
        + b'{"type":"event","length":'
        + str(len(event)).encode()
        + b"}\n"
        + event
        + b"\n"
        + b'{"type":"client_report"}\n{"discarded_events":[]}\n'
    )
    envelope = parse_envelope(body)
    assert envelope.headers["event_id"] == "9ec79c33ec9942ab8353589fcb2e04dc"
    assert [i.type for i in envelope.items] == ["event", "client_report"]
    assert envelope.items[0].json() == {"message": "hi"}


def test_length_payload_may_contain_newlines() -> None:
    payload = b'{"a":\n1}'
    body = b"{}\n" + b'{"type":"event","length":%d}\n' % len(payload) + payload
    assert parse_envelope(body).items[0].json() == {"a": 1}


def test_empty_envelope_header_and_no_trailing_newline() -> None:
    envelope = parse_envelope(b'\n{"type":"event"}\n{"x":1}')
    assert envelope.headers == {}
    assert envelope.items[0].json() == {"x": 1}


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"not json\n",
        b"{}\n{}\n{}",  # item header without type
        b'{}\n{"type":"event","length":999}\n{}',  # length past end
        b'{}\n{"type":"event","length":-1}\n{}',
        b"[1,2]\n",
    ],
)
def test_malformed(body: bytes) -> None:
    with pytest.raises(EnvelopeError):
        parse_envelope(body)
