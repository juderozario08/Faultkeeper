# Glossary

Faultkeeper uses the same vocabulary as Sentry wherever possible.

| Term | Meaning |
|---|---|
| **Event** | One occurrence of an error or message, sent by an SDK. Immutable. |
| **Issue** (a.k.a. **Group**) | A collection of events that represent the same underlying problem. The `Group` model in code. |
| **Fingerprint** | The list of components that decides which issue an event belongs to; hashed into a **grouping hash**. |
| **GroupHash** | Maps a grouping hash to an issue within a project. |
| **Grouping config** | A versioned set of fingerprinting rules (`GROUPING_CONFIG`). |
| **Envelope** | The newline-delimited container format SDKs use to send one or more items (events, sessions, attachments…). |
| **Item** | One entry inside an envelope, with its own header (`type`, `length`). |
| **DSN** | Data Source Name — `scheme://public_key@host/project_id`. Tells an SDK where to send events and which key to use. |
| **Public key / ProjectKey** | The key embedded in a DSN; identifies and authorizes a project for ingest. |
| **Ingest edge / Relay** | The first server component events hit: authenticates, rate-limits, validates, and enqueues. |
| **Event bus** | Transport between ingest and processing: Celery/Redis (phase 1), Kafka (phase 2). |
| **Normalization** | Cleaning an event into a consistent shape: defaults, trimming, frame cleanup, PII scrubbing. |
| **Symbolication** | Turning minified or compiled stack frames into original source locations (e.g. via source maps). |
| **Nodestore** | Storage for full event payloads. In Faultkeeper: the `Event.payload` JSONB column. |
| **Snuba** | Sentry's query layer over ClickHouse. Faultkeeper's lightweight equivalent is `snuba_lite`. |
| **Stack frame** | One function call in a stack trace: filename/module, function, line, column, context lines. |
| **In-app frame** | A frame from the application's own code (not a library). Drives grouping and UI highlighting. |
| **Culprit** | Short "where it happened" label: the most recent in-app frame's function and module. |
| **Breadcrumbs** | A timeline of events leading up to an error (clicks, navigation, console logs, HTTP requests). |
| **Tags** | Indexed key/value pairs used for filtering (`browser`, `release`, `environment`, custom). |
| **Contexts** | Structured, non-indexed metadata (browser, OS, runtime, device). |
| **Release** | The application version an event came from. |
| **Environment** | Deployment environment (`production`, `staging`, …). |
| **Level** | Severity: `fatal`, `error`, `warning`, `info`, `debug`. |
| **Status** | Issue state: `unresolved`, `resolved`, `ignored`. |
| **Regression** | A resolved issue that receives a new event; it becomes unresolved again. |
| **Times seen / first seen / last seen** | Issue counters and timestamps, updated through a Redis buffer. |
| **Rate limit** | Max events per minute per key; excess gets `429` with `Retry-After`. |
| **Issue Insights** | LLM-generated summary, root cause, and suggested fix for an issue. |
