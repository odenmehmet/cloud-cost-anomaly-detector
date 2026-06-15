import { useMemo, useState } from "react";
import { BellRing, CalendarRange, Crosshair, Gauge, Settings2, Target, TrendingDown } from "lucide-react";
import { EvaluationMetricChart } from "../charts/EvaluationMetricChart";
import { FalsePositiveChart } from "../charts/FalsePositiveChart";
import { DataTable, type DataColumn } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import { formatMethods, formatNumber, formatPercent, humanize, subjectName, yesNo } from "../lib/format";
import type {
  CalibrationSummary,
  DetectionDelay,
  EvaluationByType,
  EventLevelEvaluation,
  EvaluationSummary,
  FalsePositiveDay,
  ScenarioRobustness,
} from "../lib/types";

interface EvaluationProps {
  summary: EvaluationSummary[];
  byType: EvaluationByType[];
  delays: DetectionDelay[];
  falsePositives: FalsePositiveDay[];
  eventLevel: EventLevelEvaluation[];
  calibration: CalibrationSummary[];
  scenarioRobustness: ScenarioRobustness[];
}

function matchingModeName(value: string): string {
  return value === "tolerance_1_day" ? "Within one day" : "Exact day";
}

const SUMMARY_COLUMNS: DataColumn<EvaluationSummary>[] = [
  { key: "subject", label: "Evaluation subject", render: (row) => subjectName(row.subject) },
  {
    key: "predicted",
    label: "Predicted positive days",
    align: "right",
    render: (row) => row.predicted_positive_days,
  },
  { key: "tp", label: "True positives", align: "right", render: (row) => row.true_positives },
  { key: "fp", label: "False positives", align: "right", render: (row) => row.false_positives },
  { key: "precision", label: "Precision", align: "right", render: (row) => formatPercent(row.precision) },
  { key: "recall", label: "Recall", align: "right", render: (row) => formatPercent(row.recall) },
  { key: "f1", label: "F1", align: "right", render: (row) => formatPercent(row.f1) },
  {
    key: "fp30",
    label: "FP / 30 days",
    align: "right",
    render: (row) => formatNumber(row.false_positives_per_30_days, 2),
  },
];

const TYPE_COLUMNS: DataColumn<EvaluationByType>[] = [
  { key: "subject", label: "Subject", render: (row) => subjectName(row.subject) },
  { key: "type", label: "Anomaly type", render: (row) => humanize(row.anomaly_type) },
  { key: "days", label: "True days", align: "right", render: (row) => row.true_days },
  { key: "exact", label: "Detected Exact", align: "right", render: (row) => row.detected_days_exact },
  {
    key: "tolerance",
    label: "Detected ±1 Day",
    align: "right",
    render: (row) => row.detected_days_tolerance_1_day,
  },
  {
    key: "recallExact",
    label: "Recall Exact",
    align: "right",
    render: (row) => formatPercent(row.recall_exact),
  },
  {
    key: "recallTolerance",
    label: "Recall ±1 Day",
    align: "right",
    render: (row) => formatPercent(row.recall_tolerance_1_day),
  },
];

const DELAY_COLUMNS: DataColumn<DetectionDelay>[] = [
  { key: "subject", label: "Subject", render: (row) => subjectName(row.subject) },
  { key: "id", label: "Anomaly ID", render: (row) => row.anomaly_id },
  { key: "type", label: "Anomaly type", render: (row) => humanize(row.anomaly_type) },
  { key: "start", label: "Start date", render: (row) => row.start_date },
  { key: "end", label: "End date", render: (row) => row.end_date },
  { key: "detected", label: "Detected", render: (row) => yesNo(row.detected) },
  { key: "first", label: "First detection", render: (row) => row.first_detection_date ?? "-" },
  { key: "delay", label: "Delay (days)", align: "right", render: (row) => row.detection_delay_days ?? "-" },
];

const FALSE_POSITIVE_COLUMNS: DataColumn<FalsePositiveDay>[] = [
  { key: "subject", label: "Subject", render: (row) => subjectName(row.subject) },
  { key: "date", label: "Date", render: (row) => row.usage_date },
  { key: "source", label: "Prediction source", render: (row) => humanize(row.prediction_source) },
  { key: "planned", label: "Planned event", render: (row) => yesNo(row.planned_event) },
  { key: "level", label: "Alert level", render: (row) => humanize(row.alert_level ?? "none") },
  { key: "methods", label: "Methods triggered", render: (row) => formatMethods(row.methods_triggered) },
  {
    key: "delta",
    label: "Relative delta",
    align: "right",
    render: (row) => formatPercent(row.relative_delta),
  },
  { key: "reason", label: "Reason", render: (row) => row.reason },
];

