import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";
import type { Series } from "../api/types";
import { useTheme } from "../theme/ThemeContext";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

export function TimeSeriesChart({ series, height = 140, daily = false }: { series: Series; height?: number; daily?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { palette, resolved } = useTheme();

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    const label = (ts: number) =>
      new Date(ts * 1000).toLocaleString(undefined, daily ? { month: "short", day: "numeric" } : { hour: "numeric" });
    chart.setOption({
      animation: false,
      grid: { left: 36, right: 8, top: 10, bottom: 22 },
      tooltip: {
        trigger: "axis",
        backgroundColor: palette.surface,
        borderColor: palette.border,
        textStyle: { color: palette.text },
        valueFormatter: (v: number) => `${v} events`,
      },
      xAxis: {
        type: "category",
        data: series.map(([t]) => label(t)),
        axisLine: { lineStyle: { color: palette.border } },
        axisLabel: { color: palette.textSubtle, fontSize: 11 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        splitLine: { lineStyle: { color: palette.border, opacity: 0.5 } },
        axisLabel: { color: palette.textSubtle, fontSize: 11 },
      },
      series: [{ type: "bar", data: series.map(([, c]) => c), itemStyle: { color: palette.accentAlt, borderRadius: [2, 2, 0, 0] } }],
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [series, palette, resolved, daily]);

  return <div ref={ref} style={{ height, width: "100%" }} role="img" aria-label="Events over time" />;
}
