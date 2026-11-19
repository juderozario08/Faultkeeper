import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { keys } from "../api/hooks";
import type { Issue, Page, StreamMessage } from "../api/types";

export type StreamState = "connecting" | "live" | "offline";

/** Applies a stream message to cached queries instead of refetching everything. */
export function applyStreamMessage(client: QueryClient, org: string, project: string, message: StreamMessage) {
  const incoming = message.issue;
  client.setQueryData<Issue>(keys.issue(incoming.id), (old) => (old ? { ...old, ...incoming } : old));

  let found = false;
  client.setQueriesData<Page<Issue>>({ queryKey: keys.issues(org, project) }, (page) => {
    if (!page) return page;
    const results = page.results.map((issue) => {
      if (issue.id !== incoming.id) return issue;
      found = true;
      return { ...issue, ...incoming, stats_24h: bumpSparkline(issue.stats_24h, incoming.times_seen - issue.times_seen) };
    });
    return { ...page, results };
  });

  if (message.type === "issue.created" || !found) {
    // New issue (or one not on screen): let the list refetch with the right filters/sort.
    client.invalidateQueries({ queryKey: keys.issues(org, project) });
  }
  client.invalidateQueries({ queryKey: ["stats", org, project] });
}

function bumpSparkline(series: Issue["stats_24h"], delta: number) {
  if (!series?.length || delta <= 0) return series;
  const copy = series.map(([t, c]) => [t, c] as [number, number]);
  copy[copy.length - 1][1] += delta;
  return copy;
}

export function useProjectStream(org: string, project: string, projectId: number | undefined): StreamState {
  const client = useQueryClient();
  const [state, setState] = useState<StreamState>("connecting");

  useEffect(() => {
    if (!projectId) return;
    let socket: WebSocket | null = null;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${scheme}://${window.location.host}/ws/projects/${projectId}/`);
      setState("connecting");
      socket.onopen = () => {
        if (retry > 0) client.invalidateQueries({ queryKey: keys.issues(org, project) }); // catch up
        retry = 0;
        setState("live");
      };
      socket.onmessage = (event) => applyStreamMessage(client, org, project, JSON.parse(event.data));
      socket.onclose = (event) => {
        setState("offline");
        if (closed || event.code === 4403) return;
        retry += 1;
        timer = setTimeout(connect, Math.min(1000 * 2 ** retry, 15000));
      };
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, [client, org, project, projectId]);

  return state;
}
