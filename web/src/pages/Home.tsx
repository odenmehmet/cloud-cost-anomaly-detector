import {
  Activity,
  ArrowRight,
  BarChart3,
  CalendarDays,
  CircleOff,
  Database,
  Gauge,
  Search,
  ShieldAlert,
} from "lucide-react";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import type { DashboardManifest, PageId } from "../lib/types";

interface HomeProps {
  manifest: DashboardManifest;
  onNavigate: (page: PageId) => void;
}

const PIPELINE_STEPS = [
  "Synthetic data",
  "Preprocessing",
  "Detection",
  "Alerts",
  "Contributors",
  "Evaluation",
];

const PRIMARY_VIEWS: Array<{
  page: PageId;
  title: string;
  description: string;
  icon: typeof Gauge;
}> = [
  {
    page: "overview",
    title: "Cost Overview",
    description: "Review cost trends, seasonality, labels, and alerts.",
    icon: Gauge,
  },
  {
    page: "anomaly-detail",
    title: "Alert Investigation",
    description: "Inspect local context, method evidence, and contributors.",
    icon: Search,
  },
  {
    page: "evaluation",
    title: "Method Evaluation",
    description: "Compare exported precision, recall, F1, and alert noise.",
    icon: BarChart3,
  },
];

export function Home({ manifest, onNavigate }: HomeProps) {
  return (
    <div className="page page--home">
      <header className="home-intro">
        <div>
          <h1>Cloud Cost Anomaly Detector</h1>
          <p>
            Synthetic billing data, anomaly detection, contributor analysis, and evaluation in
            one workspace.
          </p>
        </div>
        <div className="home-intro__meta">
          <span>Latest export</span>
          <strong>{manifest.generated_at.slice(0, 10)}</strong>
        </div>
      </header>

      <section className="metric-grid metric-grid--five" aria-label="Dataset summary">
        <MetricCard
          label="Days analyzed"
          value={manifest.total_days.toLocaleString()}
          note="Daily observations"
          icon={CalendarDays}
        />
        <MetricCard
          label="Total alerts"
          value={manifest.total_alerts.toLocaleString()}
          note="Agreement policy output"
          icon={Activity}
          tone="purple"
        />
        <MetricCard
          label="Planned suppressions"
          value={manifest.suppressed_planned_events.toLocaleString()}
          note="Excluded from operations"
          icon={CircleOff}
          tone="warning"
        />
        <MetricCard
          label="Critical alerts"
          value={manifest.critical_alerts.toLocaleString()}
          note="Strong agreement"
          icon={ShieldAlert}
          tone="critical"
        />
        <MetricCard
          label="True anomaly days"
          value={manifest.true_anomaly_days.toLocaleString()}
          note="Injected ground truth"
          icon={Database}
          tone="success"
        />
      </section>

      <div className="context-note">
        <Database aria-hidden="true" />
        <p>
          True anomaly days are injected ground-truth labels; total alerts are final
          agreement-policy outputs.
        </p>
      </div>

      <SectionCard title="Detection pipeline">
        <div className="pipeline-flow">
          {PIPELINE_STEPS.map((step, index) => (
            <div className="pipeline-step" key={step}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{step}</strong>
              {index < PIPELINE_STEPS.length - 1 ? <ArrowRight aria-hidden="true" /> : null}
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="home-grid">
        <SectionCard title="Primary views">
          <div className="primary-view-list">
            {PRIMARY_VIEWS.map(({ page, title, description, icon: Icon }) => (
              <button type="button" key={page} onClick={() => onNavigate(page)}>
                <span className="primary-view-list__icon">
                  <Icon aria-hidden="true" />
                </span>
                <span>
                  <strong>{title}</strong>
                  <small>{description}</small>
                </span>
                <ArrowRight aria-hidden="true" />
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Scope">
          <dl className="scope-table">
            <div>
              <dt>Data source</dt>
              <dd>Synthetic CUR-like billing data</dd>
            </div>
            <div>
              <dt>Analysis</dt>
              <dd>Anomaly detection and non-causal contributor ranking</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>Local offline pipeline and web dashboard</dd>
            </div>
            <div>
              <dt>Excluded</dt>
              <dd>Live AWS ingestion, notifications, and causal attribution</dd>
            </div>
          </dl>
        </SectionCard>
      </div>
    </div>
  );
}
