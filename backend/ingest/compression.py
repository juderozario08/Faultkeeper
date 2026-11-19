import zlib

import brotli

from .auth import IngestError


def decompress(body: bytes, encoding: str | None, max_bytes: int) -> bytes:
    """Decode `Content-Encoding`, refusing outputs larger than `max_bytes`."""
    encoding = (encoding or "").strip().lower()
    if encoding in ("", "identity"):
        data = body
    elif encoding in ("gzip", "x-gzip"):
        data = _zlib(body, zlib.MAX_WBITS | 16, max_bytes)
    elif encoding == "deflate":
        try:
            data = _zlib(body, zlib.MAX_WBITS, max_bytes)  # zlib-wrapped
        except zlib.error:
            data = _zlib(body, -zlib.MAX_WBITS, max_bytes)  # raw deflate
    elif encoding == "br":
        try:
            data = brotli.decompress(body)
        except brotli.error as exc:
            raise IngestError(400, "invalid brotli body") from exc
    else:
        raise IngestError(415, f"unsupported content encoding {encoding!r}")

    if len(data) > max_bytes:
        raise IngestError(413, "payload too large")
    return data


def _zlib(body: bytes, wbits: int, max_bytes: int) -> bytes:
    try:
        decompressor = zlib.decompressobj(wbits)
        data = decompressor.decompress(body, max_bytes + 1)
    except zlib.error as exc:
        if wbits == zlib.MAX_WBITS:
            raise
        raise IngestError(400, "invalid compressed body") from exc
    return data
