import styled from "@emotion/styled";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useEvent, useIssue, useIssueTags, useProjects, useUpdateIssueStatus } from "../../api/hooks";
import type { IssueStatus } from "../../api/types";
import { Chart } from "../../components/Chart";
import {
  Button,
  ErrorState,
  LevelBadge,
  Loading,
  Muted,
  Panel,
  PanelBody,
  PanelHeader,
  StatusBadge,
  Subtle,
} from "../../components/ui";
import { useProjectStream } from "../../realtime/useProjectStream";
import { color } from "../../theme/tokens";
import { formatCount, formatDateTime, timeAgo } from "../../utils/format";
import { BreadcrumbsPanel, ContextPanel, TagsPanel } from "./EventSections";
import { ExceptionView } from "./StackTrace";

const Grid = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
  @media (max-width: 960px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

const Stats = styled.div`
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: ${color.border};
  border-top: 1px solid ${color.border};
  > div {
    background: ${color.surface};
    padding: 10px 14px;
  }
  @media (max-width: 720px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
`;

const StatLabel = styled.div`
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: ${color.textSubtle};
`;

const StatValue = styled.div`
  font-weight: 600;
  margin-top: 2px;
  color: ${color.text};
`;

export function IssueDetailPage() {
  const { org = "", project = "", issueId = "" } = useParams();
  const id = Number(issueId);
  const [params, setParams] = useSearchParams();
  const eventId = params.get("event") ?? "latest";

  const projects = useProjects(org);
  useProjectStream(org, project, projects.data?.find((p) => p.slug === project)?.id);
  const issue = useIssue(id);
  const event = useEvent(id, eventId);
  const tags = useIssueTags(id);
  const setStatus = useUpdateIssueStatus(id);

  if (issue.isLoading) return <Loading />;
  if (issue.error || !issue.data) return <ErrorState error={issue.error} />;
  const group = issue.data;
  const payload = event.data?.payload;
  const exceptions = payload?.exception?.values ?? [];

  const actions: { status: IssueStatus; label: string }[] =
    group.status === "unresolved"
      ? [
          { status: "resolved", label: "✓ Resolve" },
          { status: "ignored", label: "Ignore" },
        ]
      : [{ status: "unresolved", label: "Unresolve" }];

  const goTo = (target: string | null | undefined) => target && setParams({ event: target });

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div>
        <Link to={`/${org}/${project}/issues`}>← All issues</Link>
      </div>

      <Panel>
        <PanelBody>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap" }}>
            <div style={{ minWidth: 0 }}>
              <h1 style={{ margin: 0, fontSize: 20, wordBreak: "break-word" }}>{group.title}</h1>
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6, flexWrap: "wrap" }}>
                <LevelBadge level={group.level} />
                <StatusBadge status={group.status} substatus={group.substatus} />
                <Muted style={{ fontFamily: "ui-monospace, monospace", fontSize: 12.5 }}>{group.culprit}</Muted>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              {actions.map((a) => (
                <Button
                  key={a.status}
                  variant={a.status === "resolved" ? "primary" : "default"}
                  disabled={setStatus.isPending}
                  onClick={() => setStatus.mutate(a.status)}
                >
                  {a.label}
                </Button>
              ))}
            </div>
          </div>
        </PanelBody>
        <Stats>
          <div>
            <StatLabel>Events</StatLabel>
            <StatValue>{formatCount(group.times_seen)}</StatValue>
          </div>
          <div>
            <StatLabel>First seen</StatLabel>
            <StatValue title={formatDateTime(group.first_seen)}>{timeAgo(group.first_seen)}</StatValue>
          </div>
          <div>
            <StatLabel>Last seen</StatLabel>
            <StatValue title={formatDateTime(group.last_seen)}>{timeAgo(group.last_seen)}</StatValue>
          </div>
          <div>
            <StatLabel>First release</StatLabel>
            <StatValue>{group.first_release ?? "—"}</StatValue>
          </div>
        </Stats>
      </Panel>

      <Grid>
        <div style={{ display: "grid", gap: 16, minWidth: 0 }}>
          <Panel>
            <PanelHeader>
              <span>
                Event{" "}
                {event.data && (
                  <Subtle style={{ fontFamily: "ui-monospace, monospace" }}>
                    {event.data.event_id.slice(0, 8)} · {formatDateTime(event.data.timestamp)}
                    {event.data.release ? ` · ${event.data.release}` : ""}
                    {event.data.environment ? ` · ${event.data.environment}` : ""}
                  </Subtle>
                )}
              </span>
              <span style={{ display: "flex", gap: 6 }}>
                <Button size="sm" disabled={!event.data?.previous_event_id} onClick={() => goTo(event.data?.previous_event_id)}>
                  ← Older
                </Button>
                <Button size="sm" disabled={!event.data?.next_event_id} onClick={() => goTo(event.data?.next_event_id)}>
                  Newer →
                </Button>
                <Button size="sm" disabled={eventId === "latest"} onClick={() => setParams({})}>
                  Latest
                </Button>
              </span>
            </PanelHeader>
            {event.isLoading ? (
              <Loading />
            ) : event.error ? (
              <ErrorState error={event.error} />
            ) : exceptions.length ? (
              [...exceptions].reverse().map((exc, i) => (
                <div key={i} style={{ borderTop: i ? `1px solid ${color.border}` : undefined }}>
                  {i > 0 && <Subtle style={{ display: "block", padding: "8px 14px 0" }}>Caused by</Subtle>}
                  <ExceptionView exception={exc} />
                </div>
              ))
            ) : (
              <PanelBody>
                <div style={{ fontWeight: 600 }}>Message</div>
                <pre style={{ whiteSpace: "pre-wrap", margin: "6px 0 0" }}>{payload?.logentry?.formatted ?? "(no message)"}</pre>
              </PanelBody>
            )}
          </Panel>
          {payload && <BreadcrumbsPanel crumbs={payload.breadcrumbs?.values ?? []} />}
        </div>

        <div style={{ display: "grid", gap: 16, minWidth: 0 }}>
          {group.stats_24h && (
            <Panel>
              <PanelHeader>Last 24 hours</PanelHeader>
              <PanelBody style={{ padding: "4px 8px" }}>
                <Chart series={group.stats_24h} height={110} />
              </PanelBody>
            </Panel>
          )}
          {tags.data && <TagsPanel tags={tags.data} />}
          {payload && <ContextPanel payload={payload} />}
        </div>
      </Grid>
    </div>
  );
}
