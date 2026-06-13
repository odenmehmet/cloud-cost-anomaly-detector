import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPercent, formatUsd } from "../lib/format";
import type { Contributor } from "../lib/types";

interface ContributorBarChartProps {
  rows: Contributor[];
}

export function ContributorBarChart({ rows }: ContributorBarChartProps) {
  const data = rows.slice(0, 8).map((row) => ({
    ...row,
    label: `${row.service} / ${row.region}`,
    chart_value:
      row.contribution_basis === "current_cost_fallback" ? row.cost_usd : row.delta_cost,
  }));

  return (
    <div className="chart-frame" aria-label="Top cost contributors">
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
          <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={170}
            tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(45, 212, 191, 0.05)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as Contributor;
              return (
                <div className="chart-tooltip">
                  <strong>
                    {row.service} / {row.region}
                  </strong>
                  <p>
                    {row.contribution_basis === "current_cost_fallback" ? "Current cost" : "Delta cost"}:
                    {" "}{formatUsd(
                      row.contribution_basis === "current_cost_fallback" ? row.cost_usd : row.delta_cost,
                    )}
                  </p>
                  <p>Contribution share: {formatPercent(row.contribution_share)}</p>
                </div>
              );
            }}
          />
          <Bar dataKey="chart_value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {data.map((row, index) => (
              <Cell
                key={`${row.alert_id}-${row.rank}`}
                fill={index === 0 ? "var(--accent)" : "var(--accent-soft)"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
