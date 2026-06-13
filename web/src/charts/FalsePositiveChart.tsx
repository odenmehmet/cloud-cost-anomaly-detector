import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber, subjectChartName } from "../lib/format";
import type { EvaluationSummary } from "../lib/types";

interface FalsePositiveChartProps {
  rows: EvaluationSummary[];
}

export function FalsePositiveChart({ rows }: FalsePositiveChartProps) {
  const data = rows.map((row) => ({ ...row, label: subjectChartName(row.subject) }));
  return (
    <div className="chart-frame" aria-label="False positives per 30 days">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 12, right: 12, bottom: 18, left: 0 }}>
          <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
            interval={0}
            textAnchor="middle"
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => formatNumber(Number(value), 2)}
            contentStyle={{
              background: "var(--surface-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 8,
            }}
          />
          <Bar
            dataKey="false_positives_per_30_days"
            name="FP / 30 days"
            fill="var(--critical)"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
