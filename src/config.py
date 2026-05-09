"""
Configuration and constants for synthetic data generation and processing.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DATA_DIR = DATA_DIR / "outputs"

SYNTHETIC_CUR_LIKE_PATH = RAW_DATA_DIR / "synthetic_cur_like_daily.csv"
ANOMALY_CATALOG_PATH = RAW_DATA_DIR / "anomaly_catalog.csv"
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
CONTRIBUTORS_PATH = OUTPUTS_DATA_DIR / "contributors.csv"
ALERT_METHOD_SUMMARY_PATH = OUTPUTS_DATA_DIR / "alert_method_summary.csv"

DEFAULT_RANDOM_SEED = 42
START_DATE = "2025-10-01"
NUM_DAYS = 180
ZSCORE_ROLLING_WINDOW = 14
ZSCORE_MIN_PERIODS = 7
ZSCORE_THRESHOLD = 3.0
STL_PERIOD = 7
STL_RESIDUAL_THRESHOLD = 3.0
ISOLATION_FOREST_N_ESTIMATORS = 100
ISOLATION_FOREST_CONTAMINATION = 0.05
WARNING_RELATIVE_DELTA = 0.05
CRITICAL_RELATIVE_DELTA = 0.08
TOP_CONTRIBUTOR_LIMIT = 5

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

ENVIRONMENT_USAGE_MULTIPLIERS = {
    "prod": 1.00,
    "staging": 0.38,
    "dev": 0.24,
}

TEAM_USAGE_MULTIPLIERS = {
    "platform": 1.05,
    "data": 1.12,
    "web": 0.95,
    "ml": 1.18,
}

WEEKLY_SEASONALITY_MULTIPLIERS = {
    0: 1.07,  # Monday
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

ANOMALY_EVENTS = [
    {
        "anomaly_id": "ANOM-001",
        "anomaly_type": "one_day_spike",
        "start_day": 50,
        "duration_days": 1,
        "affected_service": "AmazonEC2",
        "affected_region": "us-east-1",
        "magnitude": 3.65,
        "planned_event": 0,
        "description": "Single-day EC2 usage spike in us-east-1.",
    },
    {
        "anomaly_id": "ANOM-002",
        "anomaly_type": "persistent_step_increase",
        "start_day": 75,
        "duration_days": 12,
        "affected_service": "AmazonRDS",
        "affected_region": "eu-west-1",
        "magnitude": 1.58,
        "planned_event": 0,
        "description": "Persistent RDS cost step increase in eu-west-1.",
    },
    {
        "anomaly_id": "ANOM-003",
        "anomaly_type": "gradual_drift",
        "start_day": 110,
        "duration_days": 16,
        "affected_service": "AmazonEKS",
        "affected_region": "eu-central-1",
        "start_magnitude": 1.05,
        "magnitude": 1.55,
        "planned_event": 0,
        "description": "Gradual EKS cost drift in eu-central-1.",
    },
    {
        "anomaly_id": "ANOM-004",
        "anomaly_type": "service_local_anomaly",
        "start_day": 145,
        "duration_days": 4,
        "affected_service": "AmazonDynamoDB",
        "affected_region": "ap-southeast-1",
        "magnitude": 2.45,
        "planned_event": 0,
        "description": "Localized DynamoDB cost anomaly in ap-southeast-1.",
    },
    {
        "anomaly_id": "PLAN-001",
        "anomaly_type": "legitimate_usage_increase",
        "start_day": 62,
        "duration_days": 8,
        "affected_service": "AmazonCloudFront",
        "affected_region": "us-east-1",
        "magnitude": 1.42,
        "planned_event": 1,
        "description": "Planned CloudFront traffic increase for a business event.",
    },
]

CUR_LIKE_COLUMNS = [
    "usage_date",
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
    "source_record_count",
    "is_anomaly",
    "anomaly_type",
    "anomaly_id",
    "planned_event",
]

ANOMALY_CATALOG_COLUMNS = [
    "anomaly_id",
    "anomaly_type",
    "start_date",
    "end_date",
    "affected_service",
    "affected_region",
    "magnitude",
    "planned_event",
    "description",
]

DAILY_TOTAL_COST_COLUMNS = [
    "usage_date",
    "total_cost_usd",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
]

PROCESSED_DAILY_TOTAL_COST_COLUMNS = [
    "usage_date",
    "total_cost_usd",
    "total_usage_amount",
    "service_count",
    "region_count",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
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
]

DAILY_FEATURE_COLUMNS = [
    "usage_date",
    "total_cost_usd",
    "total_usage_amount",
    "service_count",
    "region_count",
    "row_count",
    "is_anomaly",
    "anomaly_types",
    "planned_event",
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
    "top_region",
    "top_region_cost_usd",
    "top_region_share",
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
    "total_usage_amount",
    "day_of_week",
    "is_weekend",
    "pct_change_1d",
    "pct_change_7d",
    "cost_diff_1d",
    "cost_diff_7d",
    "top_service_share",
    "top_region_share",
    "service_count",
    "region_count",
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
    "top_service",
    "top_region",
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
    "rank",
    "contributor_reason",
]

REQUIRED_CATALOG_EVENT_TYPES = [
    "one_day_spike",
    "persistent_step_increase",
    "gradual_drift",
    "service_local_anomaly",
    "legitimate_usage_increase",
]
