"""
Alert generation using detector agreement and cost deviation magnitude.

Phase 5 scope only:
- convert detector outputs into warning/critical alerts
- copy ground-truth labels for later inspection
- do not compute evaluation metrics or deliver notifications
"""

from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # Allows: python src/alerts.py
    import config  # type: ignore


METHOD_ORDER = ["zscore", "stl", "isolation_forest"]
ALLOWED_ALERT_LEVELS = {"warning", "critical"}


def load_method_results(path: Path = config.METHOD_RESULTS_PATH) -> pd.DataFrame:
    """Load stacked detector method results."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Method results file not found: {path}")

    df = pd.read_csv(path)
    validate_method_results(df)
    df = df.copy().sort_values(["usage_date", "method"]).reset_index(drop=True)
    df["usage_date"] = pd.to_datetime(df["usage_date"], errors="raise").dt.date.astype(
        str
    )
    return df


def _load_daily_features(path: Path = config.DAILY_FEATURES_PATH) -> pd.DataFrame:
    """Load daily features used as alert context."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Daily features file not found: {path}")

    df = pd.read_csv(path)
    required_columns = {
        "usage_date",
        "is_anomaly",
        "anomaly_types",
        "planned_event",
        "top_service",
        "top_region",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Daily features are missing columns: {missing_columns}")

    df = df.copy().sort_values("usage_date").reset_index(drop=True)
    df["usage_date"] = pd.to_datetime(df["usage_date"], errors="raise").dt.date.astype(
        str
    )
    return df


def validate_method_results(df: pd.DataFrame) -> None:
    """Validate method_results.csv before alert generation."""
    missing_columns = sorted(set(config.DETECTOR_RESULT_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"method_results is missing columns: {missing_columns}")

    expected_methods = set(METHOD_ORDER)
    if set(df["method"].unique()) != expected_methods:
        raise ValueError("method_results must contain zscore, stl, and isolation_forest.")
    if len(df) != config.NUM_DAYS * len(expected_methods):
        raise ValueError("method_results must contain 540 rows.")
    if df.duplicated(["usage_date", "method"]).any():
        raise ValueError("method_results contains duplicate usage_date + method rows.")
    if not set(df["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError("method_results is_flagged must contain only 0/1.")

    numeric_columns = [
        "score",
        "threshold",
        "actual_cost",
        "expected_cost",
        "deviation",
        "relative_deviation",
    ]
    numeric_values = df[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric_values.to_numpy()).all():
        raise ValueError("method_results contains non-finite numeric values.")
    if (numeric_values["actual_cost"] < 0).any():
        raise ValueError("method_results actual_cost contains negative values.")
    if (numeric_values["relative_deviation"] < 0).any():
        raise ValueError("method_results relative_deviation contains negative values.")


def _ordered_triggered_methods(triggered: pd.DataFrame) -> list[str]:
    """Return triggered method names in a stable display order."""
    triggered_methods = set(triggered["method"])
    return [method for method in METHOD_ORDER if method in triggered_methods]


def _choose_expected_cost(group: pd.DataFrame, actual_cost: float) -> float:
    """Choose alert-level expected cost, preferring STL trend + seasonality."""
    stl_rows = group[group["method"] == "stl"]
    if not stl_rows.empty:
        stl_expected = float(stl_rows["expected_cost"].iloc[0])
        if np.isfinite(stl_expected) and stl_expected > 0:
            return stl_expected

    finite_expected = pd.to_numeric(group["expected_cost"], errors="coerce")
    finite_expected = finite_expected[np.isfinite(finite_expected) & (finite_expected > 0)]
    if not finite_expected.empty:
        return float(finite_expected.median())

    return float(actual_cost)


def _alert_level(method_count: int, relative_delta: float) -> str | None:
    """Apply Phase 5 warning/critical alert rules."""
    if method_count == 0:
        return None
    if method_count == 3:
        return "critical"
    if method_count >= 2 and relative_delta >= config.CRITICAL_RELATIVE_DELTA:
        return "critical"
    if method_count == 2:
        return "warning"
    if method_count == 1 and relative_delta >= config.WARNING_RELATIVE_DELTA:
        return "warning"
    return None


def _build_alert_reason(row: pd.Series) -> str:
    """Build a human-readable alert reason."""
    relative_percent = row["relative_delta"] * 100
    method_count = int(row["method_count"])
    if row["alert_level"] == "critical" and method_count == 3:
        reason = "Critical alert: all 3 methods flagged the same day."
    elif row["alert_level"] == "critical":
        reason = (
            f"Critical alert: {method_count} methods agreed and relative cost "
            f"deviation is {relative_percent:.1f}%."
        )
    elif method_count == 1:
        reason = (
            "Warning alert: 1 method flagged the day and relative cost "
            f"deviation is {relative_percent:.1f}%."
        )
    else:
        reason = (
            f"Warning alert: {method_count} methods flagged the day and relative "
            f"cost deviation is {relative_percent:.1f}%."
        )

    if int(row["planned_event"]) == 1:
        reason = (
            f"{reason} This date is marked as a planned event; alert retained "
            "for false-positive analysis."
        )
    return reason


def build_alert_method_summary(
    method_results: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate detector method rows to one alert-decision summary row per day."""
    context = daily_features[
        [
            "usage_date",
            "is_anomaly",
            "anomaly_types",
            "planned_event",
            "top_service",
            "top_region",
        ]
    ].rename(
        columns={
            "is_anomaly": "is_true_anomaly",
            "anomaly_types": "anomaly_type",
        }
    )

    summary_rows: list[dict[str, object]] = []
    for usage_date, group in method_results.groupby("usage_date", sort=True):
        group = group.copy()
        triggered = group[group["is_flagged"] == 1]
        triggered_methods = _ordered_triggered_methods(triggered)
        method_count = len(triggered_methods)
        actual_cost = float(pd.to_numeric(group["actual_cost"], errors="raise").median())
        expected_cost = _choose_expected_cost(group, actual_cost)

        if expected_cost > 0 and np.isfinite(expected_cost):
            relative_delta = abs(actual_cost - expected_cost) / expected_cost
        else:
            expected_cost = actual_cost
            relative_delta = 0.0

        if method_count > 0:
            max_method_score = float(pd.to_numeric(triggered["score"]).abs().max())
            severity_hints = [
                f"{row.method}:{row.severity_hint}"
                for row in triggered.sort_values("method").itertuples(index=False)
            ]
            explanations = [
                f"{row.method}: {row.explanation}"
                for row in triggered.sort_values("method").itertuples(index=False)
            ]
        else:
            max_method_score = 0.0
            severity_hints = ["none"]
            explanations = ["No detector flagged this date."]

        max_relative_deviation = float(
            pd.to_numeric(group["relative_deviation"], errors="raise").max()
        )
        summary_rows.append(
            {
                "usage_date": usage_date,
                "methods_triggered": ",".join(triggered_methods),
                "method_count": method_count,
                "actual_cost": round(actual_cost, 4),
                "expected_cost": round(expected_cost, 4),
                "relative_delta": round(float(relative_delta), 6),
                "max_method_score": round(max_method_score, 6),
                "max_relative_deviation": round(max_relative_deviation, 6),
                "method_severity_hints": ",".join(severity_hints),
                "detector_explanations": " | ".join(explanations),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary = summary.merge(context, on="usage_date", how="left")
    summary["is_true_anomaly"] = summary["is_true_anomaly"].astype(int)
    summary["planned_event"] = summary["planned_event"].astype(int)
    return summary[config.ALERT_METHOD_SUMMARY_COLUMNS]


def generate_alerts(
    method_results: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    """Generate warning and critical alerts from detector method results."""
    summary = build_alert_method_summary(method_results, daily_features)
    alert_rows: list[dict[str, object]] = []

    for row in summary.itertuples(index=False):
        alert_level = _alert_level(int(row.method_count), float(row.relative_delta))
        if alert_level is None:
            continue
        alert_row = {
            "alert_id": "",
            "usage_date": row.usage_date,
            "alert_level": alert_level,
            "methods_triggered": row.methods_triggered,
            "method_count": int(row.method_count),
            "actual_cost": float(row.actual_cost),
            "expected_cost": float(row.expected_cost),
            "relative_delta": float(row.relative_delta),
            "max_method_score": float(row.max_method_score),
            "max_relative_deviation": float(row.max_relative_deviation),
            "method_severity_hints": row.method_severity_hints,
            "is_true_anomaly": int(row.is_true_anomaly),
            "anomaly_type": row.anomaly_type,
            "planned_event": int(row.planned_event),
            "top_service": row.top_service,
            "top_region": row.top_region,
        }
        alert_row["alert_reason"] = _build_alert_reason(pd.Series(alert_row))
        alert_rows.append(alert_row)

    alerts = pd.DataFrame(alert_rows, columns=config.ALERT_COLUMNS)
    if not alerts.empty:
        alerts = alerts.sort_values("usage_date").reset_index(drop=True)
        alerts["alert_id"] = [
            f"ALERT-{index + 1:04d}" for index in range(len(alerts))
        ]
    validate_alerts(alerts)
    return alerts[config.ALERT_COLUMNS]


def validate_alerts(alerts: pd.DataFrame) -> None:
    """Validate generated warning/critical alerts."""
    if list(alerts.columns) != config.ALERT_COLUMNS:
        raise ValueError("alerts columns do not match the required schema.")
    if alerts.empty:
        raise ValueError("At least one alert is required.")
    if alerts["alert_id"].duplicated().any():
        raise ValueError("alert_id must be unique.")
    if alerts["usage_date"].duplicated().any():
        raise ValueError("usage_date must be unique in alerts.csv.")
    if not set(alerts["alert_level"].unique()).issubset(ALLOWED_ALERT_LEVELS):
        raise ValueError("alert_level must contain only warning/critical.")
    if not alerts["method_count"].between(1, 3).all():
        raise ValueError("method_count must be between 1 and 3.")
    if alerts["methods_triggered"].astype(str).str.strip().eq("").any():
        raise ValueError("methods_triggered must be non-empty.")

    numeric_columns = [
        "actual_cost",
        "expected_cost",
        "relative_delta",
        "max_method_score",
        "max_relative_deviation",
    ]
    numeric_values = alerts[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric_values.to_numpy()).all():
        raise ValueError("alerts contains non-finite numeric values.")
    if (numeric_values["actual_cost"] < 0).any():
        raise ValueError("actual_cost must be non-negative.")
    if (numeric_values["expected_cost"] < 0).any():
        raise ValueError("expected_cost must be non-negative.")
    if (numeric_values["relative_delta"] < 0).any():
        raise ValueError("relative_delta must be non-negative.")
    if (numeric_values["max_relative_deviation"] < 0).any():
        raise ValueError("max_relative_deviation must be non-negative.")
    if not set(alerts["planned_event"].unique()).issubset({0, 1}):
        raise ValueError("planned_event must contain only 0/1.")
    if not set(alerts["is_true_anomaly"].unique()).issubset({0, 1}):
        raise ValueError("is_true_anomaly must contain only 0/1.")
    if alerts["alert_reason"].astype(str).str.strip().eq("").any():
        raise ValueError("alert_reason must be non-empty.")


def save_alerts(alerts: pd.DataFrame, path: Path = config.ALERTS_PATH) -> Path:
    """Save generated alerts to CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    alerts.to_csv(path, index=False)
    return path


def run_alert_generation() -> Path:
    """Run Phase 5 alert generation and write alerts.csv."""
    method_results = load_method_results(config.METHOD_RESULTS_PATH)
    daily_features = _load_daily_features(config.DAILY_FEATURES_PATH)
    summary = build_alert_method_summary(method_results, daily_features)
    alerts = generate_alerts(method_results, daily_features)

    config.OUTPUTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(config.ALERT_METHOD_SUMMARY_PATH, index=False)
    return save_alerts(alerts, config.ALERTS_PATH)


def main() -> None:
    """CLI entry point for Phase 5 alert generation."""
    path = run_alert_generation()
    print("Alert generation complete.")
    print(f"- {path}")
    print(f"- {config.ALERT_METHOD_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
