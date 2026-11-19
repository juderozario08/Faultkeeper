import { createContext, useContext } from "react";
import type { ThemeName, Tokens } from "./tokens";

export type ThemePreference = ThemeName | "system";

export interface ThemeContextValue {
  preference: ThemePreference;
  resolved: ThemeName;
  palette: Tokens;
  setPreference: (p: ThemePreference) => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
