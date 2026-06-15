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
import { formatMethods, formatPercent, formatUsd, humanize } from "../lib/format";
import type {
  Alert,
  DailyFeature,
  MethodResult,
  StlComponent,
  SuppressedAlert,
} from "../lib/types";

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
  methods: MethodResult[];
  suppressed?: SuppressedAlert[];
  visibility: TimelineVisibility;
  selectedDate?: string;
  height?: number;
}

interface TimelinePoint extends DailyFeature {
  expected_cost: number | null;
  relative_delta: number | null;
  operational_alert_level: string | null;
  ground_truth_status: "detected" | "missed" | "none";
  raw_detector_triggers: string | null;
  detected_true_marker: number | null;
  missed_true_marker: number | null;
  planned_marker: number | null;
  warning_marker: number | null;
  critical_marker: number | null;
}

const METHOD_ORDER = ["zscore", "stl", "isolation_forest"];
const EMPTY_SUPPRESSED_ALERTS: SuppressedAlert[] = [];

function formatThousands(value: number): string {
  const thousands = value / 1000;
  return `$${thousands.toFixed(thousands >= 10 ? 0 : 1).replace(/\.0$/, "")}k`;
}

function groundTruthLabel(status: TimelinePoint["ground_truth_status"]): string {
  if (status === "detected") return "True anomaly \u2014 detected";
  if (status === "missed") return "True anomaly \u2014 missed";
  return "No";
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
      <strong>Daily cost details</strong>
      <dl>
        <div>
          <dt>Date</dt>
          <dd>{point.usage_date}</dd>
        </div>
        <div>
          <dt>Actual cost</dt>
          <dd>{formatUsd(point.total_cost_usd)}</dd>
        </div>
        <div>
          <dt>Expected cost</dt>
          <dd>{formatUsd(point.expected_cost)}</dd>
        </div>
        <div>
          <dt>Delta</dt>
          <dd>{formatPercent(point.relative_delta)}</dd>
        </div>
        <div>
          <dt>Operational alert</dt>
          <dd>
            {point.operational_alert_level
              ? humanize(point.operational_alert_level)
              : "None"}
          </dd>
        </div>
        <div>
          <dt>Ground truth</dt>
          <dd>{groundTruthLabel(point.ground_truth_status)}</dd>
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
          <dt>Raw detector triggers</dt>
          <dd>{formatMethods(point.raw_detector_triggers)}</dd>
        </div>
      </dl>
    </div>
  );
}

export function CostTimelineChart({
  daily,
  stl,
  alerts,
  methods,
  suppressed = EMPTY_SUPPRESSED_ALERTS,
  visibility,
  selectedDate,
  height = 410,
}: CostTimelineChartProps) {
  const chartData = useMemo(() => {
    const stlExpectedByDate = new Map(stl.map((row) => [row.usage_date, row.expected_cost]));
    const alertByDate = new Map(alerts.map((row) => [row.usage_date, row]));
    const suppressedByDate = new Map(suppressed.map((row) => [row.usage_date, row]));
    const rawTriggersByDate = new Map<string, Set<string>>();
    methods.forEach((row) => {
      if (row.is_flagged !== 1) return;
      const triggered = rawTriggersByDate.get(row.usage_date) ?? new Set<string>();
      triggered.add(row.method);
      rawTriggersByDate.set(row.usage_date, triggered);
    });

    return daily.map<TimelinePoint>((row) => {
      const alert = alertByDate.get(row.usage_date);
      const suppressedCandidate = suppressedByDate.get(row.usage_date);
      const expectedCost =
        alert?.expected_cost ??
        suppressedCandidate?.expected_cost ??
        stlExpectedByDate.get(row.usage_date) ??
        null;
      const relativeDelta =
        expectedCost !== null && expectedCost > 0
          ? (row.total_cost_usd - expectedCost) / expectedCost
          : null;
      const isTrueAnomaly = row.is_anomaly === 1 && row.planned_event !== 1;
      const groundTruthStatus = isTrueAnomaly
        ? alert
          ? "detected"
          : "missed"
        : "none";
      const triggeredMethods = rawTriggersByDate.get(row.usage_date);
      const orderedTriggers = METHOD_ORDER.filter((method) => triggeredMethods?.has(method));

      return {
        ...row,
        expected_cost: expectedCost,
        relative_delta: relativeDelta,
        operational_alert_level: alert?.alert_level ?? null,
        ground_truth_status: groundTruthStatus,
        raw_detector_triggers: orderedTriggers.length > 0 ? orderedTriggers.join(",") : null,
        detected_true_marker:
          groundTruthStatus === "detected" ? row.total_cost_usd : null,
        missed_true_marker: groundTruthStatus === "missed" ? row.total_cost_usd : null,
        planned_marker: row.planned_event === 1 ? row.total_cost_usd : null,
        warning_marker: alert?.alert_level === "warning" ? row.total_cost_usd : null,
        critical_marker: alert?.alert_level === "critical" ? row.total_cost_usd : null,
      };
    });
  }, [alerts, daily, methods, stl, suppressed]);

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
            <>
              <Scatter
                dataKey="detected_true_marker"
                name={"True anomaly \u2014 detected"}
                fill="var(--mint)"
                stroke="var(--bg)"
                strokeWidth={1.5}
                shape="diamond"
                legendType="diamond"
                isAnimationActive={false}
              />
              <Scatter
                dataKey="missed_true_marker"
                name={"True anomaly \u2014 missed"}
                fill="var(--mint)"
                fillOpacity={0.18}
                stroke="var(--mint)"
                strokeWidth={2}
                shape="circle"
                legendType="circle"
                isAnimationActive={false}
              />
            </>
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
