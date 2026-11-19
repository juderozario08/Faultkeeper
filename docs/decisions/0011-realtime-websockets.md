# 0011. Push updates over WebSockets
- Status: Accepted
- Date: 2026-11-18

## Context
Seeing an error appear the moment it happens is the core demo moment. Polling adds latency and load.

## Decision
- Django Channels with a Redis channel layer.
- After saving, workers publish `issue.created` / `issue.updated` to group `project.<id>`.
- Clients connect to `/ws/projects/<id>/` (session-authenticated, permission-checked) and update the TanStack Query cache in place.
- Every processed event publishes an update (fine at phase 1 volumes). Per-issue throttling (at most one `issue.updated` per second) arrives in phase 2 with the Redis count buffer, which already batches updates.
- Rejected connections close with code `4403`.

## Consequences
- Needs an ASGI server and a Redis channel layer in every environment.
- If a client misses messages while disconnected, it refetches on reconnect.
