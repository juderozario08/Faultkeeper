# 0010. Frontend stack
- Status: Accepted
- Date: 2026-11-18

## Context
Sentry's UI is React + TypeScript, styled with Emotion, with charts in ECharts.

## Decision
- React + TypeScript + Vite, React Router, TanStack Query for server state, Emotion for styling, ECharts for charts.
- Vitest + React Testing Library; ESLint; `tsc --noEmit` in CI.
- In development, Vite proxies `/api` and `/ws` to Django so the session cookie stays on the same origin.
- `demo/buggy-shop` is a separate small Vite app with deliberate bugs, instrumented with `@sentry/browser`.

## Consequences
- Aligned with Sentry's frontend.
- No component-library dependency. A small set of in-house components (Button, Badge, Table, Panel) lives in `frontend/src/components`.
