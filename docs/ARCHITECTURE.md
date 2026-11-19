# Faultkeeper Architecture

This document is the source of truth for how Faultkeeper is built. If code and this document disagree, either the code is wrong or this document must be updated in the same change. Reasons behind each choice live in [decisions/](decisions/).

---

## 1. Goals and non-goals

**Goals**
- Accept events from the **official Sentry SDKs** unchanged (envelope protocol, DSN auth). See [PROTOCOL.md](PROTOCOL.md).
- Mirror the **shape of Sentry's production architecture**: ingest edge → event bus → processing workers → Postgres + ClickHouse → Django API → React UI.
- Group duplicate events into **issues** deterministically via fingerprinting.
- Show new issues and counts **in real time**.
- Run entirely with **one `docker compose up`**, at **zero cost**.

**Non-goals (for now)**
- Performance tracing/transactions, session replay, profiling, cron monitors, alert rules/notifications (may appear later in the roadmap).
- Multi-region, high availability, horizontal autoscaling.
- Wire compatibility with Sentry's *internal* web API (`/api/0/` paths are similar in spirit, not guaranteed identical).

---

## 2. System overview

```
 ┌───────────────────────────────┐
 │ Monitored applications        │  demo/buggy-shop, any web app, Python services
 │  · @sentry/browser            │
 │  · sentry-sdk (Python)        │
 │  · faultkeeper-js (ours)      │
 └───────────────┬───────────────┘
                 │ POST /api/<project_id>/envelope/   (also legacy /store/)
                 ▼
 ┌───────────────────────────────┐
 │ INGEST EDGE   ("Relay")       │  P1-2: backend/ingest (Django view)
 │  1. authenticate DSN key      │  P3:   relay/ (Rust, axum) in front
 │  2. rate-limit per key        │
 │  3. size-limit, parse envelope│
 │  4. enqueue raw event, 200 OK │
 └───────────────┬───────────────┘
                 │ P1: Celery task on Redis   ·   P2: Kafka topic `ingest-events`
                 ▼
 ┌───────────────────────────────┐
 │ EVENT PIPELINE (workers)      │  backend/processing
 │  normalize → [symbolicate P3] │
 │  → fingerprint → group → save │
 └─────┬─────────────┬───────────┘
       │             │ P2: Kafka topic `events`
       │             ▼
       │   ┌───────────────────┐
       │   │ ANALYTICS WRITER  │  backend/snuba_lite (Kafka consumer)
       │   │ → ClickHouse      │  batch inserts, time-series + search
       │   └───────────────────┘
       ▼
 ┌───────────────────────────────┐        ┌──────────────────────────┐
 │ PostgreSQL                    │        │ Redis                    │
 │ orgs, projects, keys, issues, │        │ broker · cache · rate    │
 │ releases, event payloads      │        │ limits · count buffers · │
 └───────────────┬───────────────┘        │ Channels pub/sub         │
                 ▼                        └──────────────────────────┘
 ┌───────────────────────────────┐        ┌──────────────────────────┐
 │ WEB API  (Django + DRF)       │◄──────►│ ISSUE INSIGHTS           │
 │ REALTIME (Django Channels WS) │        │ LLM provider interface   │
 └───────────────┬───────────────┘        │ Ollama (local) · Gemini  │
                 ▼                        └──────────────────────────┘
 ┌───────────────────────────────┐
 │ DASHBOARD (React + TS + Vite) │
 └───────────────────────────────┘
```

### Component map (with Sentry equivalents)

