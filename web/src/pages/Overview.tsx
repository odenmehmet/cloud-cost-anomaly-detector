import { useMemo, useState } from "react";
import { Activity, Ban, CalendarDays, CircleDollarSign, ShieldAlert, TriangleAlert } from "lucide-react";
import { CostTimelineChart, type TimelineVisibility } from "../charts/CostTimelineChart";
import { DataTable, type DataColumn } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatMethods, formatPercent, formatUsd, formatUsdCompact, humanize, yesNo } from "../lib/format";
import type { Alert, DailyFeature, MethodResult, StlComponent, SuppressedAlert } from "../lib/types";

interface OverviewProps {
  daily: DailyFeature[];
  alerts: Alert[];
  methods: MethodResult[];
  stl: StlComponent[];
  suppressed: SuppressedAlert[];
  onSelectAlert: (alertId: string) => void;
}

const ALERT_COLUMNS = (onSelectAlert: (alertId: string) => void): DataColumn<Alert>[] => [
  {
    key: "id",
    label: "Alert",
    render: (row) => (
      <button className="table-link" type="button" onClick={() => onSelectAlert(row.alert_id)}>
        {row.alert_id}
      </button>
    ),
  },
  { key: "date", label: "Date", render: (row) => row.usage_date },
  {
    key: "level",
    label: "Severity",
    render: (row) => (
      <StatusBadge tone={row.alert_level === "critical" ? "critical" : "warning"}>
        {humanize(row.alert_level)}
      </StatusBadge>
    ),
  },
  {
    key: "agreement",
    label: "Method agreement",
    render: (row) => `${row.method_count} of 3`,
  },
  { key: "actual", label: "Actual cost", align: "right", render: (row) => formatUsd(row.actual_cost) },
  { key: "delta", label: "Delta", align: "right", render: (row) => formatPercent(row.relative_delta) },
  { key: "truth", label: "Ground truth", render: (row) => yesNo(row.is_true_anomaly) },
];

const SUPPRESSED_COLUMNS: DataColumn<SuppressedAlert>[] = [
  { key: "id", label: "Suppression", render: (row) => row.suppression_id },
  { key: "date", label: "Date", render: (row) => row.usage_date },
  { key: "event", label: "Planned event", render: (row) => row.planned_event_id },
  { key: "agreement", label: "Method agreement", render: (row) => `${row.method_count} of 3` },
  { key: "methods", label: "Methods", render: (row) => formatMethods(row.methods_triggered) },
  { key: "actual", label: "Actual cost", align: "right", render: (row) => formatUsd(row.actual_cost) },
  { key: "delta", label: "Delta", align: "right", render: (row) => formatPercent(row.relative_delta) },
];

const VISIBILITY_LABELS: Array<[keyof TimelineVisibility, string]> = [
  ["trueAnomalies", "Ground truth"],
  ["plannedEvents", "Planned events"],
  ["warningAlerts", "Warnings"],
  ["criticalAlerts", "Critical alerts"],
  ["movingAverage", "7-day average"],
  ["expectedCost", "STL expected"],
];

