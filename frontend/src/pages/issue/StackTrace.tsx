import styled from "@emotion/styled";
import { useState } from "react";
import type { ExceptionValue, Frame } from "../../api/types";
import { Button, Subtle } from "../../components/ui";
import { color } from "../../theme/tokens";

const FrameRow = styled.div<{ inApp: boolean }>`
  border-top: 1px solid ${color.border};
  background: ${({ inApp }) => (inApp ? color.surface : color.bg)};
  border-left: 3px solid ${({ inApp }) => (inApp ? color.teal : "transparent")};
`;

const FrameHeader = styled.button`
  all: unset;
  box-sizing: border-box;
  display: flex;
  gap: 8px;
  align-items: baseline;
  width: 100%;
  padding: 7px 12px;
  cursor: pointer;
  font-family: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12.5px;
  color: ${color.text};
  &:hover {
    background: ${color.surfaceHover};
  }
`;

const Code = styled.pre`
  margin: 0;
  padding: 6px 0;
  overflow-x: auto;
  background: ${color.bg};
  border-top: 1px dashed ${color.border};
`;

const Line = styled.div<{ current?: boolean }>`
  display: grid;
  grid-template-columns: 56px 1fr;
  background: ${({ current }) => (current ? color.surfaceHover : "transparent")};
  color: ${({ current }) => (current ? color.text : color.textMuted)};
  span:first-of-type {
    text-align: right;
    padding-right: 14px;
    color: ${color.textSubtle};
    user-select: none;
  }
`;

const Vars = styled.table`
  width: calc(100% - 24px);
  margin: 4px 12px 10px;
  border-collapse: collapse;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 12px;
  td {
    border-top: 1px solid ${color.border};
    padding: 3px 8px;
    vertical-align: top;
    color: ${color.textMuted};
  }
  td:first-of-type {
    color: ${color.text};
    width: 160px;
  }
`;

function location(frame: Frame) {
  return frame.module || frame.filename || frame.abs_path || "<unknown>";
}

function FrameView({ frame, defaultOpen }: { frame: Frame; defaultOpen: boolean }) {
  const hasContext = Boolean(frame.context_line);
  const hasVars = Boolean(frame.vars && Object.keys(frame.vars).length);
  const [open, setOpen] = useState(defaultOpen && (hasContext || hasVars));
  const first = (frame.lineno ?? 0) - (frame.pre_context?.length ?? 0);

  return (
    <FrameRow inApp={Boolean(frame.in_app)}>
      <FrameHeader onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span style={{ color: color.textSubtle, width: 10 }}>{hasContext || hasVars ? (open ? "▾" : "▸") : ""}</span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
          {location(frame)} <span style={{ color: color.textSubtle }}>in</span>{" "}
          <strong style={{ color: color.accentText }}>{frame.function || "?"}</strong>
          {frame.lineno != null && (
            <span style={{ color: color.textSubtle }}>
              {" "}
              at line {frame.lineno}
              {frame.colno != null ? `:${frame.colno}` : ""}
            </span>
          )}
        </span>
        {!frame.in_app && <Subtle style={{ marginLeft: "auto" }}>library</Subtle>}
      </FrameHeader>
      {open && hasContext && (
        <Code>
          {frame.pre_context?.map((line, i) => (
            <Line key={`pre${i}`}>
              <span>{first + i}</span>
              <span>{line}</span>
            </Line>
          ))}
          <Line current>
            <span>{frame.lineno}</span>
            <span>{frame.context_line}</span>
          </Line>
          {frame.post_context?.map((line, i) => (
            <Line key={`post${i}`}>
              <span>{(frame.lineno ?? 0) + i + 1}</span>
              <span>{line}</span>
            </Line>
          ))}
        </Code>
      )}
      {open && hasVars && (
        <Vars aria-label="Local variables">
          <tbody>
            {Object.entries(frame.vars!).map(([k, v]) => (
              <tr key={k}>
                <td>{k}</td>
                <td>{typeof v === "string" ? v : JSON.stringify(v)}</td>
              </tr>
            ))}
          </tbody>
        </Vars>
      )}
    </FrameRow>
  );
}

export function ExceptionView({ exception }: { exception: ExceptionValue }) {
  const frames = exception.stacktrace?.frames ?? [];
  const hasInApp = frames.some((f) => f.in_app);
  const [showAll, setShowAll] = useState(!hasInApp);
  // Most recent call first, like Sentry.
  const ordered = [...frames].reverse().filter((f) => showAll || f.in_app);
  const firstInApp = ordered.findIndex((f) => f.in_app);

  return (
    <div>
      <div style={{ padding: "12px 14px" }}>
        <div style={{ fontWeight: 700, color: color.dangerText }}>{exception.type}</div>
        <div style={{ color: color.text, marginTop: 2, wordBreak: "break-word" }}>{exception.value}</div>
        {exception.mechanism && (
          <Subtle>
            mechanism: {exception.mechanism.type ?? "generic"} · handled: {String(exception.mechanism.handled ?? "unknown")}
          </Subtle>
        )}
      </div>
      {frames.length > 0 && (
        <>
          {ordered.map((frame, i) => (
            <FrameView key={i} frame={frame} defaultOpen={i === (firstInApp === -1 ? 0 : firstInApp)} />
          ))}
          {hasInApp && frames.some((f) => !f.in_app) && (
            <div style={{ padding: 8, borderTop: `1px solid ${color.border}` }}>
              <Button size="sm" variant="ghost" onClick={() => setShowAll((s) => !s)}>
                {showAll ? "Show only my code" : `Show full stack trace (${frames.length} frames)`}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