| Component | Code location | Technology | Sentry equivalent | Phase |
|---|---|---|---|---|
| SDKs | official SDKs; `sdk/faultkeeper-js` after the course | TypeScript | Sentry SDKs | 1 / later |
| Demo apps | `demo/buggy-shop` (browser) + `demo/buggy-shop-api` (Python) | React + `@sentry/browser`; Flask/FastAPI + `sentry-sdk` | n/a | 1 |
| Ingest edge | `backend/ingest` → `relay/` | Django view → Rust/axum | Relay | 1 → 3 |
| Event bus | Celery broker → Kafka | Redis → Kafka (KRaft) | Kafka | 1 → 2 |
| Event pipeline | `backend/processing` | Celery workers | ingest consumers + `save_event` | 1 |
| Metadata DB | `backend/*/models.py` | PostgreSQL 16 | Postgres | 1 |
| Event payload store | `backend/issues` (`Event` model) | Postgres JSONB | Nodestore | 1 |
| Analytics store | `backend/snuba_lite` | ClickHouse | ClickHouse + Snuba | 2 |
| Cache / limits / buffers | n/a | Redis 7 | Redis / Memcached | 1 |
| Web API | `backend/issues`, `backend/organizations` | Django + DRF | Django monolith | 1 |
| Realtime | `backend/realtime` | Django Channels | n/a (Sentry polls) | 1 |
| Issue Insights | `backend/insights` | provider interface → Ollama / Gemini | Seer | 1 |
| Source maps | `backend/processing/symbolication` | Python | Symbolicator | 3 |
| Dashboard | `frontend/` | React, TS, Vite, Emotion, ECharts | Sentry frontend | 1 |
| Packaging | `docker-compose*.yml` | Docker Compose | self-hosted Sentry | 1 |

---

## 3. Life of an event

1. **Capture.** An app throws `TypeError: Cannot read properties of undefined (reading 'price')`. The SDK builds an **event** (exception, stack frames, breadcrumbs, tags, contexts, release, environment) and wraps it in an **envelope**.
2. **Send.** The SDK derives the endpoint from the DSN `http://<public_key>@localhost:8000/<project_id>` and sends `POST /api/<project_id>/envelope/`, passing the key in `X-Sentry-Auth` or the `sentry_key` query parameter.
3. **Ingest edge.**
   1. Resolve `public_key` → `ProjectKey` (Redis cache, Postgres fallback). Unknown or disabled key or project mismatch → `401`/`403`.
   2. Rate-limit: fixed one-minute window per key (`INCR` + `EXPIRE`). Over limit → `429` with `Retry-After` and `X-Sentry-Rate-Limits`.
   3. Reject bodies over 1 MiB (after decompression) → `413`.
   4. Decompress (`Content-Encoding: gzip|deflate|br`), parse the envelope, and keep `event` items. Other item types are acknowledged and dropped (see PROTOCOL.md).
   5. Enqueue `{project_id, received_at, payload}` and respond `200 {"id": "<event_id>"}`. **No processing happens in the request.**
4. **Normalize.** Fill defaults (`level=error`, `platform`, timestamps), trim oversized strings and lists, normalize frames (strip query strings and cache-busting hashes from filenames, default `in_app`), and scrub obvious PII such as the `Authorization` and `Cookie` headers.
5. **Symbolicate** *(phase 3)*. Map minified JS frames to original source using uploaded source maps for the event's `release`, and fetch JS source to fill in context lines. Browser SDKs don't send source lines for bundled scripts. Until phase 3, code context comes from SDKs that send it themselves, e.g. `sentry-sdk` for Python.
6. **Fingerprint.** Compute the grouping hash (§5).
7. **Group.** Look up `GroupHash(project, hash)`. If it exists, use that issue. If not, create a `Group` and a `GroupHash` in one transaction; a unique constraint plus `get_or_create` handles races. A resolved issue that receives a new event is marked **regressed** and moves back to unresolved.
8. **Save.**
   - Insert the `Event` row (full JSONB payload).
   - Increment `times_seen` and update `last_seen` with an atomic `UPDATE` (`F('times_seen') + 1`), so the API and the WebSocket always agree. *(Phase 2: replace with a Redis write buffer flushed in batches, justified with before/after load-test numbers.)*
   - Upsert `Release` and `Environment` rows if they are new.
   - *(Phase 2)* Publish the processed event to Kafka `events` → ClickHouse.
9. **Broadcast.** Publish `issue.created` or `issue.updated` to the Channels group `project.<id>`. Connected dashboards update immediately.
10. **Explain** *(on demand)*. A user clicks **Insights** on an issue. The API builds a PII-scrubbed context (title, exception, top in-app frames with context lines, last breadcrumbs, tags), calls the configured LLM provider, and stores the result in `IssueInsight` so it isn't regenerated.

### Phase 2 pipeline (Kafka)

```
ingest ──► [ingest-events] ──► process consumer ──► Postgres
                                       └──► [events] ──► snuba_lite consumer ──► ClickHouse
```
- Topic key: `project_id`, which keeps per-project ordering.
- Consumers commit offsets only after a successful write, so delivery is at-least-once. Event inserts are idempotent on `(project_id, event_id)`.

