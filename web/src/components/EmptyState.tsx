import { DatabaseZap } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  message?: string;
  compact?: boolean;
}

export function EmptyState({
  title = "Dashboard data is missing.",
  message = "Run .\\run_web.bat from the repository root to generate and export dashboard data.",
  compact = false,
}: EmptyStateProps) {
  return (
    <div className={`empty-state ${compact ? "empty-state--compact" : ""}`} role="status">
      <DatabaseZap aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}
