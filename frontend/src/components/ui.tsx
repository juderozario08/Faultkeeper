import styled from "@emotion/styled";
import type { ReactNode } from "react";
import type { IssueStatus, Level } from "../api/types";
import { color } from "../theme/tokens";

export const Button = styled.button<{ variant?: "primary" | "default" | "ghost"; size?: "sm" | "md" }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  border: 1px solid ${({ variant }) => (variant === "primary" ? color.accentText : variant === "ghost" ? "transparent" : color.border)};
  background: ${({ variant }) => (variant === "primary" ? color.accentText : variant === "ghost" ? "transparent" : color.surface)};
  color: ${({ variant }) => (variant === "primary" ? color.onAccent : color.text)};
  font: inherit;
  font-weight: 500;
  font-size: ${({ size }) => (size === "sm" ? "12px" : "13px")};
  padding: ${({ size }) => (size === "sm" ? "3px 8px" : "6px 12px")};
  cursor: pointer;
  white-space: nowrap;
  &:hover:not(:disabled) {
    background: ${({ variant }) => (variant === "primary" ? color.accentText : color.surfaceHover)};
    filter: ${({ variant }) => (variant === "primary" ? "brightness(1.08)" : "none")};
  }
  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`;

export const Panel = styled.section`
  background: ${color.surface};
  border: 1px solid ${color.border};
  border-radius: 8px;
  overflow: hidden;
`;

export const PanelHeader = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid ${color.border};
  font-weight: 600;
  font-size: 13px;
  color: ${color.text};
`;

export const PanelBody = styled.div`
  padding: 14px;
`;

export const Muted = styled.span`
  color: ${color.textMuted};
`;

export const Subtle = styled.span`
  color: ${color.textSubtle};
  font-size: 12px;
`;

export const Input = styled.input`
  background: ${color.bg};
  border: 1px solid ${color.border};
  color: ${color.text};
  border-radius: 6px;
  padding: 6px 10px;
  font: inherit;
  min-width: 0;
  &::placeholder {
    color: ${color.textSubtle};
  }
`;

export const Select = styled.select`
  background: ${color.bg};
  border: 1px solid ${color.border};
  color: ${color.text};
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
`;

const LEVEL_COLORS: Record<Level, { fg: string; dot: string }> = {
  fatal: { fg: color.dangerText, dot: color.danger },
  error: { fg: color.dangerText, dot: color.danger },
  warning: { fg: color.warningText, dot: color.warning },
  info: { fg: color.infoText, dot: color.info },
  debug: { fg: color.textSubtle, dot: color.textSubtle },
};

const BadgeBase = styled.span<{ fg: string; dot?: string; bold?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: ${({ bold }) => (bold ? 700 : 600)};
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: ${({ fg }) => fg};
  border: 1px solid ${color.border};
  border-radius: 999px;
  padding: 1px 8px;
  background: ${color.bg};
  &::before {
    content: "";
    display: ${({ dot }) => (dot ? "block" : "none")};
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: ${({ dot }) => dot};
  }
`;

export function LevelBadge({ level }: { level: Level }) {
  const c = LEVEL_COLORS[level] ?? LEVEL_COLORS.error;
  return (
    <BadgeBase fg={c.fg} dot={c.dot} bold={level === "fatal"} aria-label={`level ${level}`}>
      {level}
    </BadgeBase>
  );
}

const STATUS_COLORS: Record<string, string> = {
  resolved: color.successText,
  ignored: color.textSubtle,
  regressed: color.orangeText,
  new: color.accentText,
  ongoing: color.textMuted,
};

export function StatusBadge({ status, substatus }: { status: IssueStatus; substatus?: string }) {
  const label = status === "unresolved" ? (substatus ?? "unresolved") : status;
  return <BadgeBase fg={STATUS_COLORS[label] ?? color.textMuted}>{label}</BadgeBase>;
}

export const Center = styled.div`
  display: grid;
  place-items: center;
  padding: 48px 16px;
  color: ${color.textMuted};
  text-align: center;
`;

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Center>
      <div>
        <div style={{ fontSize: 15, fontWeight: 600, color: color.text, marginBottom: 6 }}>{title}</div>
        {children}
      </div>
    </Center>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <Center role="status">{label}</Center>;
}

export function ErrorState({ error }: { error: unknown }) {
  return (
    <Center role="alert">
      <span style={{ color: color.dangerText }}>{error instanceof Error ? error.message : "Something went wrong."}</span>
    </Center>
  );
}

export const Kbd = styled.code`
  background: ${color.bg};
  border: 1px solid ${color.border};
  border-radius: 4px;
  padding: 1px 5px;
  color: ${color.text};
`;
