import styled from "@emotion/styled";
import { useGenerateInsight, useInsights } from "../../api/hooks";
import { Button, Panel, PanelBody, PanelHeader, Subtle } from "../../components/ui";
import { color } from "../../theme/tokens";
import { timeAgo } from "../../utils/format";

const Section = styled.div`
  h3 {
    margin: 0 0 4px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: ${color.accentText};
  }
  p {
    margin: 0;
    white-space: pre-wrap;
    color: ${color.text};
  }
`;

const Spark = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden style={{ fill: color.accentAlt }}>
    <path d="M12 2l2.2 6.6L21 11l-6.8 2.4L12 20l-2.2-6.6L3 11l6.8-2.4z" />
  </svg>
);

export function InsightsPanel({ issueId }: { issueId: number }) {
  const state = useInsights(issueId);
  const generate = useGenerateInsight(issueId);
  const insight = state.data?.insight;
  const available = state.data?.available ?? false;

  return (
    <Panel aria-busy={generate.isPending}>
      <PanelHeader>
        <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
          <Spark /> Issue Insights
        </span>
        <Button
          size="sm"
          variant={insight ? "default" : "primary"}
          disabled={!available || generate.isPending}
          onClick={() => generate.mutate()}
        >
          {generate.isPending ? "Analyzing…" : insight ? "Regenerate" : "Explain this issue"}
        </Button>
      </PanelHeader>
      <PanelBody style={{ display: "grid", gap: 12 }}>
        {generate.isPending && <Subtle>Reading the stack trace and breadcrumbs… local models can take up to a minute.</Subtle>}
        {generate.error && (
          <div role="alert" style={{ color: color.dangerText, fontSize: 13 }}>
            {generate.error.message}
          </div>
        )}
        {insight ? (
          <>
            <Section>
              <h3>Summary</h3>
              <p>{insight.summary}</p>
            </Section>
            <Section>
              <h3>Root cause</h3>
              <p>{insight.root_cause}</p>
            </Section>
            <Section>
              <h3>Suggested fix</h3>
              <p>{insight.suggested_fix}</p>
            </Section>
            <Subtle>
              Generated {timeAgo(insight.created_at)} by {insight.model} ({insight.provider}). AI output can be wrong; verify before
              changing code.
            </Subtle>
          </>
        ) : (
          !generate.isPending &&
          state.data && (
            <Subtle style={{ fontSize: 13 }}>
              {available
                ? "Get a plain-English root cause and suggested fix from the latest event. No user data is sent to the model."
                : state.data.provider_detail}
            </Subtle>
          )
        )}
      </PanelBody>
    </Panel>
  );
}
