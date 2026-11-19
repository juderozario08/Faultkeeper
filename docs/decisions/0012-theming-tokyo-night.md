# 0012. Theming: light + dark, dark = Tokyo Night
- Status: Accepted
- Date: 2026-11-18

## Context
Developers spend long sessions in error dashboards, and many prefer dark UIs. The product needs a distinctive, cohesive look rather than default framework styling. Tokyo Night is a popular editor theme (MIT-licensed palette) that developers recognize immediately.

## Decision
- The dashboard (and the Buggy Shop demo's chrome where relevant) supports **two themes: Light and Dark**.
- **Dark = Tokyo Night** ("Night" variant). **Light = Tokyo Night Day**, the official light variant of the same family, so both themes feel related.
- Theme selection: follows the OS (`prefers-color-scheme`) by default; a toggle in the header lets the user pick Light / Dark / System. The choice is stored in `localStorage` (`fk-theme`) and applied before first paint (inline script on `<html data-theme>`) to avoid a flash.
- All colors come from **semantic design tokens** exposed as CSS custom properties and an Emotion theme object (`frontend/src/theme/`). Components never use raw hex values.
- Charts (ECharts) read the same tokens; a theme switch re-renders charts.
- Code/stack-trace blocks use the same palette for syntax-like highlighting.

### Tokens

| Token | Dark (Tokyo Night) | Light (Tokyo Night Day) | Use |
|---|---|---|---|
| `bg` | `#1a1b26` | `#e1e2e7` | page background |
| `bg-elevated` | `#16161e` | `#d0d5e3` | sidebar, header |
| `surface` | `#1f2335` | `#e9e9ed` | cards, panels |
| `surface-hover` | `#292e42` | `#c4c8da` | hover, selected rows |
| `border` | `#3b4261` | `#a8aecb` | dividers, inputs |
| `text` | `#c0caf5` | `#3760bf` | primary text |
| `text-muted` | `#a9b1d6` | `#6172b0` | secondary text |
| `text-subtle` | `#565f89` | `#848cb5` | timestamps, hints |
| `accent` | `#7aa2f7` | `#2e7de9` | links, primary buttons, focus ring |
| `accent-alt` | `#bb9af7` | `#9854f1` | highlights, badges |
| `info` | `#7dcfff` | `#007197` | info level |
| `success` | `#9ece6a` | `#587539` | resolved |
| `warning` | `#e0af68` | `#8c6c3e` | warning level |
| `orange` | `#ff9e64` | `#b15c00` | regressions, fatal accents |
| `danger` | `#f7768e` | `#f52a65` | error level, destructive actions |
| `teal` | `#73daca` | `#118c74` | in-app frame marker, sparkline |

Level → color: `fatal` danger (bold), `error` danger, `warning` warning, `info` info, `debug` text-subtle.

## Consequences
- One token file drives everything; adding a theme later is a new token set.
- Contrast must be checked for both themes (WCAG AA for body text); Tokyo Night Day's muted tones may need slight darkening for small text.
- Tests snapshot key components in both themes.
