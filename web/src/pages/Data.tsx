import { Database } from "lucide-react";
import { DataTable, type DataColumn } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatUsd } from "../lib/format";
import type { SyntheticCurRow, SyntheticCurSample } from "../lib/types";

interface DataProps {
  sample: SyntheticCurSample | null;
}

interface CurMappingRow {
  column: string;
  cur: string;
  purpose: string;
}

const CUR_MAPPING: CurMappingRow[] = [
  { column: "usage_date", cur: "lineItem/UsageStartDate", purpose: "Daily aggregation key" },
  { column: "billing_period_start", cur: "bill/BillingPeriodStartDate", purpose: "Billing period" },
  { column: "usage_account_id", cur: "lineItem/UsageAccountId", purpose: "Account grouping" },
  { column: "service", cur: "lineItem/ProductCode", purpose: "Service-level breakdown" },
  { column: "region", cur: "product/region", purpose: "Region-level breakdown" },
  { column: "usage_amount / usage_unit", cur: "lineItem/UsageAmount", purpose: "Usage volume" },
  { column: "cost_usd", cur: "lineItem/UnblendedCost", purpose: "Cost signal analyzed" },
  { column: "operation", cur: "lineItem/Operation", purpose: "API operation context" },
  { column: "usage_type", cur: "lineItem/UsageType", purpose: "Usage type context" },
  { column: "tag_environment / tag_team", cur: "resourceTags/user:*", purpose: "Cost-allocation tags" },
  { column: "line_item_type", cur: "lineItem/LineItemType", purpose: "Line item classification" },
  { column: "billing_currency", cur: "lineItem/CurrencyCode", purpose: "Currency (USD)" },
];

const MAPPING_COLUMNS: DataColumn<CurMappingRow>[] = [
  { key: "column", label: "Synthetic column", render: (row) => <code>{row.column}</code> },
  { key: "cur", label: "AWS CUR field", render: (row) => <code>{row.cur}</code> },
  { key: "purpose", label: "Purpose", render: (row) => row.purpose },
];

const ROW_COLUMNS: DataColumn<SyntheticCurRow>[] = [
  { key: "usage_date", label: "Date", render: (row) => row.usage_date },
  { key: "service", label: "Service", render: (row) => row.service },
  { key: "region", label: "Region", render: (row) => row.region },
  { key: "tag_environment", label: "Env", render: (row) => row.tag_environment },
  { key: "tag_team", label: "Team", render: (row) => row.tag_team },
  { key: "usage_type", label: "Usage type", render: (row) => row.usage_type },
  {
    key: "usage_amount",
    label: "Usage",
    align: "right",
    render: (row) => `${row.usage_amount.toLocaleString("en-US")} ${row.usage_unit}`,
  },
  { key: "cost_usd", label: "Cost", align: "right", render: (row) => formatUsd(row.cost_usd) },
  {
    key: "label",
    label: "Ground truth",
    render: (row) =>
      row.is_anomaly === 1 ? (
        <StatusBadge tone="critical">{row.anomaly_type}</StatusBadge>
      ) : row.planned_event === 1 ? (
        <StatusBadge tone="warning">planned</StatusBadge>
      ) : (
        <StatusBadge tone="muted">normal</StatusBadge>
      ),
  },
];

export function Data({ sample }: DataProps) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Synthetic CUR-like Data</h1>
          <p>
            The pipeline operates on AWS Cost and Usage Report (CUR) style billing rows.
            Data is fully synthetic and deterministic so anomaly labels and evaluation stay
            reproducible. Real CUR data is not ingested.
          </p>
        </div>
      </header>

      <div className="metric-grid">
        <MetricCard
          icon={Database}
          label="Total raw rows"
          value={sample ? sample.total_rows.toLocaleString("en-US") : "-"}
          note="Full synthetic CUR-like dataset"
        />
        <MetricCard
          icon={Database}
          label="Sample shown"
          value={sample ? sample.sample_rows.toLocaleString("en-US") : "-"}
          note="First rows exported for preview"
        />
        <MetricCard
          icon={Database}
          label="Columns"
          value={sample ? String(sample.columns.length) : "-"}
          note="CUR-equivalent fields + labels"
        />
      </div>

      <SectionCard
        title="AWS CUR Column Mapping"
        description="Each synthetic column mirrors a real CUR field so the pipeline reads realistic billing data."
      >
        <DataTable columns={MAPPING_COLUMNS} rows={CUR_MAPPING} rowKey={(row) => row.column} />
        <p>
          The <code>is_anomaly</code>, <code>anomaly_type</code>, <code>anomaly_id</code>,{" "}
          <code>planned_event</code>, and <code>planned_event_id</code> columns are synthetic
          ground-truth labels that do not exist in real CUR. They exist only to make evaluation
          reproducible.
        </p>
      </SectionCard>

      <SectionCard
        title="Raw Data Preview"
        description={
          sample
            ? `First ${sample.sample_rows} of ${sample.total_rows.toLocaleString("en-US")} synthetic CUR-like rows.`
            : "Synthetic data sample was not exported."
        }
      >
        <DataTable
          columns={ROW_COLUMNS}
          rows={sample?.rows ?? []}
          rowKey={(_, index) => String(index)}
          emptyTitle="Run the pipeline and export to preview synthetic data."
        />
      </SectionCard>
    </div>
  );
}
