const METHOD_NAMES: Record<string, string> = {
  zscore: "Rolling Z-score",
  stl: "STL Decomposition",
  isolation_forest: "Isolation Forest",
  raw_alert_candidate: "Raw Alert Candidate",
};

const SUBJECT_NAMES: Record<string, string> = {
  ...METHOD_NAMES,
  agreement_alert: "Agreement Alert",
};

const SUBJECT_CHART_NAMES: Record<string, string> = {
  agreement_alert: "Ops Alert",
  isolation_forest: "IF",
  raw_alert_candidate: "Raw",
  stl: "STL",
  zscore: "Z-score",
};

export function formatUsd(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
      }).format(value)
    : "-";
}

export function formatUsdCompact(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(value)
    : "-";
}

export function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "-";
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "-";
}

export function yesNo(value: number | boolean | null | undefined): string {
  return value === 1 || value === true ? "Yes" : "No";
}

export function humanize(value: string | null | undefined): string {
  if (!value || value === "none") return "None";
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function methodName(value: string): string {
  return METHOD_NAMES[value] ?? humanize(value);
}

export function subjectName(value: string): string {
  return SUBJECT_NAMES[value] ?? humanize(value);
}

export function subjectChartName(value: string): string {
  return SUBJECT_CHART_NAMES[value] ?? subjectName(value);
}

export function formatMethods(value: string | null | undefined): string {
  if (!value) return "None";
  return value
    .split(",")
    .map((method) => methodName(method.trim()))
    .join(", ");
}
