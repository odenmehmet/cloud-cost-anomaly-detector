export interface DashboardManifest {
  generated_at: string;
  total_days: number;
  total_alerts: number;
  warning_alerts: number;
  critical_alerts: number;
  suppressed_planned_events: number;
  true_anomaly_days: number;
  planned_event_days: number;
  data_files_available: string[];
}

export interface DailyFeature {
  usage_date: string;
  total_cost_usd: number;
  is_anomaly: number;
  anomaly_types: string;
  planned_event: number;
  planned_event_ids: string;
  account_count: number;
  cost_rolling_mean_7: number;
  top_service: string;
  top_region: string;
}

export interface MethodResult {
  usage_date: string;
  method: string;
  is_flagged: number;
  score: number;
  threshold: number;
  actual_cost: number;
  expected_cost: number;
  deviation: number;
  relative_deviation: number;
  severity_hint: string;
  explanation: string;
}

export interface Alert {
  alert_id: string;
  usage_date: string;
  alert_level: string;
  methods_triggered: string;
  method_count: number;
  actual_cost: number;
  expected_cost: number;
  relative_delta: number;
  max_method_score: number;
  max_relative_deviation: number;
  method_severity_hints: string;
  is_true_anomaly: number;
  anomaly_type: string;
  planned_event: number;
  top_service: string;
  top_region: string;
  alert_reason: string;
}

export interface Contributor {
  alert_id: string;
  usage_date: string;
  alert_level: string;
  service: string;
  region: string;
  cost_usd: number;
  previous_7d_avg_cost: number;
  delta_cost: number;
  contribution_share: number;
  contribution_basis: string;
  rank: number;
  contributor_reason: string;
}

export interface SuppressedAlert {
  suppression_id: string;
  usage_date: string;
  suppression_type: string;
  methods_triggered: string;
  method_count: number;
  actual_cost: number;
  expected_cost: number;
  relative_delta: number;
  planned_event_id: string;
  suppression_reason: string;
}

export interface CalibrationSummary {
  method: string;
  candidate_id: string;
  parameters: string;
  predicted_positive_days: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1: number;
  event_recall: number;
  selection_score: number;
  selected: number;
}

export interface EventLevelEvaluation {
  subject: string;
  matching_mode: string;
  true_events: number;
  predicted_events: number;
  detected_events: number;
  false_positive_events: number;
  missed_events: number;
  event_precision: number;
  event_recall: number;
  event_f1: number;
}

export interface StlComponent {
  usage_date: string;
  actual_cost: number;
  trend: number;
  seasonal: number;
  residual: number;
  expected_cost: number;
  residual_score: number;
  is_flagged: number;
}

export interface EvaluationSummary {
  subject: string;
  matching_mode: string;
  total_days: number;
  true_anomaly_days: number;
  predicted_positive_days: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1: number;
  false_positives_per_30_days: number;
}

export interface EvaluationByType {
  subject: string;
  anomaly_type: string;
  true_days: number;
  detected_days_exact: number;
  detected_days_tolerance_1_day: number;
  recall_exact: number;
  recall_tolerance_1_day: number;
}

export interface DetectionDelay {
  subject: string;
  anomaly_id: string;
  anomaly_type: string;
  start_date: string;
  end_date: string;
  detected: number;
  first_detection_date: string | null;
  detection_delay_days: number | null;
}

export interface FalsePositiveDay {
  subject: string;
  usage_date: string;
  prediction_source: string;
  planned_event: number;
  anomaly_type: string;
  alert_level: string | null;
  methods_triggered: string | null;
  actual_cost: number;
  expected_cost: number;
  relative_delta: number;
  reason: string;
}

export interface ScenarioRobustness {
  scenario_id: string;
  random_seed: number;
  calibration_mode: string;
  true_anomaly_days: number;
  true_anomaly_events: number;
  operational_alerts: number;
  suppressed_planned_candidates: number;
  operational_precision: number;
  operational_recall: number;
  operational_f1: number;
  operational_false_positives_per_30_days: number;
  event_precision: number;
  event_recall: number;
  event_f1: number;
}

export interface SyntheticCurRow {
  usage_date: string;
  billing_period_start: string;
  usage_account_id: number;
  service: string;
  region: string;
  usage_amount: number;
  usage_unit: string;
  cost_usd: number;
  operation: string;
  usage_type: string;
  tag_environment: string;
  tag_team: string;
  line_item_type: string;
  billing_currency: string;
  source_record_count: number;
  is_anomaly: number;
  anomaly_type: string;
  anomaly_id: string;
  planned_event: number;
  planned_event_id: string;
}

export interface SyntheticCurSample {
  sample_rows: number;
  total_rows: number;
  columns: string[];
  rows: SyntheticCurRow[];
}

export interface DashboardData {
  manifest: DashboardManifest | null;
  syntheticSample: SyntheticCurSample | null;
  dailyFeatures: DailyFeature[];
  methodResults: MethodResult[];
  alerts: Alert[];
  suppressedAlerts: SuppressedAlert[];
  contributors: Contributor[];
  stlComponents: StlComponent[];
  calibrationSummary: CalibrationSummary[];
  evaluationSummary: EvaluationSummary[];
  eventLevelEvaluation: EventLevelEvaluation[];
  evaluationByType: EvaluationByType[];
  detectionDelay: DetectionDelay[];
  falsePositiveDays: FalsePositiveDay[];
  scenarioRobustness: ScenarioRobustness[];
}

export interface DataLoadResult {
  data: DashboardData;
  missingFiles: string[];
}

export type PageId = "home" | "data" | "overview" | "anomaly-detail" | "evaluation";