---

## 4. Data model

### PostgreSQL

| Model | Important fields | Notes |
|---|---|---|
| `User` | email (login), name | Django custom user |
| `Organization` | name, slug | top-level tenant |
| `OrganizationMember` | org, user, role ∈ {owner, admin, member} | RBAC |
| `Project` | org, name, slug, platform | unique (org, slug) |
| `ProjectKey` | project, public_key (32 hex), is_active, rate_limit_per_minute | the DSN key |
| `Release` | project, version, first_seen | from event `release` |
| `Environment` | project, name | from event `environment` |
| `Group` (issue) | project, title, culprit, type, level, status ∈ {unresolved, resolved, ignored}, substatus (new / regressed / ongoing), first_seen, last_seen, times_seen, first_release | one bug |
| `GroupHash` | project, hash (md5 hex), group | unique (project, hash) |
| `Event` | event_id (UUID), project, group, timestamp, received_at, level, release, environment, payload (JSONB) | unique (project, event_id); index (group, timestamp desc) |
| `IssueInsight` | group, provider, model, summary, root_cause, suggested_fix, created_at | cached LLM output |

**Retention:** a periodic Celery task deletes `Event` rows older than 30 days (configurable). Issues are kept.

### ClickHouse *(phase 2)*

```sql
CREATE TABLE events (
    event_id     UUID,
    project_id   UInt64,
    group_id     UInt64,
    timestamp    DateTime64(3),
    level        LowCardinality(String),
    platform     LowCardinality(String),
    release      String,
    environment  LowCardinality(String),
    browser      LowCardinality(String),
    os           LowCardinality(String),
    url          String,
    title        String,
    tags         Map(String, String)
) ENGINE = ReplacingMergeTree
PARTITION BY toDate(timestamp)
ORDER BY (project_id, toStartOfHour(timestamp), group_id, event_id)
TTL toDateTime(timestamp) + INTERVAL 30 DAY;
```

### Redis keys

| Key | Type | Purpose |
|---|---|---|
| `pk:<public_key>` | string (JSON), TTL 60 s | ProjectKey cache |
| `rl:<public_key>:<epoch_minute>` | counter, TTL 120 s | rate limiting |
| `buf:group:<id>` *(phase 2)* | hash {times_seen, last_seen} | count buffer |
| `buf:dirty` *(phase 2)* | set of group ids | groups pending flush |
| Celery queues | lists | phase 1 broker |
| `asgi:*` | Channels layer | WebSocket pub/sub |

---

## 5. Grouping (fingerprinting)

The grouping hash decides which events count as "the same bug". It must stay **stable across deploys**, so line and column numbers, memory addresses and dynamic values are excluded.

1. **Custom fingerprint.** If the event has `fingerprint` and it isn't exactly `["{{ default }}"]`, hash its values, replacing `{{ default }}` with the default components below.
2. **Exception with frames.** Use every exception in `exception.values` (chained exceptions). For each one, take `type` plus, for each frame, `module` if present, otherwise the normalized filename, plus `function`. Use only `in_app` frames, or all frames if none are in-app. Line numbers, columns and the exception message are left out.
3. **Exception without frames.** Use `type` + the normalized `value`.
4. **Message only.** Use the normalized `message` or `logentry.formatted`.

**Normalization** replaces UUIDs, hex strings of 8+ characters, IP addresses, emails, numbers and quoted strings with placeholders (`<uuid>`, `<hex>`, `<ip>`, `<email>`, `<int>`, `<str>`).

**Hash:** `md5("\n".join(components)).hexdigest()`, the same hash function Sentry uses for grouping.

**Issue title:** `"<type>: <value>"` (truncated to 200 characters) or the message. **Culprit:** `function` in `module/filename` of the most recent in-app frame.

The rules are versioned (`GROUPING_CONFIG = "faultkeeper:2026-11"`) so they can change later without silently splitting existing issues.

---

## 6. APIs

### Ingest (SDK-facing)
| Method | Path | Notes |
|---|---|---|
| POST | `/api/<project_id>/envelope/` | primary endpoint. CORS `*`; accepts `text/plain` so browsers skip the preflight request |
| POST | `/api/<project_id>/store/` | legacy single-event JSON |