export function Overview({ daily, alerts, methods, stl, suppressed, onSelectAlert }: OverviewProps) {
  const [startDate, setStartDate] = useState(daily[0]?.usage_date ?? "");
  const [endDate, setEndDate] = useState(daily[daily.length - 1]?.usage_date ?? "");
  const [visibility, setVisibility] = useState<TimelineVisibility>({
    trueAnomalies: true,
    plannedEvents: true,
    warningAlerts: true,
    criticalAlerts: true,
    movingAverage: true,
    expectedCost: true,
  });

  const filteredDaily = useMemo(
    () =>
      daily.filter(
        (row) => (!startDate || row.usage_date >= startDate) && (!endDate || row.usage_date <= endDate),
      ),
    [daily, endDate, startDate],
  );
  const filteredAlerts = useMemo(
    () =>
      alerts.filter(
        (row) => (!startDate || row.usage_date >= startDate) && (!endDate || row.usage_date <= endDate),
      ),
    [alerts, endDate, startDate],
  );
  const filteredStl = useMemo(
    () =>
      stl.filter(
        (row) => (!startDate || row.usage_date >= startDate) && (!endDate || row.usage_date <= endDate),
      ),
    [endDate, startDate, stl],
  );
  const filteredSuppressed = useMemo(
    () =>
      suppressed.filter(
        (row) => (!startDate || row.usage_date >= startDate) && (!endDate || row.usage_date <= endDate),
      ),
    [endDate, startDate, suppressed],
  );

  const totalCost = filteredDaily.reduce((sum, row) => sum + row.total_cost_usd, 0);
  const methodCounts = ["zscore", "stl", "isolation_forest"].map((method) => ({
    method,
    count: methods.filter(
      (row) =>
        row.method === method &&
        row.is_flagged === 1 &&
        (!startDate || row.usage_date >= startDate) &&
        (!endDate || row.usage_date <= endDate),
    ).length,
  }));

  const toggle = (key: keyof TimelineVisibility) => {
    setVisibility((current) => ({ ...current, [key]: !current[key] }));
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Cost Overview</h1>
          <p>Daily cloud cost, expected behavior, detector flags, and agreement alerts.</p>
        </div>
      </header>

      <div className="context-note">
        <Activity aria-hidden="true" />
        <p>Weekly seasonality is expected in this synthetic billing series.</p>
      </div>
      <div className="context-note context-note--policy">
        <ShieldAlert aria-hidden="true" />
        <p>
          Final alerts are generated only when detector agreement and severity thresholds
          are met.
        </p>
      </div>

      <SectionCard className="control-panel">
        <div className="control-grid">
          <label>
            <span>Start date</span>
            <input
              className="date-input"
              type="text"
              inputMode="numeric"
              pattern="\d{4}-\d{2}-\d{2}"
              placeholder="YYYY-MM-DD"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>
          <label>
            <span>End date</span>
            <input
              className="date-input"
              type="text"
              inputMode="numeric"
              pattern="\d{4}-\d{2}-\d{2}"
              placeholder="YYYY-MM-DD"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </label>
          {VISIBILITY_LABELS.map(([key, label]) => (
            <label className="toggle-control" key={key}>
              <input type="checkbox" checked={visibility[key]} onChange={() => toggle(key)} />
              <span className="toggle-control__track" />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </SectionCard>

      <section className="metric-grid metric-grid--five">
        <MetricCard
          label="Total cost"
          value={formatUsdCompact(totalCost)}
          note="Selected range"
          icon={CircleDollarSign}
        />
        <MetricCard
          label="True anomaly days"
          value={filteredDaily.filter((row) => row.is_anomaly === 1).length.toLocaleString()}
          note="Injected labels"
          icon={CalendarDays}
          tone="success"
        />
        <MetricCard
          label="Total alerts"
          value={filteredAlerts.length.toLocaleString()}
          note="Selected range"
          icon={Activity}
          tone="purple"
        />
        <MetricCard
          label="Warning alerts"
          value={filteredAlerts.filter((row) => row.alert_level === "warning").length.toLocaleString()}
          note="Moderate agreement"
          icon={TriangleAlert}
          tone="warning"
        />
        <MetricCard
          label="Critical alerts"
          value={filteredAlerts.filter((row) => row.alert_level === "critical").length.toLocaleString()}
          note="Strong agreement"
          icon={ShieldAlert}
          tone="critical"
        />
      </section>

      <SectionCard
        title="Daily cost and expected behavior"
        description="Hover for operational status, ground truth, planned events, and raw detector triggers."
      >
        <CostTimelineChart
          daily={filteredDaily}
          alerts={filteredAlerts}
          methods={methods}
          suppressed={filteredSuppressed}
          stl={filteredStl}
          visibility={visibility}
        />
      </SectionCard>

      <div className="overview-lower-grid">
        <SectionCard title="Detector flag counts" description="Independent flags in the selected range.">
          <div className="method-count-list">
            {methodCounts.map(({ method, count }) => (
              <div key={method}>
                <span>{formatMethods(method)}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        </SectionCard>
        <SectionCard title="Series context">
          <dl className="series-context">
            <div>
              <dt>Daily cost</dt>
              <dd>Observed synthetic billing total</dd>
            </div>
            <div>
              <dt>7-day average</dt>
              <dd>Visual smoothing only</dd>
            </div>
            <div>
              <dt>STL expected</dt>
              <dd>Trend plus weekly seasonal component</dd>
            </div>
          </dl>
        </SectionCard>
      </div>

      <SectionCard title="Alert summary" description="Select an alert to open its investigation view.">
        <DataTable
          columns={ALERT_COLUMNS(onSelectAlert)}
          rows={filteredAlerts}
          rowKey={(row) => row.alert_id}
        />
      </SectionCard>

      <SectionCard
        title="Suppressed planned events"
        description="Detector candidates explained by the planned-event catalog and excluded from operational alerts."
      >
        {filteredSuppressed.length > 0 ? (
          <DataTable
            columns={SUPPRESSED_COLUMNS}
            rows={filteredSuppressed}
            rowKey={(row) => row.suppression_id}
          />
        ) : (
          <div className="empty-inline">
            <Ban aria-hidden="true" />
            <span>No planned-event suppressions in the selected range.</span>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
