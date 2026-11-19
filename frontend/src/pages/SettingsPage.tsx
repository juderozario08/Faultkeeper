import styled from "@emotion/styled";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useProjectKeys, useProjects } from "../api/hooks";
import { Button, ErrorState, Loading, Panel, PanelBody, PanelHeader, Subtle } from "../components/ui";
import { color } from "../theme/tokens";

const Code = styled.pre`
  margin: 0;
  padding: 12px 14px;
  background: ${color.bg};
  border: 1px solid ${color.border};
  border-radius: 6px;
  overflow-x: auto;
  color: ${color.text};
`;

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      size="sm"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? "Copied ✓" : "Copy"}
    </Button>
  );
}

function snippets(dsn: string) {
  return {
    "JavaScript (browser)": `import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: "${dsn}",
  release: "my-app@1.0.0",
  environment: "production",
});`,
    Python: `import sentry_sdk

sentry_sdk.init(
    dsn="${dsn}",
    release="my-app@1.0.0",
    environment="production",
)`,
  };
}

export function SettingsPage() {
  const { org = "", project = "" } = useParams();
  const projects = useProjects(org);
  const keys = useProjectKeys(org, project);
  const current = projects.data?.find((p) => p.slug === project);

  if (keys.isLoading) return <Loading />;
  if (keys.error) return <ErrorState error={keys.error} />;
  const key = keys.data?.find((k) => k.is_active) ?? keys.data?.[0];

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h1 style={{ margin: 0, fontSize: 20 }}>{current?.name ?? project} · Settings</h1>
      {key && (
        <>
          <Panel>
            <PanelHeader>
              Client key (DSN) <CopyButton text={key.dsn} />
            </PanelHeader>
            <PanelBody style={{ display: "grid", gap: 8 }}>
              <Code>{key.dsn}</Code>
              <Subtle>
                Rate limit: {key.rate_limit_per_minute.toLocaleString()} events/minute · works with the official Sentry SDKs.
              </Subtle>
            </PanelBody>
          </Panel>
          {Object.entries(snippets(key.dsn)).map(([name, code]) => (
            <Panel key={name}>
              <PanelHeader>
                {name} <CopyButton text={code} />
              </PanelHeader>
              <PanelBody>
                <Code>{code}</Code>
              </PanelBody>
            </Panel>
          ))}
        </>
      )}
    </div>
  );
}
