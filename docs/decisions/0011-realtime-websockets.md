# 0011. Push updates over WebSockets
- Status: Accepted
- Date: 2026-11-18

## Context
Seeing an error appear the moment it happens is the core demo moment. Polling adds latency and load.

## Decision
- Django Channels with a Redis channel layer.
- After saving, workers publish `issue.created` / `issue.updated` to group `project.<id>`.
- Clients connect to `/ws/projects/<id>/` (session-authenticated, permission-checked) and update the TanStack Query cache in place.
- Count updates are throttled: at most one `issue.updated` per issue per second.

## Consequences
- Needs an ASGI server and a Redis channel layer in every environment.
- If a client misses messages while disconnected, it refetches on reconnect.
