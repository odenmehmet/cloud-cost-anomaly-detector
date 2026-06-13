import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  note?: string;
  tone?: "info" | "success" | "warning" | "critical" | "purple";
  icon?: LucideIcon;
}

export function MetricCard({
  label,
  value,
  note,
  tone = "info",
  icon: Icon,
}: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__header">
        <span>{label}</span>
        {Icon ? <Icon aria-hidden="true" size={17} /> : null}
      </div>
      <strong>{value}</strong>
      {note ? <p>{note}</p> : null}
    </article>
  );
}
