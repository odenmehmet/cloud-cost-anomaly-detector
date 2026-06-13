import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPercent, subjectChartName } from "../lib/format";
import type { EvaluationSummary } from "../lib/types";

interface EvaluationMetricChartProps {
  rows: EvaluationSummary[];
}

export function EvaluationMetricChart({ rows }: EvaluationMetricChartProps) {
  const data = rows.map((row) => ({ ...row, label: subjectChartName(row.subject) }));
  return (
    <div className="chart-frame" aria-label="Precision recall and F1 by subject">
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={data} margin={{ top: 12, right: 14, bottom: 18, left: 0 }}>
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
            domain={[0, 1]}
            tickFormatter={(value) => `${Math.round(Number(value) * 100)}%`}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => formatPercent(Number(value))}
            contentStyle={{
              background: "var(--surface-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 8,
            }}
          />
          <Legend wrapperStyle={{ color: "var(--text-secondary)", fontSize: 12 }} />
          <Bar dataKey="precision" name="Precision" fill="var(--accent)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="recall" name="Recall" fill="var(--warning)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="f1" name="F1" fill="var(--purple)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
