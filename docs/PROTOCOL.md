# Ingest Protocol

Faultkeeper implements a subset of the publicly documented [Sentry SDK protocol](https://develop.sentry.dev/sdk/) so the official SDKs can send events to it unmodified. This page describes exactly what Faultkeeper accepts. When the upstream docs and this page differ, this page describes Faultkeeper's behaviour, and the upstream docs describe what SDKs actually send.

---

## 1. DSN

```
{scheme}://{public_key}@{host}[:{port}]/{project_id}
http://3f2a9c...e1@localhost:8000/1
```

SDKs derive two endpoints from it:
- envelope: `{scheme}://{host}:{port}/api/{project_id}/envelope/`
- store (legacy): `{scheme}://{host}:{port}/api/{project_id}/store/`

`public_key` is a 32-character lowercase hex string stored in `ProjectKey.public_key`. Secret keys are not used.

## 2. Authentication

Faultkeeper accepts the key from either of these, in order of precedence:

1. Header `X-Sentry-Auth: Sentry sentry_version=7, sentry_key=<public_key>, sentry_client=<sdk>/<version>`
2. Query string `?sentry_key=<public_key>&sentry_version=7` (browser SDKs use this)

Failures:
| Condition | Status |
|---|---|
| no key | 401 |
| unknown or inactive key | 401 |
| key belongs to another project | 403 |

## 3. Request handling

| Concern | Behaviour |
|---|---|
| Methods | `POST` (and `OPTIONS` for CORS) |
| CORS | `Access-Control-Allow-Origin: *`; allow headers `Content-Type, X-Sentry-Auth, Content-Encoding` |
| Content-Type | `application/x-sentry-envelope`, `text/plain` (browsers, to avoid the preflight request), `application/json` (store) |
| Compression | `Content-Encoding: gzip`, `deflate`, `br`, or none. The Python SDK gzips by default. |
| Size limit | 1 MiB after decompression (`INGEST_MAX_BYTES`) → `413` |
| Success | `200` `{"id": "<event_id>"}` |
| Rate limited | `429`, `Retry-After: <seconds>`, `X-Sentry-Rate-Limits: <seconds>::key` |
| Malformed | `400` `{"detail": "<reason>"}` |

## 4. Envelope format

An envelope is newline (`\n`) separated:

```
<envelope header JSON>\n
<item header JSON>\n
<item payload>\n
<item header JSON>\n
<item payload>\n
...
```

**Envelope header** (all optional): `event_id`, `dsn`, `sent_at`, `sdk {name, version}`.

**Item header:** `type` (required), `length` (optional, in bytes), `content_type`, `filename`.
- If `length` is present, read exactly that many bytes for the payload and then expect `\n` or EOF.
- If `length` is absent, the payload runs until the next `\n` or EOF.

### Item types

| `type` | Faultkeeper behaviour |
|---|---|
| `event` | **processed**: becomes an Event (see §5) |
| `client_report`, `session`, `sessions` | accepted, dropped |
| `transaction`, `span`, `profile`, `replay_event`, `replay_recording`, `check_in`, `statsd`, `metric_meta` | accepted, dropped (not yet supported) |
| `attachment`, `user_report`, `feedback` | accepted, dropped (future) |
| unknown | accepted, dropped |

Dropping unsupported items is intentional. SDKs treat any non-2xx response as a failure and may retry or back off, so Faultkeeper always acknowledges well-formed envelopes.

## 5. Event payload (fields Faultkeeper reads)

| Field | Type | Use |
|---|---|---|
| `event_id` | 32-hex string (UUID without dashes) | idempotency key; generated if missing |
| `timestamp` | RFC 3339 string or Unix seconds (float) | event time; falls back to receive time |
| `platform` | string (`javascript`, `python`, …) | display, grouping hints |
| `level` | `fatal` `error` `warning` `info` `debug` | default `error` |
| `logger`, `transaction`, `server_name` | string | tags/display |
| `release`, `environment`, `dist` | string | releases, filters |
| `message` / `logentry {message, formatted, params}` | | message events |
| `exception.values[]` | list | see below |
| `breadcrumbs.values[]` | `{timestamp, type, category, message, level, data}` | timeline |
| `tags` | object or list of pairs | filters |
| `contexts` | `{browser, os, runtime, device, …}` | display, derived tags |
| `request` | `{url, method, headers, query_string}` | display (headers scrubbed) |
| `user` | `{id, email, ip_address, username}` | display only; never sent to the LLM |
| `sdk` | `{name, version}` | display |
| `fingerprint` | list of strings | custom grouping |

**Exception value:**
```json
{
  "type": "TypeError",
  "value": "Cannot read properties of undefined (reading 'price')",
  "module": null,
  "mechanism": { "type": "onerror", "handled": false },
  "stacktrace": {
    "frames": [
      { "filename": "app.js", "abs_path": "http://localhost:5174/assets/app.js",
        "function": "checkout", "module": null, "lineno": 42, "colno": 17,
        "in_app": true }
    ]
  }
}
```

- Frames are ordered **oldest call first, most recent call last**, so the crashing frame is the last element.
- **Context lines** (`context_line`, `pre_context`, `post_context`) are sent by server SDKs such as `sentry-sdk` for Python, which also sends local variables in `vars`. Browser SDKs **do not** send source lines for bundled scripts. Filling them in (source fetching / source maps) is phase 3.
- With chained exceptions, `exception.values` is ordered oldest (cause) first.

## 6. Legacy store endpoint

`POST /api/<project_id>/store/` takes a single event JSON object as the body. It goes through the same auth, limits and processing as an `event` envelope item.

## 7. Verifying compatibility

`backend/ingest/tests/fixtures/` holds real envelopes captured from:
- `@sentry/browser` (uncaught error, unhandled rejection, `captureMessage`)
- `sentry-sdk` for Python (exception, chained exception, gzip-encoded)
- `faultkeeper-js`

Every fixture must parse and produce the expected issue title, culprit and fingerprint. Whenever an SDK major version changes, capture a new fixture and add it.
