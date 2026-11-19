# Roadmap

Faultkeeper is built in small, end-to-end increments. Every milestone leaves the system runnable and demoable. Check items off in the same commit that completes them.

Legend: ☐ todo · ◐ in progress · ☑ done

---

## Phase 1: Core error tracker

**Target:** a complete, Sentry-SDK-compatible error tracker running with `docker compose up`.

### M1. Foundation
- ☑ Repo layout: `backend/`, `frontend/`, `demo/`, `loadtest/`
- ☑ `docker-compose.yml`: postgres, redis, web, worker, buggy-shop-api with health checks; `ai` profile; multi-arch images
- ☑ `.gitattributes` (LF line endings), `.python-version` (3.12), Django 5.2 LTS
- ◐ Cross-platform: verified on Windows; start/stop/check scripts for macOS, Linux and Windows
- ☑ Django project on ASGI, settings from environment, `.env.example`, `/api/0/health/`
- ☑ CI pipeline runs locally via `scripts/check` (16 checks: lint, types, tests, builds, compose smoke test, 300-event end-to-end check, production image)

### M2. Tenancy and auth
- ☑ Custom `User`, `Organization`, `OrganizationMember` (owner/admin/member), `Project`, `ProjectKey`
- ☑ Session login/logout/me API; membership-scoped permissions (foreign orgs → 404)
- ◐ Roles: project creation limited to owners/admins; finer-grained role checks later
- ☑ Seed command: demo org, three projects with deterministic local keys, admin user

### M3. Ingest
- ☑ Envelope parser (length / no-length items), gzip / deflate / br
- ☑ `/api/<id>/envelope/` and `/api/<id>/store/` endpoints, CORS
- ☑ DSN key auth (header + query), Redis key cache
- ☑ Per-key rate limiting with `429` + `Retry-After` / `X-Sentry-Rate-Limits`
- ☑ Size limit `413`; enqueue to Celery (or the in-process worker in single mode)
- ☑ Async ingest path with native asyncio Redis (2× throughput)
- ☑ Compatibility tests drive the real `sentry-sdk`; `@sentry/browser` verified end to end via the Buggy Shop

### M4. Processing and grouping
- ☑ Normalization + PII scrubbing (sensitive headers, cookies)
- ☑ Fingerprinting per ARCHITECTURE §5 (incl. synthetic exceptions), table-driven tests
- ☑ `Group` / `GroupHash` / `Event` persistence, race-safe, idempotent on `event_id`
- ☑ Regression detection (resolved → unresolved/regressed)
- ☑ Atomic `times_seen` / `last_seen` updates; retention task (Celery beat)
- ☑ Release / Environment upsert

### M5. Web API
- ☑ Issues list with filter params (`status`, `level`, `release`, `environment`, `q`), sort, cursor pagination, 24h sparklines
- ☑ Issue detail, status updates, events list, event detail with previous/next, tag summaries
- ☑ Project stats series and filter values (Postgres)
- ☑ Project keys and DSN endpoint

### M6. Dashboard
- ☑ Vite app shell, routing, auth flow, API client
- ☑ Theme system: semantic tokens, Tokyo Night (dark) + Tokyo Night Day (light), Light/Dark/System toggle, no flash on load, contrast tests
- ☑ Issues list page with sparklines, filters, live status
- ☑ Issue detail: stack trace (in-app highlighting, context lines, locals), chained exceptions, breadcrumbs, tags, contexts, event navigation
- ☑ Resolve / ignore / unresolve actions
- ☑ Project settings: DSN + setup snippets

### M7. Realtime
- ☑ Channels consumer `/ws/projects/<id>/` with auth (4403 for non-members)
- ☑ Publish `issue.created` / `issue.updated` from workers and status changes (throttling arrives in phase 2)
- ☑ Frontend cache updates + reconnect with backoff and catch-up refetch

### M8. Demo apps
- ☑ `demo/buggy-shop`: storefront with deliberate bugs (null access, unhandled rejection, failing API calls, warning message), `@sentry/browser`
- ☑ `demo/buggy-shop-api`: Flask backend with deliberate server bugs, `sentry-sdk` (context lines + locals)

### M9. Issue Insights
- ☑ Provider interface + Ollama + Gemini + disabled, with availability hints
- ☑ Context builder (no PII, no frame `vars`, no query strings), structured JSON-schema output, caching
- ☑ Insights panel in issue detail
- ☑ Optional `ai` compose profile for containerised Ollama

### M10. Ship
- ☑ Load test script + benchmark numbers in README
- ☑ Single-process mode (`DEPLOY_MODE=single`): in-process worker, in-memory channel layer + cache (verified without Redis)
- ☑ Production image: Django serves the built dashboard (same origin), single-process mode; verified with a live update
- ☐ Hosted demo on free tiers (Render + Neon); unminified Buggy Shop on Cloudflare Pages
- ☐ README screenshots / demo GIF

---

## Phase 2: Sentry-style pipeline

- ☐ `full` compose profile: Kafka (KRaft) + ClickHouse
- ☐ Redis count buffer + batched flush (replace atomic updates), with before/after load-test numbers
- ☐ Sentry-style search syntax parser mapped onto the filter params
- ☐ `faultkeeper-js` SDK: init(dsn), global handlers, captureException/Message, breadcrumbs, envelope transport
- ☐ `EVENT_BUS=kafka`: ingest producer → `ingest-events`
- ☐ Processing consumer (shared `process_event`) → Postgres + `events` topic
- ☐ `snuba_lite` ClickHouse writer (batched) + schema migration
- ☐ Stats + search endpoints backed by ClickHouse
- ☐ Benchmark: Celery vs Kafka pipeline

## Phase 3: Edge and symbolication

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
