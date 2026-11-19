# 0003. Django + DRF + Channels monolith
- Status: Accepted
- Date: 2026-11-18

## Context
Sentry's core is a Python/Django monolith. Faultkeeper needs an ORM with migrations, auth and sessions, an admin, a REST layer and WebSockets, all delivered quickly.

## Decision
- Pinned versions: **Django 5.2 LTS** (supported until April 2028) and **Python 3.12**, pinned with `.python-version` so the host machine's own Python (macOS or Windows) doesn't matter.
- One Django project (`backend/`) served over ASGI (uvicorn), with apps: `organizations`, `ingest`, `processing`, `issues`, `realtime`, `insights`, `snuba_lite`.
- Django REST Framework for the web API; Django Channels (Redis channel layer) for WebSockets.
- Dependencies managed with `uv`. Lint and format with ruff; type-check with mypy.
- Session authentication + CSRF for the dashboard (same-origin through the Vite proxy). DSN keys for ingest.

## Consequences
- Ingest runs in the same process as the API in phases 1 and 2. It must stay thin (auth → limit → parse → enqueue) so the Rust edge can replace it in phase 3.
- App boundaries mirror Sentry's concepts, so code is easy to find.
