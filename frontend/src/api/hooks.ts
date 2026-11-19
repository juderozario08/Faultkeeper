import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, ensureCsrf } from "./client";
import type {
  EventDetail,
  InsightState,
  Issue,
  IssueFilters,
  IssueStatus,
  Organization,
  Page,
  Project,
  ProjectKey,
  Series,
  TagSummary,
  User,
} from "./types";

export const keys = {
  me: ["me"] as const,
  orgs: ["orgs"] as const,
  projects: (org: string) => ["projects", org] as const,
  projectKeys: (org: string, project: string) => ["project-keys", org, project] as const,
  issues: (org: string, project: string) => ["issues", org, project] as const,
  issueList: (org: string, project: string, filters: IssueFilters, cursor: string | null) =>
    ["issues", org, project, filters, cursor] as const,
  issue: (id: number) => ["issue", id] as const,
  event: (issueId: number, eventId: string) => ["event", issueId, eventId] as const,
  tags: (issueId: number) => ["tags", issueId] as const,
  insights: (issueId: number) => ["insights", issueId] as const,
  stats: (org: string, project: string, period: string) => ["stats", org, project, period] as const,
  filters: (org: string, project: string) => ["filters", org, project] as const,
};

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async () => {
      try {
        return await api<User>("auth/me/");
      } catch (error) {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
        throw error;
      }
    },
    staleTime: Infinity,
  });
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      await ensureCsrf();
      return api<User>("auth/login/", { method: "POST", json: credentials });
    },
    onSuccess: (user) => {
      client.clear();
      client.setQueryData(keys.me, user);
    },
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("auth/logout/", { method: "POST" }),
    onSuccess: () => {
      client.clear();
      client.setQueryData(keys.me, null);
    },
  });
}

export function useOrganizations() {
  return useQuery({ queryKey: keys.orgs, queryFn: () => api<Organization[]>("organizations/") });
}

export function useProjects(org: string | undefined) {
  return useQuery({
    queryKey: keys.projects(org ?? ""),
    queryFn: () => api<Project[]>(`organizations/${org}/projects/`),
    enabled: Boolean(org),
  });
}

export function useProjectKeys(org: string, project: string) {
  return useQuery({
    queryKey: keys.projectKeys(org, project),
    queryFn: () => api<ProjectKey[]>(`projects/${org}/${project}/keys/`),
  });
}

function issueQuery(filters: IssueFilters): string {
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(filters)) if (value) params.set(name, value);
  return params.toString();
}

export function useIssues(org: string, project: string, filters: IssueFilters, cursor: string | null) {
  return useQuery({
    queryKey: keys.issueList(org, project, filters, cursor),
    queryFn: () => {
      if (cursor) {
        // DRF returns absolute "next"/"previous" URLs; keep only path + query (same origin).
        const url = new URL(cursor, window.location.origin);
        return api<Page<Issue>>(url.pathname + url.search);
      }
      return api<Page<Issue>>(`projects/${org}/${project}/issues/?${issueQuery(filters)}`);
    },
    placeholderData: keepPreviousData,
  });
}

export function useIssue(id: number) {
  return useQuery({ queryKey: keys.issue(id), queryFn: () => api<Issue>(`issues/${id}/`) });
}

export function useEvent(issueId: number, eventId: string) {
  return useQuery({
    queryKey: keys.event(issueId, eventId),
    queryFn: () => api<EventDetail>(`issues/${issueId}/events/${eventId}/`),
    placeholderData: keepPreviousData,
  });
}

export function useIssueTags(issueId: number) {
  return useQuery({ queryKey: keys.tags(issueId), queryFn: () => api<TagSummary[]>(`issues/${issueId}/tags/`) });
}

export function useProjectStats(org: string, project: string, period: "24h" | "14d") {
  const interval = period === "24h" ? "1h" : "1d";
  return useQuery({
    queryKey: keys.stats(org, project, period),
    queryFn: () => api<Series>(`projects/${org}/${project}/stats/?period=${period}&interval=${interval}`),
  });
}

export function useProjectFilters(org: string, project: string) {
  return useQuery({
    queryKey: keys.filters(org, project),
    queryFn: () => api<{ releases: string[]; environments: string[] }>(`projects/${org}/${project}/filters/`),
  });
}

export function useUpdateIssueStatus(issueId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (status: IssueStatus) => api<Issue>(`issues/${issueId}/`, { method: "PUT", json: { status } }),
    onSuccess: (issue) => {
      client.setQueryData(keys.issue(issueId), issue);
      client.invalidateQueries({ queryKey: ["issues"] });
    },
  });
}

export function useInsights(issueId: number) {
  return useQuery({ queryKey: keys.insights(issueId), queryFn: () => api<InsightState>(`issues/${issueId}/insights/`) });
}

export function useGenerateInsight(issueId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<InsightState>(`issues/${issueId}/insights/`, { method: "POST" }),
    onSuccess: (state) => client.setQueryData(keys.insights(issueId), state),
  });
}