### Web API (dashboard-facing, session auth + CSRF)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/0/auth/login/`, `/logout/`; GET `/api/0/auth/me/` | session auth |
| GET/POST | `/api/0/organizations/` | list/create orgs |
| GET/POST | `/api/0/organizations/<org>/projects/` | list/create projects |
| GET/POST | `/api/0/projects/<org>/<project>/keys/` | DSN keys |
| GET | `/api/0/projects/<org>/<project>/issues/?query=&status=&sort=&cursor=` | issue list (cursor pagination) |
| GET/PUT | `/api/0/issues/<id>/` | detail; change status |
| GET | `/api/0/issues/<id>/events/`, `/events/latest/` | events of an issue |
| GET | `/api/0/projects/<org>/<project>/stats/?interval=1h&period=24h` | chart series (Postgres in P1, ClickHouse in P2) |
| POST/GET | `/api/0/issues/<id>/insights/` | generate / read Issue Insights |

Issue filtering in phase 1 uses plain query parameters: `?status=&level=&release=&environment=&q=` (`q` = free text in the title). A Sentry-style search syntax (`is:unresolved level:error release:1.2`) comes later as a parser that maps onto these same filters.

### Realtime
`WS /ws/projects/<project_id>/`: requires a session and project access.

Messages sent to the client:
```json
{ "type": "issue.created", "issue": { "id": 12, "title": "...", "times_seen": 1, "last_seen": "..." } }
{ "type": "issue.updated", "issue": { "id": 12, "times_seen": 57, "last_seen": "..." } }
```

---

## 7. Issue Insights (LLM)

- **Interface:** `backend/insights/providers/base.py` defines `InsightProvider.generate(context: IssueContext) -> Insight`.
- **Implementations:** `ollama.py` (default; local, free), `gemini.py` (free tier, used for the hosted demo), `disabled.py`.
- **Ollama runs natively on the host, not in Docker.** Containers can't use the GPU on macOS, and Docker on Windows only supports NVIDIA GPUs. The backend reaches it at `http://host.docker.internal:11434` (compose adds `extra_hosts: host.docker.internal:host-gateway` for Linux). A containerised Ollama is available via `--profile ai` for Linux/NVIDIA machines.
- **Default model:** a small code-capable model that fits an 8 GB Apple M1. It's configurable.
- **Fallback:** if the provider is unreachable, Insights reports itself as unavailable (`disabled` behaviour) instead of erroring.
- **Configuration:** `INSIGHTS_PROVIDER=ollama|gemini|disabled`, `INSIGHTS_MODEL=<name>`, `OLLAMA_URL`, `GEMINI_API_KEY` (never committed).
- **Privacy:** the context contains no user identifiers, IPs, cookies, request bodies, URL query strings or **frame local variables** (`vars`, sent by `sentry-sdk`). It is built only from the exception, frames and context lines, breadcrumb categories and messages, and tags.
- **Output:** uses each provider's structured-output mode (Ollama `format` with a JSON schema; Gemini `responseSchema`) to get `{summary, root_cause, suggested_fix}`. Schema validation failure → error shown in the UI.
- Results are cached per issue. Users can regenerate them on demand.

---

## 8. Frontend

- **Stack:** React + TypeScript + Vite, React Router, TanStack Query (server state), Emotion (styling), ECharts (charts), Vitest + React Testing Library.
- **Pages:** Login → Organization/Project picker → **Issues list** (search, status filter, live updates, sparkline) → **Issue detail** (title, culprit, counts, stack trace with in-app highlighting, breadcrumbs timeline, tags, event navigation, resolve/ignore, Insights panel) → **Project settings** (DSN, rate limit, setup snippet).
- **Theming:** Light and Dark themes. **Dark = Tokyo Night**, **Light = Tokyo Night Day**. The default follows the OS. A header toggle (Light / Dark / System) is saved in `localStorage` and applied before first paint. All colors are semantic tokens in `frontend/src/theme/` (CSS variables + Emotion theme). Components never use raw hex values, and ECharts uses the same tokens. Text tokens are adjusted to meet WCAG AA (4.5:1), and a unit test enforces it. Palette: [ADR 0012](decisions/0012-theming-tokyo-night.md).
- **Realtime:** one WebSocket per open project. Incoming messages update the TanStack Query cache directly instead of refetching.
- **Dev server:** Vite proxies `/api` and `/ws` to Django, so cookies stay on the same origin.

