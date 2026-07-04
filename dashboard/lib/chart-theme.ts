export const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
] as const;

export function chartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

export const CHART_AXIS_PROPS = {
  tick: { fontSize: 11, fill: "var(--muted-foreground)" },
  axisLine: { stroke: "var(--border)" },
  tickLine: { stroke: "var(--border)" },
} as const;

export const CHART_GRID_PROPS = {
  strokeDasharray: "3 3",
  stroke: "var(--border)",
} as const;

export const CHART_TOOLTIP_CURSOR = {
  fill: "var(--muted)",
  fillOpacity: 0.4,
  stroke: "var(--border)",
  strokeOpacity: 0.6,
  radius: 4,
} as const;

export const CHART_TOOLTIP_PROPS = {
  cursor: CHART_TOOLTIP_CURSOR,
  contentStyle: {
    backgroundColor: "var(--popover)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    color: "var(--popover-foreground)",
    boxShadow: "none",
    padding: "8px 12px",
  },
  labelStyle: {
    color: "var(--popover-foreground)",
    fontWeight: 600,
    marginBottom: 4,
  },
  itemStyle: {
    color: "var(--muted-foreground)",
  },
  wrapperStyle: {
    outline: "none",
    zIndex: 50,
  },
} as const;

export const CHART_ACTIVE_BAR_PROPS = {
  fillOpacity: 0.85,
  stroke: "var(--foreground)",
  strokeWidth: 1,
  strokeOpacity: 0.12,
} as const;
