import { lazy, Suspense } from "react";
import type { Series } from "../api/types";

const TimeSeriesChart = lazy(() => import("./TimeSeriesChart").then((m) => ({ default: m.TimeSeriesChart })));

/** Code-split wrapper: ECharts loads only when a chart is first shown. */
export function Chart(props: { series: Series; height?: number; daily?: boolean }) {
  return (
    <Suspense fallback={<div style={{ height: props.height ?? 140 }} />}>
      <TimeSeriesChart {...props} />
    </Suspense>
  );
}
