# Roadmap

Faultkeeper is built in small, end-to-end increments. Every milestone leaves the system runnable and demoable. Check items off in the same commit that completes them.

Legend: ☐ todo · ◐ in progress · ☑ done

---

## Phase 1 — Core error tracker

**Target:** a complete, Sentry-SDK-compatible error tracker running with `docker compose up`.

### M1. Foundation
- ☐ Repo scaffolding: `backend/`, `frontend/`, `sdk/`, `demo/`, `loadtest/`
- ☐ `docker-compose.yml` (core services; `full` and `ai` profiles), multi-arch (`linux/arm64`) images, Vite apps run natively
- ☐ `.gitattributes` (LF line endings), `.python-version` (3.12), Django 5.2 LTS
- ☐ Verified on macOS (Apple Silicon) and Windows
- ☐ Django project on ASGI, settings from environment, `.env.example`
- ☐ CI: ruff, mypy, pytest, eslint, tsc, vitest

### M2. Tenancy and auth
- ☐ Custom `User`, `Organization`, `OrganizationMember` (owner/admin/member), `Project`, `ProjectKey`
- ☐ Session login/logout/me API; permission classes
- ☐ Seed command: demo org, project, key, admin user

### M3. Ingest
- ☐ Envelope parser (length / no-length items, compression)
- ☐ `/api/<id>/envelope/` and `/api/<id>/store/` endpoints, CORS
- ☐ DSN key auth (header + query), Redis key cache
- ☐ Per-key rate limiting with `429` + `Retry-After` / `X-Sentry-Rate-Limits`
- ☐ Size limit `413`; enqueue to Celery
- ☐ Fixtures from `@sentry/browser` and `sentry-sdk`

### M4. Processing and grouping
- ☐ Normalization + PII scrubbing
- ☐ Fingerprinting per ARCHITECTURE §5, table-driven tests
- ☐ `Group` / `GroupHash` / `Event` persistence, race-safe
- ☐ Regression detection (resolved → unresolved)
- ☐ Atomic `times_seen` / `last_seen` updates; retention task
- ☐ Release / Environment upsert

### M5. Web API
- ☐ Issues list with filter params (`status`, `level`, `release`, `environment`, `q`), sort, cursor pagination
- ☐ Issue detail, status updates, events list, latest event
- ☐ Project stats series (Postgres)
- ☐ Project keys and DSN endpoint

### M6. Dashboard
- ☐ Vite app shell, routing, auth flow, API client
- ☐ Theme system: semantic tokens, Tokyo Night (dark) + Tokyo Night Day (light), Light/Dark/System toggle, no flash on load
- ☐ Issues list page with sparklines
- ☐ Issue detail: stack trace (in-app highlighting, context lines), breadcrumbs, tags, contexts, event navigation
- ☐ Resolve / ignore actions
- ☐ Project settings: DSN + setup snippets

### M7. Realtime
- ☐ Channels consumer `/ws/projects/<id>/` with auth
- ☐ Publish `issue.created` / `issue.updated` from workers (throttled)
- ☐ Frontend cache updates + reconnect refetch

### M8. Demo apps
- ☐ `demo/buggy-shop`: storefront with ≥4 deliberate bugs (null access, failed fetch, unhandled rejection, custom message), `@sentry/browser`
- ☐ `demo/buggy-shop-api`: Flask/FastAPI backend with deliberate server bugs, `sentry-sdk` (context lines + locals)

### M9. Issue Insights
- ☐ Provider interface + Ollama (native, via `host.docker.internal`) + Gemini + disabled, with unavailable fallback
- ☐ Context builder (no PII, no frame `vars`, no query strings), structured JSON-schema output, caching
- ☐ Insights panel in issue detail
- ☐ Optional `ai` compose profile for containerised Ollama (Linux/NVIDIA)

### M10. Ship
- ☐ Load test script + first benchmark numbers in README
- ☐ Single-process mode (`DEPLOY_MODE=single`): in-process worker, in-memory channel layer + cache
- ☐ Hosted demo on free tiers: Django serves the built dashboard (same origin); unminified Buggy Shop on Pages
- ☐ README screenshots / demo GIF

---

## Phase 2 — Sentry-style pipeline

- ☐ `full` compose profile: Kafka (KRaft) + ClickHouse
- ☐ Redis count buffer + batched flush (replace atomic updates), with before/after load-test numbers
- ☐ Sentry-style search syntax parser mapped onto the filter params
- ☐ `faultkeeper-js` SDK: init(dsn), global handlers, captureException/Message, breadcrumbs, envelope transport
- ☐ `EVENT_BUS=kafka`: ingest producer → `ingest-events`
- ☐ Processing consumer (shared `process_event`) → Postgres + `events` topic
- ☐ `snuba_lite` ClickHouse writer (batched) + schema migration
- ☐ Stats + search endpoints backed by ClickHouse
- ☐ Benchmark: Celery vs Kafka pipeline

## Phase 3 — Edge and symbolication

- ☐ `relay/` Rust (axum) ingest: auth, rate limits, envelope parsing, Kafka produce
- ☐ Black-box ingest test suite run against Django and Rust
- ☐ Benchmark: Django vs Rust ingest
- ☐ Release artifact upload API for source maps
- ☐ Source-map symbolication of JavaScript frames + JS source fetching for context lines

## Later ideas
- Alert rules + email/webhook notifications
- Performance transactions and spans
- User feedback widget
- Issue assignment and comments
- Python SDK integration example for Django apps
