"""Configuration and constants for synthetic data generation and processing."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DATA_DIR = DATA_DIR / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"

SYNTHETIC_CUR_LIKE_PATH = RAW_DATA_DIR / "synthetic_cur_like_daily.csv"
ANOMALY_CATALOG_PATH = RAW_DATA_DIR / "anomaly_catalog.csv"
PLANNED_EVENT_CATALOG_PATH = RAW_DATA_DIR / "planned_event_catalog.csv"
DAILY_TOTAL_COST_PATH = PROCESSED_DATA_DIR / "daily_total_cost.csv"
DAILY_SERVICE_COST_PATH = PROCESSED_DATA_DIR / "daily_service_cost.csv"
DAILY_REGION_COST_PATH = PROCESSED_DATA_DIR / "daily_region_cost.csv"
DAILY_SERVICE_REGION_COST_PATH = PROCESSED_DATA_DIR / "daily_service_region_cost.csv"
DAILY_FEATURES_PATH = PROCESSED_DATA_DIR / "daily_features.csv"
ZSCORE_RESULTS_PATH = OUTPUTS_DATA_DIR / "zscore_results.csv"
STL_RESULTS_PATH = OUTPUTS_DATA_DIR / "stl_results.csv"
ISOLATION_FOREST_RESULTS_PATH = OUTPUTS_DATA_DIR / "isolation_forest_results.csv"
STL_COMPONENTS_PATH = OUTPUTS_DATA_DIR / "stl_components.csv"
METHOD_RESULTS_PATH = OUTPUTS_DATA_DIR / "method_results.csv"
ALERTS_PATH = OUTPUTS_DATA_DIR / "alerts.csv"
SUPPRESSED_ALERTS_PATH = OUTPUTS_DATA_DIR / "suppressed_alerts.csv"
CONTRIBUTORS_PATH = OUTPUTS_DATA_DIR / "contributors.csv"
ALERT_METHOD_SUMMARY_PATH = OUTPUTS_DATA_DIR / "alert_method_summary.csv"
CALIBRATION_SUMMARY_PATH = REPORTS_DIR / "calibration_summary.csv"
EVALUATION_SUMMARY_PATH = REPORTS_DIR / "evaluation_summary.csv"
EVALUATION_BY_TYPE_PATH = REPORTS_DIR / "evaluation_by_type.csv"
EVENT_LEVEL_EVALUATION_PATH = REPORTS_DIR / "event_level_evaluation.csv"
DETECTION_DELAY_PATH = REPORTS_DIR / "detection_delay.csv"
FALSE_POSITIVE_DAYS_PATH = REPORTS_DIR / "false_positive_days.csv"
EVALUATION_DAILY_PREDICTIONS_PATH = REPORTS_DIR / "evaluation_daily_predictions.csv"

DEFAULT_RANDOM_SEED = 42
START_DATE = "2025-10-01"
NUM_DAYS = 180

ZSCORE_ROLLING_WINDOW = 14
ZSCORE_MIN_PERIODS = 4
ZSCORE_THRESHOLD = 3.0
STL_PERIOD = 7
STL_RESIDUAL_THRESHOLD = 3.0
ISOLATION_FOREST_N_ESTIMATORS = 200
ISOLATION_FOREST_CONTAMINATION = 0.08

CALIBRATION_ZSCORE_WINDOWS = [7, 14, 21]
CALIBRATION_ZSCORE_THRESHOLDS = [2.5, 3.0, 3.5]
CALIBRATION_STL_THRESHOLDS = [2.5, 3.0, 3.5]
CALIBRATION_ISOLATION_CONTAMINATIONS = [0.04, 0.06, 0.08, 0.10, 0.12]

# Operational alerts require meaningful upward cost deviation as well as detector
# evidence. Planned-event candidates are exported separately and suppressed.
ALERT_WARNING_RELATIVE_DELTA = 0.05
ALERT_CRITICAL_RELATIVE_DELTA = 0.10
ALERT_STRONG_SINGLE_METHOD_DELTA = 0.12
ALERT_WARNING_MIN_METHODS = 2
ALERT_CRITICAL_MIN_METHODS = 3

TOP_CONTRIBUTOR_LIMIT = 5
EVALUATION_SUBJECTS = [
    "zscore",
    "stl",
    "isolation_forest",
    "raw_alert_candidate",
    "agreement_alert",
]
EVALUATION_MATCHING_MODES = ["exact_day", "tolerance_1_day"]
EVENT_MATCHING_MODES = ["event_window", "event_window_tolerance_1_day"]

SERVICES = [
    "AmazonEC2",
    "AmazonS3",
    "AWSLambda",
    "AmazonRDS",
    "AmazonCloudFront",
    "AmazonEKS",
    "AmazonDynamoDB",
    "AmazonCloudWatch",
]

REGIONS = [
    "us-east-1",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
]

TAG_ENVIRONMENTS = ["prod", "staging", "dev"]
TAG_TEAMS = ["platform", "data", "web", "ml"]
ACCOUNT_BY_ENVIRONMENT = {
    "prod": "111111111111",
    "staging": "222222222222",
    "dev": "333333333333",
}

SERVICE_METADATA = {
    "AmazonEC2": {
        "base_usage": 85.0,
        "unit_rate": 0.096,
        "usage_unit": "Hours",
        "operation": "RunInstances",
        "usage_type": "BoxUsage",
    },
    "AmazonS3": {
        "base_usage": 540.0,
        "unit_rate": 0.023,
        "usage_unit": "GB-Mo",
        "operation": "StandardStorage",
        "usage_type": "TimedStorage-ByteHrs",
    },
    "AWSLambda": {
        "base_usage": 2_400_000.0,
        "unit_rate": 0.0000002,
        "usage_unit": "Requests",
        "operation": "Invoke",
        "usage_type": "Request",
    },
    "AmazonRDS": {
        "base_usage": 64.0,
        "unit_rate": 0.135,
        "usage_unit": "Hours",
        "operation": "CreateDBInstance",
        "usage_type": "InstanceUsage",
    },
    "AmazonCloudFront": {
        "base_usage": 820.0,
        "unit_rate": 0.085,
        "usage_unit": "GB",
        "operation": "DataTransfer-Out-Bytes",
        "usage_type": "DataTransfer-Out-Bytes",
    },
    "AmazonEKS": {
        "base_usage": 58.0,
        "unit_rate": 0.10,
        "usage_unit": "Hours",
        "operation": "ClusterUsage",
        "usage_type": "EKS-Hours",
    },
    "AmazonDynamoDB": {
        "base_usage": 7_500.0,
        "unit_rate": 0.00065,
        "usage_unit": "RequestUnits",
        "operation": "ReadWriteCapacity",
        "usage_type": "ReadWriteCapacityUnit-Hrs",
    },
    "AmazonCloudWatch": {
        "base_usage": 1_400.0,
        "unit_rate": 0.003,
        "usage_unit": "Metrics",
        "operation": "MetricMonitorUsage",
        "usage_type": "MetricStorage",
    },
}

REGION_COST_MULTIPLIERS = {
    "us-east-1": 1.00,
    "eu-west-1": 1.08,
    "eu-central-1": 1.11,
    "ap-southeast-1": 1.14,
}

ENVIRONMENT_USAGE_MULTIPLIERS = {"prod": 1.00, "staging": 0.38, "dev": 0.24}
TEAM_USAGE_MULTIPLIERS = {"platform": 1.05, "data": 1.12, "web": 0.95, "ml": 1.18}
WEEKLY_SEASONALITY_MULTIPLIERS = {
    0: 1.07,
    1: 1.05,
    2: 1.04,
    3: 1.03,
    4: 1.01,
    5: 0.87,
    6: 0.84,
}

LONG_TERM_TREND_DAILY_RATE = 0.0007
USAGE_NOISE_STDDEV = 0.045
COST_NOISE_STDDEV = 0.012
DAILY_GLOBAL_NOISE_STDDEV = 0.012
SERVICE_DAILY_NOISE_STDDEV = 0.018

# Events stay service/region-specific, but their duration and magnitude are
# aligned with daily-total Level 1 detection rather than being structurally
# invisible after aggregation.
ANOMALY_EVENTS = [
    {
        "anomaly_id": "ANOM-001",
        "anomaly_type": "one_day_spike",
        "start_day": 50,
        "duration_days": 1,
        "affected_service": "AmazonEC2",
        "affected_region": "us-east-1",
        "magnitude": 5.00,
        "description": "Single-day EC2 runaway usage spike in us-east-1.",
    },
    {
        "anomaly_id": "ANOM-002",
        "anomaly_type": "persistent_step_increase",
        "start_day": 75,
        "duration_days": 5,
        "affected_service": "AmazonRDS",
        "affected_region": "ap-southeast-1",
        "magnitude": 3.00,
        "description": "Five-day RDS capacity step increase in ap-southeast-1.",
    },
    {
        "anomaly_id": "ANOM-003",
        "anomaly_type": "gradual_drift",
        "start_day": 110,
        "duration_days": 8,
        "affected_service": "AmazonS3",
        "affected_region": "eu-central-1",
        "start_magnitude": 1.10,
        "magnitude": 2.40,
        "description": "Eight-day S3 storage drift in eu-central-1.",
    },
    {
        "anomaly_id": "ANOM-004",
        "anomaly_type": "service_local_anomaly",
        "start_day": 145,
        "duration_days": 3,
        "affected_service": "AmazonDynamoDB",
        "affected_region": "ap-southeast-1",
        "magnitude": 5.00,
        "description": "Localized DynamoDB capacity anomaly in ap-southeast-1.",
    },
    {
        "anomaly_id": "ANOM-005",
        "anomaly_type": "multi_day_burst",
        "start_day": 160,
        "duration_days": 3,
        "affected_service": "AmazonEC2",
        "affected_region": "eu-central-1",
        "magnitude": 4.00,
        "description": "Three-day EC2 workload burst in eu-central-1.",
    },
]

PLANNED_EVENTS = [
    {
        "planned_event_id": "PLAN-001",
        "planned_event_type": "legitimate_usage_increase",
        "start_day": 62,
        "duration_days": 5,
        "affected_service": "AmazonCloudFront",
        "affected_region": "us-east-1",
        "magnitude": 1.25,
        "description": "Planned CloudFront traffic growth for a business event.",
    },
]

CUR_LIKE_COLUMNS = [
    "usage_date",
    "billing_period_start",
    "usage_account_id",
    "service",
    "region",
    "usage_amount",
    "usage_unit",
    "cost_usd",
    "operation",
    "usage_type",
    "tag_environment",
    "tag_team",
    "line_item_type",
    "billing_currency",
    "source_record_count",
    "is_anomaly",
    "anomaly_type",
    "anomaly_id",
    "planned_event",
    "planned_event_id",
]

ANOMALY_CATALOG_COLUMNS = [
    "anomaly_id",
    "anomaly_type",
    "start_date",
    "end_date",
    "affected_service",
    "affected_region",
    "magnitude",
    "description",
]

PLANNED_EVENT_CATALOG_COLUMNS = [
    "planned_event_id",
    "planned_event_type",
    "start_date",
    "end_date",
    "affected_service",
    "affected_region",
    "magnitude",
    "description",
]

DAILY_TOTAL_COST_COLUMNS = [
    "usage_date",
    "total_cost_usd",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
]

PROCESSED_DAILY_TOTAL_COST_COLUMNS = [
    "usage_date",
    "total_cost_usd",
    "total_usage_amount",
    "service_count",
    "region_count",
    "account_count",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
]

DAILY_SERVICE_COST_COLUMNS = [
    "usage_date",
    "service",
    "service_cost_usd",
    "service_usage_amount",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
]

DAILY_REGION_COST_COLUMNS = [
    "usage_date",
    "region",
    "region_cost_usd",
    "region_usage_amount",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
]

DAILY_SERVICE_REGION_COST_COLUMNS = [
    "usage_date",
    "service",
    "region",
    "service_region_cost_usd",
    "service_region_usage_amount",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
]

DAILY_FEATURE_COLUMNS = [
    "usage_date",
    "total_cost_usd",
    "total_usage_amount",
    "service_count",
    "region_count",
    "account_count",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
    "day_of_week",
    "is_weekend",
    "cost_rolling_mean_7",
    "cost_rolling_std_7",
    "cost_rolling_mean_14",
    "cost_rolling_std_14",
    "cost_rolling_mean_30",
    "cost_rolling_std_30",
    "usage_rolling_mean_7",
    "usage_rolling_std_7",
    "pct_change_1d",
    "pct_change_7d",
    "cost_diff_1d",
    "cost_diff_7d",
    "top_service",
    "top_service_cost_usd",
    "top_service_share",
    "top_service_share_change_1d",
    "top_region",
    "top_region_cost_usd",
    "top_region_share",
    "top_region_share_change_1d",
    "cost_vs_rolling_mean_7",
    "cost_vs_rolling_mean_14",
]

DETECTOR_RESULT_COLUMNS = [
    "usage_date",
    "method",
    "is_flagged",
    "score",
    "threshold",
    "actual_cost",
    "expected_cost",
    "deviation",
    "relative_deviation",
    "severity_hint",
    "explanation",
]

DETECTOR_OPTIONAL_CONTEXT_COLUMNS = [
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
    "top_service",
    "top_region",
]
DETECTOR_RESULT_WITH_CONTEXT_COLUMNS = (
    DETECTOR_RESULT_COLUMNS + DETECTOR_OPTIONAL_CONTEXT_COLUMNS
)

STL_COMPONENT_COLUMNS = [
    "usage_date",
    "actual_cost",
    "trend",
    "seasonal",
    "residual",
    "expected_cost",
    "residual_score",
    "is_flagged",
]

ISOLATION_FOREST_FEATURE_COLUMNS = [
    "total_cost_usd",
    "cost_rolling_mean_14",
    "cost_rolling_std_14",
    "day_of_week",
    "is_weekend",
    "pct_change_1d",
    "pct_change_7d",
    "cost_diff_1d",
    "cost_diff_7d",
    "top_service_share",
    "top_service_share_change_1d",
    "top_region_share",
    "top_region_share_change_1d",
    "cost_vs_rolling_mean_7",
    "cost_vs_rolling_mean_14",
]

ALERT_COLUMNS = [
    "alert_id",
    "usage_date",
    "alert_level",
    "methods_triggered",
    "method_count",
    "actual_cost",
    "expected_cost",
    "relative_delta",
    "max_method_score",
    "max_relative_deviation",
    "method_severity_hints",
    "is_true_anomaly",
    "anomaly_type",
    "planned_event",
    "top_service",
    "top_region",
    "alert_reason",
]

ALERT_METHOD_SUMMARY_COLUMNS = [
    "usage_date",
    "methods_triggered",
    "method_count",
    "actual_cost",
    "expected_cost",
    "relative_delta",
    "max_method_score",
    "max_relative_deviation",
    "method_severity_hints",
    "detector_explanations",
    "is_true_anomaly",
    "anomaly_type",
    "planned_event",
    "planned_event_ids",
    "top_service",
    "top_region",
]

SUPPRESSED_ALERT_COLUMNS = [
    "suppression_id",
    "usage_date",
    "suppression_type",
    "methods_triggered",
    "method_count",
    "actual_cost",
    "expected_cost",
    "relative_delta",
    "planned_event_id",
    "suppression_reason",
]

CONTRIBUTOR_COLUMNS = [
    "alert_id",
    "usage_date",
    "alert_level",
    "service",
    "region",
    "cost_usd",
    "previous_7d_avg_cost",
    "delta_cost",
    "contribution_share",
    "contribution_basis",
    "rank",
    "contributor_reason",
]

CALIBRATION_SUMMARY_COLUMNS = [
    "method",
    "candidate_id",
    "parameters",
    "predicted_positive_days",
    "true_positives",
    "false_positives",
    "false_negatives",
    "precision",
    "recall",
    "f1",
    "event_recall",
    "selection_score",
    "selected",
]

EVALUATION_SUMMARY_COLUMNS = [
    "subject",
    "matching_mode",
    "total_days",
    "true_anomaly_days",
    "predicted_positive_days",
    "true_positives",
    "false_positives",
    "true_negatives",
    "false_negatives",
    "precision",
    "recall",
    "f1",
    "false_positives_per_30_days",
]

EVALUATION_BY_TYPE_COLUMNS = [
    "subject",
    "anomaly_type",
    "true_days",
    "detected_days_exact",
    "detected_days_tolerance_1_day",
    "recall_exact",
    "recall_tolerance_1_day",
]

EVENT_LEVEL_EVALUATION_COLUMNS = [
    "subject",
    "matching_mode",
    "true_events",
    "predicted_events",
    "detected_events",
    "false_positive_events",
    "missed_events",
    "event_precision",
    "event_recall",
    "event_f1",
]

DETECTION_DELAY_COLUMNS = [
    "subject",
    "anomaly_id",
    "anomaly_type",
    "start_date",
    "end_date",
    "detected",
    "first_detection_date",
    "detection_delay_days",
]

FALSE_POSITIVE_DAYS_COLUMNS = [
    "subject",
    "usage_date",
    "prediction_source",
    "planned_event",
    "anomaly_type",
    "alert_level",
    "methods_triggered",
    "actual_cost",
    "expected_cost",
    "relative_delta",
    "reason",
]

EVALUATION_DAILY_PREDICTION_COLUMNS = [
    "usage_date",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
    "planned_event_ids",
    "zscore_pred",
    "stl_pred",
    "isolation_forest_pred",
    "raw_alert_candidate_pred",
    "agreement_alert_pred",
]

REQUIRED_CATALOG_EVENT_TYPES = [
    "one_day_spike",
    "persistent_step_increase",
    "gradual_drift",
    "service_local_anomaly",
    "multi_day_burst",
]