const EVENT_COLUMNS: DataColumn<EventLevelEvaluation>[] = [
  { key: "subject", label: "Subject", render: (row) => subjectName(row.subject) },
  { key: "true", label: "True events", align: "right", render: (row) => row.true_events },
  { key: "predicted", label: "Predicted events", align: "right", render: (row) => row.predicted_events },
  { key: "detected", label: "Detected events", align: "right", render: (row) => row.detected_events },
  {
    key: "falsePositive",
    label: "False-positive events",
    align: "right",
    render: (row) => row.false_positive_events,
  },
  { key: "precision", label: "Event precision", align: "right", render: (row) => formatPercent(row.event_precision) },
  {
    key: "recall",
    label: "Event-level detection rate",
    align: "right",
    render: (row) => formatPercent(row.event_recall),
  },
  { key: "f1", label: "Event F1", align: "right", render: (row) => formatPercent(row.event_f1) },
];

const CALIBRATION_COLUMNS: DataColumn<CalibrationSummary>[] = [
  { key: "method", label: "Method", render: (row) => subjectName(row.method) },
  { key: "candidate", label: "Selected candidate", render: (row) => row.candidate_id },
  { key: "parameters", label: "Parameters", render: (row) => row.parameters },
  { key: "predictions", label: "Predicted days", align: "right", render: (row) => row.predicted_positive_days },
  { key: "precision", label: "Precision", align: "right", render: (row) => formatPercent(row.precision) },
  { key: "recall", label: "Recall", align: "right", render: (row) => formatPercent(row.recall) },
  { key: "f1", label: "F1", align: "right", render: (row) => formatPercent(row.f1) },
  { key: "events", label: "Event recall", align: "right", render: (row) => formatPercent(row.event_recall) },
];

const ROBUSTNESS_COLUMNS: DataColumn<ScenarioRobustness>[] = [
  {
    key: "scenario",
    label: "Scenario",
    render: (row) => row.scenario_id === "seed_42_main" ? "Main (seed 42)" : humanize(row.scenario_id),
  },
  { key: "seed", label: "Seed", align: "right", render: (row) => row.random_seed },
  {
    key: "precision",
    label: "Ops precision",
    align: "right",
    render: (row) => formatPercent(row.operational_precision),
  },
  {
    key: "recall",
    label: "Ops recall",
    align: "right",
    render: (row) => formatPercent(row.operational_recall),
  },
  {
    key: "f1",
    label: "Ops F1",
    align: "right",
    render: (row) => formatPercent(row.operational_f1),
  },
  {
    key: "eventRecall",
    label: "Event recall",
    align: "right",
    render: (row) => formatPercent(row.event_recall),
  },
  {
    key: "fp30",
    label: "FP / 30 days",
    align: "right",
    render: (row) => formatNumber(row.operational_false_positives_per_30_days, 2),
  },
];

