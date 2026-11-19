/**
 * Design tokens (ADR 0012). Dark = Tokyo Night, Light = Tokyo Night Day.
 * Palette colours are used as-is for surfaces, borders, accents and charts;
 * every `text*` token is tuned to meet WCAG AA (4.5:1) on bg, surface and surfaceHover.
 */
export type ThemeName = "dark" | "light";

export interface Tokens {
  bg: string;
  bgElevated: string;
  surface: string;
  surfaceHover: string;
  border: string;
  text: string;
  textMuted: string;
  textSubtle: string;
  accent: string;
  accentText: string;
  accentAlt: string;
  info: string;
  infoText: string;
  success: string;
  successText: string;
  warning: string;
  warningText: string;
  orange: string;
  orangeText: string;
  danger: string;
  dangerText: string;
  teal: string;
  onAccent: string;
}

export const tokens: Record<ThemeName, Tokens> = {
  dark: {
    bg: "#1a1b26",
    bgElevated: "#16161e",
    surface: "#1f2335",
    surfaceHover: "#292e42",
    border: "#3b4261",
    text: "#c0caf5",
    textMuted: "#a9b1d6",
    textSubtle: "#9aa5ce",
    accent: "#7aa2f7",
    accentText: "#7aa2f7",
    accentAlt: "#bb9af7",
    info: "#7dcfff",
    infoText: "#7dcfff",
    success: "#9ece6a",
    successText: "#9ece6a",
    warning: "#e0af68",
    warningText: "#e0af68",
    orange: "#ff9e64",
    orangeText: "#ff9e64",
    danger: "#f7768e",
    dangerText: "#f7768e",
    teal: "#73daca",
    onAccent: "#16161e",
  },
  light: {
    bg: "#e1e2e7",
    bgElevated: "#d0d5e3",
    surface: "#e9e9ed",
    surfaceHover: "#d5d8e5",
    border: "#a8aecb",
    text: "#2f4a9a",
    textMuted: "#3f4d7d",
    textSubtle: "#4a5680",
    accent: "#2e7de9",
    accentText: "#1d5bb5",
    accentAlt: "#9854f1",
    info: "#007197",
    infoText: "#005a78",
    success: "#587539",
    successText: "#3e5426",
    warning: "#8c6c3e",
    warningText: "#694f27",
    orange: "#b15c00",
    orangeText: "#8a4700",
    danger: "#f52a65",
    dangerText: "#a01845",
    teal: "#118c74",
    onAccent: "#ffffff",
  },
};

export const TEXT_TOKENS: (keyof Tokens)[] = [
  "text",
  "textMuted",
  "textSubtle",
  "accentText",
  "infoText",
  "successText",
  "warningText",
  "orangeText",
  "dangerText",
];
export const BACKGROUND_TOKENS: (keyof Tokens)[] = ["bg", "surface", "surfaceHover"];

const kebab = (name: string) => name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

/** CSS custom properties for a theme, e.g. `--fk-surface-hover: #292e42;`. */
export function cssVariables(theme: ThemeName): string {
  return Object.entries(tokens[theme])
    .map(([name, value]) => `--fk-${kebab(name)}: ${value};`)
    .join("\n");
}

/** `var(--fk-…)` references, so components never hard-code colours. */
export const color = Object.fromEntries(
  Object.keys(tokens.dark).map((name) => [name, `var(--fk-${kebab(name)})`]),
) as Record<keyof Tokens, string>;
