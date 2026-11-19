import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { keys } from "../api/hooks";
import type { Issue, IssueFilters, Page } from "../api/types";
import { applyStreamMessage } from "./useProjectStream";

const filters: IssueFilters = { status: "unresolved", level: "", release: "", environment: "", q: "", sort: "last_seen" };

function issue(overrides: Partial<Issue> = {}): Issue {
  return {
    id: 1,
    title: "TypeError: boom",
    culprit: "src/app.ts in checkout",
    type: "error",
    level: "error",
    platform: "javascript",
    status: "unresolved",
    substatus: "new",
    first_seen: "2026-11-18T10:00:00Z",
    last_seen: "2026-11-18T10:00:00Z",
    times_seen: 1,
    first_release: null,
    project: { id: 1, slug: "web" },
    stats_24h: [
      [1, 0],
      [2, 1],
    ],
    ...overrides,
  };
}

describe("applyStreamMessage", () => {
  it("patches an issue already in the list and bumps its sparkline", () => {
    const client = new QueryClient();
    const listKey = keys.issueList("acme", "web", filters, null);
    client.setQueryData<Page<Issue>>(listKey, { next: null, previous: null, results: [issue()] });

    applyStreamMessage(client, "acme", "web", {
      type: "issue.updated",
      issue: issue({ times_seen: 4, last_seen: "2026-11-18T11:00:00Z", stats_24h: undefined }),
    });

    const updated = client.getQueryData<Page<Issue>>(listKey)!.results[0];
    expect(updated.times_seen).toBe(4);
    expect(updated.last_seen).toBe("2026-11-18T11:00:00Z");
    expect(updated.stats_24h?.at(-1)?.[1]).toBe(4); // 1 + 3 new events
    expect(client.getQueryState(listKey)?.isInvalidated).toBe(false);
  });

  it("invalidates the list when a new issue is created", () => {
    const client = new QueryClient();
    const listKey = keys.issueList("acme", "web", filters, null);
    client.setQueryData<Page<Issue>>(listKey, { next: null, previous: null, results: [] });

    applyStreamMessage(client, "acme", "web", { type: "issue.created", issue: issue({ id: 2 }) });

    expect(client.getQueryState(listKey)?.isInvalidated).toBe(true);
  });

  it("updates a cached issue detail", () => {
    const client = new QueryClient();
    client.setQueryData(keys.issue(1), issue());
    applyStreamMessage(client, "acme", "web", { type: "issue.updated", issue: issue({ status: "resolved" }) });
    expect(client.getQueryData<Issue>(keys.issue(1))?.status).toBe("resolved");
  });
});
