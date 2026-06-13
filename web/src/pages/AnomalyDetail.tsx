import { useEffect, useMemo, useState } from "react";
import { Activity, CheckCircle2, Network } from "lucide-react";
import { ContributorBarChart } from "../charts/ContributorBarChart";
import { CostTimelineChart } from "../charts/CostTimelineChart";
import { DataTable, type DataColumn } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import {
  formatNumber,
  formatPercent,
  formatUsd,
  humanize,
  methodName,
  yesNo,
} from "../lib/format";
import type { Alert, Contributor, DailyFeature, MethodResult, StlComponent } from "../lib/types";

interface AnomalyDetailProps {
  alerts: Alert[];
  daily: DailyFeature[];
  methods: MethodResult[];
  contributors: Contributor[];
  stl: StlComponent[];
  initialAlertId?: string;
  onAlertChange: (alertId: string) => void;
}

function contributorColumns(basis: string): DataColumn<Contributor>[] {
  const usesCurrentCost = basis === "current_cost_fallback";
  return [
    { key: "rank", label: "Rank", render: (row) => row.rank },
    { key: "service", label: "Service", render: (row) => row.service },
    { key: "region", label: "Region", render: (row) => row.region },
    {
      key: "current",
      label: "Current cost",
      align: "right",
      render: (row) => formatUsd(row.cost_usd),
    },
    {
      key: "average",
      label: "Previous 7-day average",
      align: "right",
      render: (row) => formatUsd(row.previous_7d_avg_cost),
    },
    {
      key: "delta",
      label: usesCurrentCost ? "Cost change" : "Cost increase",
      align: "right",
      render: (row) => formatUsd(row.delta_cost),
    },
    {
      key: "share",
      label: usesCurrentCost ? "Current-cost share" : "Increase contribution",
      align: "right",
      render: (row) => formatPercent(row.contribution_share),
    },
    { key: "reason", label: "Ranking basis", render: (row) => row.contributor_reason },
  ];
}

function alertContext(alert: Alert): string {
  if (alert.planned_event === 1) {
    return "Explained planned usage growth; suppressed from operational alerting.";
  }
  if (alert.is_true_anomaly === 1) {
    return "Matches injected ground truth.";
  }
  return "Operational alert with no matching injected anomaly label.";
}

function eventClassification(alert: Alert): string {
  if (alert.planned_event === 1) return "Explained planned event";
  if (alert.is_true_anomaly === 1) return "Injected anomaly";
  return "Non-injected event";
}

function anomalyTypeLabel(alert: Alert): string {
  if (alert.planned_event === 1) return "Planned usage growth";
  if (alert.is_true_anomaly !== 1 || alert.anomaly_type === "none") {
    return "Non-injected event";
  }
  return humanize(alert.anomaly_type);
}

