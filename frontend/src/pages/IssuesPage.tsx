import styled from "@emotion/styled";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useIssues, useProjectFilters, useProjects, useProjectStats } from "../api/hooks";
import type { Issue, IssueFilters } from "../api/types";
import { Sparkline } from "../components/Sparkline";
import { Chart } from "../components/Chart";
import {
  Button,
  EmptyState,
  ErrorState,
  Input,
  LevelBadge,
  Loading,
  Muted,
  Panel,
  PanelBody,
  PanelHeader,
  Select,
  StatusBadge,
  Subtle,
} from "../components/ui";
import { useProjectStream, type StreamState } from "../realtime/useProjectStream";
import { color } from "../theme/tokens";
import { formatCount, timeAgo } from "../utils/format";

const DEFAULT_FILTERS: IssueFilters = { status: "unresolved", level: "", release: "", environment: "", q: "", sort: "last_seen" };

const Toolbar = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
`;

const Tabs = styled.div`
  display: inline-flex;
  border: 1px solid ${color.border};
  border-radius: 6px;
  overflow: hidden;
`;

const Tab = styled.button<{ active: boolean }>`
  border: 0;
  font: inherit;
  font-size: 13px;
  padding: 6px 12px;
  cursor: pointer;
  background: ${({ active }) => (active ? color.surfaceHover : color.surface)};
  color: ${({ active }) => (active ? color.text : color.textMuted)};
  font-weight: ${({ active }) => (active ? 600 : 400)};
`;

const Row = styled(Link)`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px 80px 110px;
  gap: 16px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid ${color.border};
  color: inherit;
  &:hover {
    background: ${color.surfaceHover};
    text-decoration: none;
  }
  &:last-of-type {
    border-bottom: 0;
  }
  @media (max-width: 720px) {
    grid-template-columns: minmax(0, 1fr) 70px;
    .wide {
      display: none;
    }
  }
`;

const HeadRow = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px 80px 110px;
  gap: 16px;
  padding: 8px 14px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: ${color.textSubtle};
  border-bottom: 1px solid ${color.border};
  @media (max-width: 720px) {
    grid-template-columns: minmax(0, 1fr) 70px;
    .wide {
      display: none;
    }
  }
`;

const Title = styled.div`
  font-weight: 600;
  color: ${color.text};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const Meta = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 4px;
  font-size: 12px;
  color: ${color.textMuted};
  min-width: 0;
  span.culprit {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

const LiveDot = styled.span<{ state: StreamState }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: ${color.textMuted};
  &::before {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${({ state }) => (state === "live" ? color.success : state === "connecting" ? color.warning : color.danger)};
  }
`;

function IssueRow({ issue, org, project }: { issue: Issue; org: string; project: string }) {
  return (
    <Row to={`/${org}/${project}/issues/${issue.id}`}>
      <div style={{ minWidth: 0 }}>
        <Title title={issue.title}>{issue.title}</Title>
        <Meta>
          <LevelBadge level={issue.level} />
          {issue.substatus !== "ongoing" && issue.status === "unresolved" && (
            <StatusBadge status={issue.status} substatus={issue.substatus} />
          )}
          {issue.status !== "unresolved" && <StatusBadge status={issue.status} />}
          <span className="culprit">{issue.culprit}</span>
          <Subtle style={{ whiteSpace: "nowrap" }}>
            {timeAgo(issue.last_seen)} · first seen {timeAgo(issue.first_seen)}
          </Subtle>
        </Meta>
      </div>
      <div className="wide">
        <Sparkline series={issue.stats_24h} />
      </div>
      <div style={{ textAlign: "right", fontWeight: 600 }}>{formatCount(issue.times_seen)}</div>
      <div className="wide" style={{ textAlign: "right" }}>
        <Muted>{timeAgo(issue.last_seen)}</Muted>
      </div>
    </Row>
  );
}