export function Evaluation({
  summary,
  byType,
  delays,
  falsePositives,
  eventLevel,
  calibration,
  scenarioRobustness,
}: EvaluationProps) {
  const [matchingMode, setMatchingMode] = useState("exact_day");
  const filteredSummary = useMemo(
    () => summary.filter((row) => row.matching_mode === matchingMode),
    [matchingMode, summary],
  );
  const agreement = filteredSummary.find((row) => row.subject === "agreement_alert");
  const eventMatchingMode =
    matchingMode === "tolerance_1_day" ? "event_window_tolerance_1_day" : "event_window";
  const filteredEvents = eventLevel.filter((row) => row.matching_mode === eventMatchingMode);
  const agreementEvents = filteredEvents.find((row) => row.subject === "agreement_alert");
  const selectedCalibration = calibration.filter((row) => row.selected === 1);
  const modeLabel = matchingModeName(matchingMode);

  return (
    <div className="page">
      <header className="page-header page-header--with-control">
        <div>
          <h1>Method Evaluation</h1>
          <p>Exported detector and agreement-alert metrics against injected anomaly labels.</p>
        </div>
        <label className="select-control">
          <span>Matching mode</span>
          <select value={matchingMode} onChange={(event) => setMatchingMode(event.target.value)}>
            <option value="exact_day">Exact day</option>
            <option value="tolerance_1_day">Within one day</option>
          </select>
        </label>
      </header>

      <SectionCard
        title="Evaluation stages"
        description="Metrics remain separate so detector sensitivity is not confused with operational alert quality."
      >
        <div className="evaluation-stage-grid">
          <div>
            <strong>Raw detector metrics</strong>
            <p>Rolling Z-score, STL, and Isolation Forest flags before alert policy.</p>
          </div>
          <div>
            <strong>Raw alert candidate</strong>
            <p>Agreement and severity candidates before planned-event suppression.</p>
          </div>
          <div>
            <strong>Operational alert metrics</strong>
            <p>Final agreement alerts after planned-event suppression.</p>
          </div>
        </div>
      </SectionCard>

      <section className="metric-grid metric-grid--four">
        <MetricCard
          label="Operational alert precision"
          value={formatPercent(agreement?.precision)}
          note={modeLabel}
          icon={Crosshair}
        />
        <MetricCard
          label="Operational alert recall"
          value={formatPercent(agreement?.recall)}
          note={modeLabel}
          icon={Gauge}
          tone="warning"
        />
        <MetricCard
          label="Operational alert F1"
          value={formatPercent(agreement?.f1)}
          note={modeLabel}
          icon={Target}
          tone="purple"
        />
        <MetricCard
          label="Operational FP / 30 days"
          value={formatNumber(agreement?.false_positives_per_30_days, 2)}
          note="Alert noise"
          icon={BellRing}
          tone="critical"
        />
      </section>

      <div className="evaluation-chart-grid">
        <SectionCard
          title="Day-level precision, recall, and F1"
          description="Raw detectors, raw alert candidates, and final operational alerts."
        >
          <EvaluationMetricChart rows={filteredSummary} />
        </SectionCard>
        <SectionCard title="False positives per 30 days by evaluation subject">
          <FalsePositiveChart rows={filteredSummary} />
        </SectionCard>
      </div>

      <section className="metric-grid metric-grid--four">
        <MetricCard
          label="Agreement event precision"
          value={formatPercent(agreementEvents?.event_precision)}
          note={modeLabel}
          icon={Crosshair}
        />
        <MetricCard
          label="Agreement event recall"
          value={formatPercent(agreementEvents?.event_recall)}
          note={modeLabel}
          icon={CalendarRange}
          tone="warning"
        />
        <MetricCard
          label="Agreement event F1"
          value={formatPercent(agreementEvents?.event_f1)}
          note="Contiguous alert runs"
          icon={Target}
          tone="purple"
        />
        <MetricCard
          label="Suppressed planned candidates"
          value={falsePositives
            .filter((row) => row.prediction_source === "suppressed_alerts")
            .length.toLocaleString()}
          note="Not operational alerts"
          icon={BellRing}
          tone="success"
        />
      </section>

      <SectionCard title="Interpretation">
        <div className="interpretation-list">
          <div>
            <Target aria-hidden="true" />
            <p>Day-level recall is conservative for long gradual or persistent anomalies.</p>
          </div>
          <div>
            <TrendingDown aria-hidden="true" />
            <p>Event-level detection shows whether an anomaly event was detected at least once.</p>
          </div>
          <div>
            <Gauge aria-hidden="true" />
            <p>Agreement alerts prioritize high-confidence operational alerts over maximum recall.</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Scenario robustness check"
        description="Main-scenario operational precision is not a production guarantee; alternate deterministic synthetic runs show metric variability."
      >
        <DataTable
          columns={ROBUSTNESS_COLUMNS}
          rows={scenarioRobustness}
          rowKey={(row) => row.scenario_id}
        />
      </SectionCard>

      <details className="summary-details">
        <summary>
          Day-level evaluation summary <span>{filteredSummary.length} rows</span>
        </summary>
        <DataTable
          columns={SUMMARY_COLUMNS}
          rows={filteredSummary}
          rowKey={(row) => `${row.subject}-${row.matching_mode}`}
        />
      </details>

      <div className="detail-stack">
        <details open>
          <summary>
            Event-level evaluation ({modeLabel}) <span>{filteredEvents.length} rows</span>
          </summary>
          <DataTable
            columns={EVENT_COLUMNS}
            rows={filteredEvents}
            rowKey={(row) => `${row.subject}-${row.matching_mode}`}
          />
        </details>
        <details>
          <summary>
            Selected calibration settings <span>{selectedCalibration.length} rows</span>
          </summary>
          <div className="detail-callout">
            <Settings2 aria-hidden="true" />
            <p>Selection score combines day-level F1 and event recall over a bounded candidate sweep.</p>
          </div>
          <DataTable
            columns={CALIBRATION_COLUMNS}
            rows={selectedCalibration}
            rowKey={(row) => row.candidate_id}
          />
        </details>
        <details>
          <summary>
            Evaluation by anomaly type <span>{byType.length} rows</span>
          </summary>
          <DataTable
            columns={TYPE_COLUMNS}
            rows={byType}
            rowKey={(row) => `${row.subject}-${row.anomaly_type}`}
          />
        </details>
        <details>
          <summary>
            Detection delay <span>{delays.length} rows</span>
          </summary>
          <DataTable
            columns={DELAY_COLUMNS}
            rows={delays}
            rowKey={(row) => `${row.subject}-${row.anomaly_id}`}
          />
        </details>
        <details>
          <summary>
            False positive days across all methods and alert stages{" "}
            <span>{falsePositives.length} rows</span>
          </summary>
          <DataTable
            columns={FALSE_POSITIVE_COLUMNS}
            rows={falsePositives}
            rowKey={(row, index) => `${row.subject}-${row.usage_date}-${index}`}
          />
        </details>
      </div>
    </div>
  );
}
