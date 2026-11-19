export type Level = "fatal" | "error" | "warning" | "info" | "debug";
export type IssueStatus = "unresolved" | "resolved" | "ignored";

export interface User {
  id: number;
  email: string;
  name: string;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  platform: string;
  organization: string;
}

export interface ProjectKey {
  id: number;
  label: string;
  public_key: string;
  dsn: string;
  is_active: boolean;
  rate_limit_per_minute: number;
}

export type Series = [number, number][];

export interface Issue {
  id: number;
  title: string;
  culprit: string;
  type: string;
  level: Level;
  platform: string;
  status: IssueStatus;
  substatus: "new" | "ongoing" | "regressed";
  first_seen: string;
  last_seen: string;
  times_seen: number;
  first_release: string | null;
  project: { id: number; slug: string };
  stats_24h?: Series;
}

export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Frame {
  filename?: string;
  abs_path?: string;
  module?: string;
  function?: string;
  lineno?: number;
  colno?: number;
  in_app?: boolean;
  context_line?: string;
  pre_context?: string[];
  post_context?: string[];
  vars?: Record<string, unknown>;
}

export interface ExceptionValue {
  type: string;
  value: string;
  module?: string;
  mechanism?: { type?: string; handled?: boolean };
  stacktrace?: { frames: Frame[] };
}

export interface Breadcrumb {
  timestamp?: string | number;
  type?: string;
  category?: string;
  message?: string;
  level?: string;
  data?: Record<string, unknown>;
}

export interface EventPayload {
  event_id: string;
  timestamp: string;
  level: Level;
  platform: string;
  release?: string;
  environment?: string;
  logentry?: { formatted: string };
  exception?: { values: ExceptionValue[] };
  breadcrumbs?: { values: Breadcrumb[] };
  tags?: [string, string][];
  contexts?: Record<string, Record<string, unknown>>;
  request?: { url?: string; method?: string; headers?: Record<string, string> | [string, string][]; query_string?: unknown };
  user?: Record<string, unknown>;
  sdk?: { name?: string; version?: string };
}

export interface EventDetail {
  event_id: string;
  timestamp: string;
  level: Level;
  release: string;
  environment: string;
  title: string;
  platform: string;
  group_id: number;
  received_at: string;
  payload: EventPayload;
  next_event_id: string | null;
  previous_event_id: string | null;
}

export interface TagSummary {
  key: string;
  total: number;
  top: { value: string; count: number }[];
}

export interface IssueFilters {
  status: IssueStatus | "all";
  level: string;
  release: string;
  environment: string;
  q: string;
  sort: "last_seen" | "first_seen" | "times_seen";
}

export interface StreamMessage {
  type: "issue.created" | "issue.updated";
  issue: Issue;
}