export function IssuesPage() {
  const { org = "", project = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const filters: IssueFilters = useMemo(
    () => ({ ...DEFAULT_FILTERS, ...Object.fromEntries(params.entries()) }) as IssueFilters,
    [params],
  );
  const [cursor, setCursor] = useState<string | null>(null);
  const [search, setSearch] = useState(filters.q);

  const projects = useProjects(org);
  const projectId = projects.data?.find((p) => p.slug === project)?.id;
  const stream = useProjectStream(org, project, projectId);
  const issues = useIssues(org, project, filters, cursor);
  const stats = useProjectStats(org, project, "24h");
  const filterValues = useProjectFilters(org, project);

  const setFilter = (name: keyof IssueFilters, value: string) => {
    const next = new URLSearchParams(params);
    if (value && value !== DEFAULT_FILTERS[name]) next.set(name, value);
    else next.delete(name);
    setCursor(null);
    setParams(next, { replace: true });
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Panel>
        <PanelHeader>
          <span>Events in the last 24 hours</span>
          <LiveDot state={stream} aria-live="polite">
            {stream === "live" ? "Live" : stream === "connecting" ? "Connecting…" : "Offline, retrying"}
          </LiveDot>
        </PanelHeader>
        <PanelBody style={{ paddingTop: 4, paddingBottom: 4 }}>
          {stats.data ? <Chart series={stats.data} height={120} /> : <div style={{ height: 120 }} />}
        </PanelBody>
      </Panel>

      <div>
        <Toolbar>
          <Tabs role="tablist" aria-label="Status">
            {(["unresolved", "resolved", "ignored", "all"] as const).map((s) => (
              <Tab key={s} role="tab" aria-selected={filters.status === s} active={filters.status === s} onClick={() => setFilter("status", s)}>
                {s[0].toUpperCase() + s.slice(1)}
              </Tab>
            ))}
          </Tabs>
          <form
            style={{ flex: "1 1 220px", display: "flex" }}
            onSubmit={(e) => {
              e.preventDefault();
              setFilter("q", search.trim());
            }}
          >
            <Input
              type="search"
              placeholder="Search titles and culprits…"
              aria-label="Search issues"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ flex: 1 }}
            />
          </form>
          <Select aria-label="Level" value={filters.level} onChange={(e) => setFilter("level", e.target.value)}>
            <option value="">All levels</option>
            {["fatal", "error", "warning", "info", "debug"].map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </Select>
          <Select aria-label="Environment" value={filters.environment} onChange={(e) => setFilter("environment", e.target.value)}>
            <option value="">All environments</option>
            {filterValues.data?.environments.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </Select>
          <Select aria-label="Release" value={filters.release} onChange={(e) => setFilter("release", e.target.value)}>
            <option value="">All releases</option>
            {filterValues.data?.releases.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </Select>
          <Select aria-label="Sort" value={filters.sort} onChange={(e) => setFilter("sort", e.target.value)}>
            <option value="last_seen">Last seen</option>
            <option value="first_seen">First seen</option>
            <option value="times_seen">Events</option>
          </Select>
        </Toolbar>

        <Panel>
          <HeadRow>
            <span>Issue</span>
            <span className="wide">Last 24h</span>
            <span style={{ textAlign: "right" }}>Events</span>
            <span className="wide" style={{ textAlign: "right" }}>
              Last seen
            </span>
          </HeadRow>
          {issues.isLoading ? (
            <Loading />
          ) : issues.error ? (
            <ErrorState error={issues.error} />
          ) : issues.data?.results.length ? (
            issues.data.results.map((issue) => <IssueRow key={issue.id} issue={issue} org={org} project={project} />)
          ) : (
            <EmptyState title={filters.status === "unresolved" ? "No unresolved issues 🎉" : "No issues match"}>
              Send an error from an app using this project's DSN (see Settings).
            </EmptyState>
          )}
        </Panel>
        {(issues.data?.previous || issues.data?.next) && (
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
            <Button size="sm" disabled={!issues.data.previous} onClick={() => setCursor(issues.data!.previous)}>
              ← Previous
            </Button>
            <Button size="sm" disabled={!issues.data.next} onClick={() => setCursor(issues.data!.next)}>
              Next →
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