export function AnomalyDetail({
  alerts,
  daily,
  methods,
  contributors,
  stl,
  initialAlertId,
  onAlertChange,
}: AnomalyDetailProps) {
  const fallbackAlert = alerts.find((alert) => alert.alert_id === "ALERT-0001") ?? alerts[0];
  const [selectedId, setSelectedId] = useState(initialAlertId ?? fallbackAlert?.alert_id ?? "");

  useEffect(() => {
    if (initialAlertId && alerts.some((alert) => alert.alert_id === initialAlertId)) {
      setSelectedId(initialAlertId);
    }
  }, [alerts, initialAlertId]);

  const selected = alerts.find((alert) => alert.alert_id === selectedId) ?? fallbackAlert;
  const localDaily = useMemo(() => {
    if (!selected) return [];
    const selectedIndex = daily.findIndex((row) => row.usage_date === selected.usage_date);
    return daily.slice(Math.max(0, selectedIndex - 14), selectedIndex + 15);
  }, [daily, selected]);
  const localDates = useMemo(() => new Set(localDaily.map((row) => row.usage_date)), [localDaily]);
  const localStl = stl.filter((row) => localDates.has(row.usage_date));
  const localAlerts = alerts.filter((row) => localDates.has(row.usage_date));
  const methodEvidence = methods.filter((row) => row.usage_date === selected?.usage_date);
  const contributorRows = contributors
    .filter((row) => row.alert_id === selected?.alert_id)
    .sort((a, b) => a.rank - b.rank);
  const contributionBasis = contributorRows[0]?.contribution_basis ?? "positive_delta";
  const contributorDescription =
    contributionBasis === "current_cost_fallback"
      ? "No positive service-region deltas were available, so rows are ranked by current cost."
      : "Positive service and region cost changes versus the previous 7-day average.";
  const contributorNote =
    contributionBasis === "current_cost_fallback"
      ? "Contributor ranking shows current-cost share because no positive increases were available. It is not causal attribution."
      : "Contributor ranking highlights where cost increased most. It is not causal attribution.";

  if (!selected) {
    return <EmptyState title="No alerts are available for investigation." />;
  }

  const changeAlert = (alertId: string) => {
    setSelectedId(alertId);
    onAlertChange(alertId);
  };

  return (
    <div className="page">
      <header className="page-header page-header--with-control">
        <div>
          <h1>Alert Investigation</h1>
          <p>Incident context, detector evidence, and non-causal contributor ranking.</p>
        </div>
        <label className="select-control">
          <span>Alert</span>
          <select value={selected.alert_id} onChange={(event) => changeAlert(event.target.value)}>
            {alerts.map((alert) => (
              <option key={alert.alert_id} value={alert.alert_id}>
                {alert.alert_id} | {alert.usage_date} | {humanize(alert.alert_level)}
              </option>
            ))}
          </select>
        </label>
      </header>

      <section className={`incident-panel incident-panel--${selected.alert_level}`}>
        <div className="incident-panel__top">
          <div>
            <span className="incident-panel__id">{selected.alert_id}</span>
            <h2>{selected.usage_date}</h2>
            <p className="incident-panel__summary">{alertContext(selected)}</p>
          </div>
          <div className="badge-list">
            <StatusBadge tone={selected.alert_level === "critical" ? "critical" : "warning"}>
              {humanize(selected.alert_level)}
            </StatusBadge>
            <StatusBadge tone={selected.is_true_anomaly === 1 ? "success" : "muted"}>
              Ground truth: {yesNo(selected.is_true_anomaly)}
            </StatusBadge>
            <StatusBadge tone={selected.planned_event === 1 ? "warning" : "muted"}>
              {eventClassification(selected)}
            </StatusBadge>
          </div>
        </div>
        <div className="incident-grid">
          <div>
            <span>Actual cost</span>
            <strong>{formatUsd(selected.actual_cost)}</strong>
          </div>
          <div>
            <span>Expected cost</span>
            <strong>{formatUsd(selected.expected_cost)}</strong>
          </div>
          <div>
            <span>Relative delta</span>
            <strong>{formatPercent(selected.relative_delta)}</strong>
          </div>
          <div>
            <span>Method agreement</span>
            <strong>{selected.method_count} of 3 methods</strong>
          </div>
          <div>
            <span>Ground truth</span>
            <strong>{yesNo(selected.is_true_anomaly)}</strong>
          </div>
          <div>
            <span>Event classification</span>
            <strong>{eventClassification(selected)}</strong>
          </div>
          <div>
            <span>Anomaly type</span>
            <strong>{anomalyTypeLabel(selected)}</strong>
          </div>
          <div>
            <span>Top contributor dimension</span>
            <strong>
              {contributorRows[0]
                ? `${contributorRows[0].service} / ${contributorRows[0].region}`
                : `${selected.top_service} / ${selected.top_region}`}
            </strong>
          </div>
        </div>
      </section>

      <SectionCard
        title="Local cost context"
        description="Actual and STL expected cost for 14 days before and after the alert."
      >
        <CostTimelineChart
          daily={localDaily}
          stl={localStl}
          alerts={localAlerts}
          selectedDate={selected.usage_date}
          height={360}
          visibility={{
            movingAverage: false,
            expectedCost: true,
            trueAnomalies: true,
            plannedEvents: true,
            warningAlerts: false,
            criticalAlerts: false,
          }}
        />
      </SectionCard>

      <SectionCard title="Method evidence" description="Values are shown exactly as exported by the pipeline.">
        <div className="evidence-grid">
          {methodEvidence.map((row) => (
            <article
              className={row.is_flagged === 1 ? "evidence-card evidence-card--flagged" : "evidence-card"}
              key={row.method}
            >
              <div className="evidence-card__head">
                <div className="evidence-card__icon">
                  {row.is_flagged === 1 ? (
                    <CheckCircle2 aria-hidden="true" />
                  ) : (
                    <Activity aria-hidden="true" />
                  )}
                </div>
                <div>
                  <h3>{methodName(row.method)}</h3>
                  <StatusBadge tone={row.is_flagged === 1 ? "success" : "muted"}>
                    Flagged: {yesNo(row.is_flagged)}
                  </StatusBadge>
                </div>
              </div>
              <dl className="evidence-values">
                <div>
                  <dt>Score</dt>
                  <dd>{formatNumber(row.score, 4)}</dd>
                </div>
                <div>
                  <dt>Threshold</dt>
                  <dd>{formatNumber(row.threshold, 4)}</dd>
                </div>
                <div>
                  <dt>Relative deviation</dt>
                  <dd>{formatPercent(row.relative_deviation)}</dd>
                </div>
                <div>
                  <dt>Severity hint</dt>
                  <dd>{humanize(row.severity_hint)}</dd>
                </div>
              </dl>
              <p>{row.explanation}</p>
            </article>
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Contributor ranking"
        description={contributorDescription}
      >
        <ContributorBarChart rows={contributorRows} />
      </SectionCard>

      <SectionCard title="Contributor detail">
        <DataTable
          columns={contributorColumns(contributionBasis)}
          rows={contributorRows}
          rowKey={(row) => `${row.alert_id}-${row.rank}`}
        />
      </SectionCard>

      <div className="non-causal-note">
        <Network aria-hidden="true" />
        <p>{contributorNote}</p>
      </div>
    </div>
  );
}