---

## 9. Deployment and environments

### Local (primary; used for demos)

Must run identically on **macOS (Apple Silicon)** and **Windows**.

| Service | Runs in | Port | Compose profile |
|---|---|---|---|
| `web` (Django, ASGI/uvicorn) | Docker | 8000 | default |
| `worker` (Celery worker + beat) | Docker (Celery doesn't support Windows natively) | n/a | default |
| `postgres` | Docker, postgres:16 | 5432 | default |
| `redis` | Docker, redis:7 | 6379 | default |
| `buggy-shop-api` (Flask/FastAPI + `sentry-sdk`) | Docker | 5175 | default |
| `frontend` (Vite dev server) | **native Node** | 5173 | n/a |
| `buggy-shop` (Vite dev server) | **native Node** | 5174 | n/a |
| Ollama | **native app** | 11434 | n/a (`ai` profile for Linux/NVIDIA) |
| `kafka` (apache/kafka, KRaft) | Docker | 9092 | `full` |
| `clickhouse` | Docker | 8123 / 9000 | `full` |
| `relay` *(phase 3)* | Docker, Rust binary | 3000 | `full` |

- **One compose file with profiles:** `docker compose up` starts only the core. `--profile full` adds Kafka + ClickHouse (and sets `EVENT_BUS=kafka`). `--profile ai` adds a containerised Ollama.
- **Vite apps run natively:** file watching over bind mounts is unreliable on Windows, and `node_modules` access through Docker is slow on both platforms.
- **Images must publish `linux/arm64`** builds so they run natively on Apple Silicon. Verify each tag when pinning.
- **Line endings:** `.gitattributes` forces LF (`* text=auto eol=lf`), so scripts checked out on Windows still run inside Linux containers.

### Hosted demo (free tiers, phase 1 feature set)
| Part | Provider |
|---|---|
| Django API **+ built dashboard** (same origin) | Render free web service |
| Postgres | Neon free tier |
| Buggy Shop (static) | Cloudflare Pages |
| Insights | Gemini free tier |

- **Same origin for the dashboard:** Django serves the built dashboard with WhiteNoise. A dashboard on a different site would need cross-site session cookies, which Safari and Firefox block. The Buggy Shop can live elsewhere because ingest uses CORS `*` and no cookies.
- **Single-process mode** (`DEPLOY_MODE=single`): an in-process worker thread replaces Celery, an in-memory channel layer replaces Redis pub/sub, and an in-memory cache replaces Redis caching and rate-limit counters. The hosted demo then needs no Redis, which avoids free-tier request quotas and fits Render's 512 MB. This is possible because `process_event` doesn't depend on the transport ([ADR 0004](decisions/0004-event-bus-celery-then-kafka.md)).
- **Unminified demo build:** the hosted Buggy Shop is built with minification off (source maps still emitted) until phase 3 symbolication. Minified names would make stack traces unreadable and split grouping on every deploy.

Free-tier limits change, so check them at deploy time ([ADR 0007](decisions/0007-zero-cost-infrastructure.md)). Kafka, ClickHouse and Relay run locally only.

### Configuration (`.env`)
`DJANGO_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `DEPLOY_MODE=standard|single`, `EVENT_BUS=celery|kafka`, `OLLAMA_URL`, `KAFKA_BOOTSTRAP`, `CLICKHOUSE_URL`, `INSIGHTS_PROVIDER`, `INSIGHTS_MODEL`, `GEMINI_API_KEY`, `EVENT_RETENTION_DAYS`, `INGEST_MAX_BYTES`. `.env.example` lists every variable with a safe default. Secrets are never committed.

---

## 10. Quality and observability

- **Backend:** pytest (+ pytest-django), ruff (lint + format), mypy.
- **Frontend:** Vitest, oxlint, `tsc -b`.
- **CI:** GitHub Actions runs every check on each push and PR.
- **Tests that must exist:** envelope parsing (fixtures captured from real SDKs), fingerprint stability (same bug → same hash; different bug → different hash), rate limiting, the grouping race, API permissions.
- **Load testing:** `loadtest/` sends N events across M distinct bugs and reports throughput, p50/p99 ingest latency and the issue count. Results go in the README.
- **Dogfooding:** Faultkeeper's own Django backend can report errors to a Faultkeeper project.
