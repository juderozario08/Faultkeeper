import styled from "@emotion/styled";
import type { Breadcrumb, EventPayload, TagSummary } from "../../api/types";
import { Panel, PanelBody, PanelHeader, Subtle } from "../../components/ui";
import { color } from "../../theme/tokens";

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  th {
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: ${color.textSubtle};
    padding: 6px 12px;
    border-bottom: 1px solid ${color.border};
  }
  td {
    padding: 6px 12px;
    border-bottom: 1px solid ${color.border};
    vertical-align: top;
    color: ${color.textMuted};
  }
  tr:last-of-type td {
    border-bottom: 0;
  }
`;

function crumbTime(ts: Breadcrumb["timestamp"]) {
  if (ts == null) return "";
  const date = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString();
}

function crumbText(crumb: Breadcrumb) {
  if (crumb.message) return crumb.message;
  if (crumb.data) {
    const { method, url, status_code } = crumb.data as Record<string, unknown>;
    if (url) return [method, url, status_code].filter(Boolean).join(" ");
    return JSON.stringify(crumb.data);
  }
  return "";
}

export function BreadcrumbsPanel({ crumbs }: { crumbs: Breadcrumb[] }) {
  if (!crumbs.length) return null;
  const recent = [...crumbs].reverse().slice(0, 50);
  return (
    <Panel>
      <PanelHeader>
        Breadcrumbs <Subtle>{crumbs.length} total · most recent first</Subtle>
      </PanelHeader>
      <div style={{ overflowX: "auto" }}>
        <Table>
          <thead>
            <tr>
              <th>Category</th>
              <th>Description</th>
              <th>Level</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((c, i) => (
              <tr key={i}>
                <td style={{ color: color.accentText, whiteSpace: "nowrap" }}>{c.category || c.type || "default"}</td>
                <td style={{ color: color.text, wordBreak: "break-word" }}>{crumbText(c)}</td>
                <td>{c.level ?? "info"}</td>
                <td style={{ whiteSpace: "nowrap" }}>{crumbTime(c.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </Panel>
  );
}

const Bar = styled.div`
  height: 6px;
  border-radius: 3px;
  background: ${color.border};
  overflow: hidden;
  margin-top: 3px;
  div {
    height: 100%;
    background: ${color.accentAlt};
  }
`;

export function TagsPanel({ tags }: { tags: TagSummary[] }) {
  if (!tags.length) return null;
  return (
    <Panel>
      <PanelHeader>Tags</PanelHeader>
      <PanelBody style={{ display: "grid", gap: 12 }}>
        {tags.map((tag) => {
          const top = tag.top[0];
          const share = top ? Math.round((top.count / tag.total) * 100) : 0;
          return (
            <div key={tag.key}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, fontSize: 12.5 }}>
                <span style={{ color: color.textMuted }}>{tag.key}</span>
                <span style={{ color: color.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={top?.value}>
                  {top?.value} <Subtle>{share}%</Subtle>
                </span>
              </div>
              <Bar aria-hidden>
                <div style={{ width: `${share}%` }} />
              </Bar>
            </div>
          );
        })}
      </PanelBody>
    </Panel>
  );
}

const KV = styled.dl`
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 16px;
  margin: 0;
  font-size: 12.5px;
  dt {
    color: ${color.textMuted};
  }
  dd {
    margin: 0;
    color: ${color.text};
    word-break: break-word;
  }
`;

function flat(value: unknown): string {
  return typeof value === "object" && value !== null ? JSON.stringify(value) : String(value);
}

export function ContextPanel({ payload }: { payload: EventPayload }) {
  const contexts = Object.entries(payload.contexts ?? {}).filter(([, v]) => v && typeof v === "object");
  const request = payload.request;
  const sdk = payload.sdk;
  if (!contexts.length && !request && !sdk) return null;
  return (
    <Panel>
      <PanelHeader>Context</PanelHeader>
      <PanelBody style={{ display: "grid", gap: 14 }}>
        {request?.url && (
          <div>
            <Subtle>Request</Subtle>
            <KV>
              <dt>URL</dt>
              <dd>
                {request.method ? `${request.method} ` : ""}
                {request.url}
              </dd>
            </KV>
          </div>
        )}
        {contexts.map(([name, ctx]) => (
          <div key={name}>
            <Subtle style={{ textTransform: "capitalize" }}>{name}</Subtle>
            <KV>
              {Object.entries(ctx)
                .filter(([k]) => k !== "type")
                .slice(0, 8)
                .map(([k, v]) => (
                  <div key={k} style={{ display: "contents" }}>
                    <dt>{k}</dt>
                    <dd>{flat(v)}</dd>
                  </div>
                ))}
            </KV>
          </div>
        ))}
        {sdk?.name && (
          <div>
            <Subtle>SDK</Subtle>
            <KV>
              <dt>name</dt>
              <dd>
                {sdk.name} {sdk.version}
              </dd>
            </KV>
          </div>
        )}
      </PanelBody>
    </Panel>
  );
}
