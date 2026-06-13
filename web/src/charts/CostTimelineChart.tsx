import { useMemo } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatMethods, formatUsd, humanize } from "../lib/format";
import type { Alert, DailyFeature, StlComponent } from "../lib/types";

export interface TimelineVisibility {
  movingAverage: boolean;
  expectedCost: boolean;
  trueAnomalies: boolean;
  plannedEvents: boolean;
  warningAlerts: boolean;
  criticalAlerts: boolean;
}

interface CostTimelineChartProps {
  daily: DailyFeature[];
  stl: StlComponent[];
  alerts: Alert[];
  visibility: TimelineVisibility;
  selectedDate?: string;
  height?: number;
}

interface TimelinePoint extends DailyFeature {
  expected_cost: number | null;
  alert_level: string | null;
  methods_triggered: string | null;
  true_marker: number | null;
  planned_marker: number | null;
  warning_marker: number | null;
  critical_marker: number | null;
}

function formatThousands(value: number): string {
  const thousands = value / 1000;
  return `$${thousands.toFixed(thousands >= 10 ? 0 : 1).replace(/\.0$/, "")}k`;
}

function TimelineTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TimelinePoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{point.usage_date}</strong>
      <dl>
        <div>
          <dt>Actual cost</dt>
          <dd>{formatUsd(point.total_cost_usd)}</dd>
        </div>
        <div>
          <dt>Moving average</dt>
          <dd>{formatUsd(point.cost_rolling_mean_7)}</dd>
        </div>
        <div>
          <dt>Expected cost</dt>
          <dd>{formatUsd(point.expected_cost)}</dd>
        </div>
        <div>
          <dt>Alert level</dt>
          <dd>{point.alert_level ? humanize(point.alert_level) : "None"}</dd>
        </div>
        <div>
          <dt>Anomaly type</dt>
          <dd>{humanize(point.anomaly_types)}</dd>
        </div>
        <div>
          <dt>Planned event</dt>
          <dd>{point.planned_event === 1 ? point.planned_event_ids : "None"}</dd>
        </div>
        <div>
          <dt>Methods triggered</dt>
          <dd>{formatMethods(point.methods_triggered)}</dd>
        </div>
      </dl>
    </div>
  );
}

export function CostTimelineChart({
  daily,
  stl,
  alerts,
  visibility,
  selectedDate,
  height = 410,
}: CostTimelineChartProps) {
  const chartData = useMemo(() => {
    const expectedByDate = new Map(stl.map((row) => [row.usage_date, row.expected_cost]));
    const alertByDate = new Map(alerts.map((row) => [row.usage_date, row]));
    return daily.map<TimelinePoint>((row) => {
      const alert = alertByDate.get(row.usage_date);
      return {
        ...row,
        expected_cost: expectedByDate.get(row.usage_date) ?? null,
        alert_level: alert?.alert_level ?? null,
        methods_triggered: alert?.methods_triggered ?? null,
        true_marker: row.is_anomaly === 1 ? row.total_cost_usd : null,
        planned_marker: row.planned_event === 1 ? row.total_cost_usd : null,
        warning_marker: alert?.alert_level === "warning" ? row.total_cost_usd : null,
        critical_marker: alert?.alert_level === "critical" ? row.total_cost_usd : null,
      };
    });
  }, [alerts, daily, stl]);

  return (
    <div className="chart-frame" aria-label="Daily cloud cost timeline">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 18, right: 16, bottom: 8, left: 2 }}>
          <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey="usage_date"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            minTickGap={42}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(value) => formatThousands(Number(value))}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={48}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<TimelineTooltip />} />
          <Legend wrapperStyle={{ color: "var(--text-secondary)", fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="total_cost_usd"
            name="Daily cost"
            stroke="var(--accent)"
            strokeWidth={2.4}
            dot={false}
            isAnimationActive={false}
            activeDot={{ r: 5, fill: "var(--accent)", stroke: "var(--bg)" }}
          />
          {visibility.movingAverage ? (
            <Line
              type="monotone"
              dataKey="cost_rolling_mean_7"
              name="7-day moving average"
              stroke="var(--purple)"
              strokeWidth={1.8}
              strokeDasharray="6 4"
              dot={false}
              isAnimationActive={false}
            />
          ) : null}
          {visibility.expectedCost ? (
            <Line
              type="monotone"
              dataKey="expected_cost"
              name="STL expected cost"
              stroke="var(--mint)"
              strokeWidth={1.8}
              dot={false}
              isAnimationActive={false}
            />
          ) : null}
          {visibility.trueAnomalies ? (
            <Scatter
              dataKey="true_marker"
              name="True anomaly"
              fill="var(--mint)"
              shape="diamond"
              isAnimationActive={false}
            />
          ) : null}
          {visibility.plannedEvents ? (
            <Scatter
              dataKey="planned_marker"
              name="Planned event"
              fill="var(--purple)"
              shape="triangle"
              isAnimationActive={false}
            />
          ) : null}
          {visibility.warningAlerts ? (
            <Scatter
              dataKey="warning_marker"
              name="Warning"
              fill="var(--warning)"
              isAnimationActive={false}
            />
          ) : null}
          {visibility.criticalAlerts ? (
            <Scatter
              dataKey="critical_marker"
              name="Critical"
              fill="var(--critical)"
              isAnimationActive={false}
            />
          ) : null}
          {selectedDate ? (
            <ReferenceLine
              x={selectedDate}
              stroke="var(--critical)"
              strokeWidth={2}
              strokeDasharray="4 4"
              label={{ value: "Selected alert", fill: "var(--critical)", fontSize: 12 }}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
