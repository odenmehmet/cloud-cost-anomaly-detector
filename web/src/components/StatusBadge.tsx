import type { ReactNode } from "react";

type BadgeTone = "default" | "info" | "success" | "warning" | "critical" | "muted";

interface StatusBadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
}

export function StatusBadge({ children, tone = "default" }: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}
