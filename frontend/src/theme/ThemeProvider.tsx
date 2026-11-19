import { Global, css } from "@emotion/react";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ThemeContext, type ThemePreference } from "./ThemeContext";
import { cssVariables, tokens, type ThemeName } from "./tokens";

const STORAGE_KEY = "fk-theme";

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    /* storage unavailable */
  }
  return "system";
}

function systemTheme(): ThemeName {
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(readPreference);
  const [system, setSystem] = useState<ThemeName>(systemTheme);

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: light)");
    if (!media) return;
    const onChange = () => setSystem(media.matches ? "light" : "dark");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const resolved: ThemeName = preference === "system" ? system : preference;

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
  }, [resolved]);

  const setPreference = useCallback((p: ThemePreference) => {
    setPreferenceState(p);
    try {
      localStorage.setItem(STORAGE_KEY, p);
    } catch {
      /* storage unavailable */
    }
  }, []);

  const value = useMemo(
    () => ({ preference, resolved, palette: tokens[resolved], setPreference }),
    [preference, resolved, setPreference],
  );

  return (
    <ThemeContext.Provider value={value}>
      <GlobalStyles />
      {children}
    </ThemeContext.Provider>
  );
}

function GlobalStyles() {
  return (
    <Global
      styles={css`
        :root,
        :root[data-theme="dark"] {
          ${cssVariables("dark")}
          color-scheme: dark;
        }
        :root[data-theme="light"] {
          ${cssVariables("light")}
          color-scheme: light;
        }
        *,
        *::before,
        *::after {
          box-sizing: border-box;
        }
        html,
        body,
        #root {
          height: 100%;
        }
        body {
          margin: 0;
          background: var(--fk-bg);
          color: var(--fk-text);
          font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
          font-size: 14px;
          line-height: 1.5;
          -webkit-font-smoothing: antialiased;
        }
        a {
          color: var(--fk-accent-text);
          text-decoration: none;
        }
        a:hover {
          text-decoration: underline;
        }
        code,
        pre {
          font-family: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
          font-size: 12.5px;
        }
        :focus-visible {
          outline: 2px solid var(--fk-accent);
          outline-offset: 2px;
        }
      `}
    />
  );
}
