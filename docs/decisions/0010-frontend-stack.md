# 0010. Frontend stack and demo apps
- Status: Accepted
- Date: 2026-11-18

## Context
Sentry's UI is React + TypeScript, styled with Emotion, with charts in ECharts. The demo needs realistic errors with rich stack traces. Browser SDKs don't send source-code lines for bundled JavaScript (Sentry's server fetches them), so a browser-only demo would show no code context.

## Decision
- React + TypeScript + Vite, React Router, TanStack Query for server state, Emotion for styling, ECharts for charts.
- Vitest + React Testing Library; ESLint; `tsc --noEmit` in CI.
- **Vite apps run natively with Node, not in Docker.** File watching over bind mounts is unreliable on Windows, and `node_modules` access through Docker is slow on macOS and Windows.
- In development, Vite proxies `/api` and `/ws` to Django so the session cookie stays on the same origin. In the hosted build, Django serves the built dashboard itself ([ADR 0007](0007-zero-cost-infrastructure.md)).
- **Demo apps:**
  - `demo/buggy-shop`: a small Vite storefront with deliberate front-end bugs, instrumented with `@sentry/browser`.
  - `demo/buggy-shop-api`: a tiny Flask/FastAPI backend with deliberate server bugs, instrumented with `sentry-sdk` for Python. It sends context lines and local variables, which gives rich stack traces and better Insights.
- JS source fetching for context lines is deferred to phase 3, together with source maps.

## Consequences
- Aligned with Sentry's frontend. The demo shows compatibility with two official SDKs.
- No component-library dependency. A small set of in-house components (Button, Badge, Table, Panel) lives in `frontend/src/components`.
