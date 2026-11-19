import type { Series } from "../api/types";
import { color } from "../theme/tokens";

/** Tiny SVG bar chart for issue rows (no chart library needed). */
export function Sparkline({ series, width = 96, height = 24 }: { series?: Series; width?: number; height?: number }) {
  if (!series?.length) return <svg width={width} height={height} aria-hidden />;
  const max = Math.max(1, ...series.map(([, c]) => c));
  const barWidth = width / series.length;
  const total = series.reduce((sum, [, c]) => sum + c, 0);
  return (
    <svg width={width} height={height} role="img" aria-label={`${total} events in the last 24 hours`}>
      {series.map(([t, c], i) => {
        const h = c === 0 ? 1 : Math.max(2, (c / max) * height);
        return (
          <rect
            key={t}
            x={i * barWidth + 0.5}
            y={height - h}
            width={Math.max(1, barWidth - 1.5)}
            height={h}
            rx={1}
            style={{ fill: c === 0 ? color.border : color.teal }}
          />
        );
      })}
    </svg>
  );
}
