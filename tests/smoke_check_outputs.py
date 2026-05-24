"""Smoke-check generated pipeline outputs for the course demo.

Run after `python run_pipeline.py`:

    python tests/smoke_check_outputs.py
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


ROOT_DIR = Path(__file__).resolve().parents[1]


FILES = {
    "raw": ROOT_DIR / "data" / "raw" / "synthetic_cur_like_daily.csv",
    "anomaly_catalog": ROOT_DIR / "data" / "raw" / "anomaly_catalog.csv",
    "daily_total": ROOT_DIR / "data" / "processed" / "daily_total_cost.csv",
    "daily_service": ROOT_DIR / "data" / "processed" / "daily_service_cost.csv",
    "daily_region": ROOT_DIR / "data" / "processed" / "daily_region_cost.csv",
    "daily_service_region": ROOT_DIR
    / "data"
    / "processed"
    / "daily_service_region_cost.csv",
    "daily_features": ROOT_DIR / "data" / "processed" / "daily_features.csv",
    "method_results": ROOT_DIR / "data" / "outputs" / "method_results.csv",
    "alerts": ROOT_DIR / "data" / "outputs" / "alerts.csv",
    "contributors": ROOT_DIR / "data" / "outputs" / "contributors.csv",
    "evaluation_summary": ROOT_DIR / "reports" / "evaluation_summary.csv",
    "evaluation_by_type": ROOT_DIR / "reports" / "evaluation_by_type.csv",
    "detection_delay": ROOT_DIR / "reports" / "detection_delay.csv",
    "false_positive_days": ROOT_DIR / "reports" / "false_positive_days.csv",
}


EXPECTED_SUBJECTS = {
    "zscore",
    "stl",
    "isolation_forest",
    "agreement_alert",
}
EXPECTED_MATCHING_MODES = {"exact_day", "tolerance_1_day"}


def read_csv(name: str) -> pd.DataFrame:
    """Read a required generated CSV file."""
    path = FILES[name]
    assert path.exists(), f"Missing required output file: {path}"
    return pd.read_csv(path)


def assert_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    """Assert that a DataFrame includes required columns."""
    missing = sorted(set(columns) - set(df.columns))
    assert not missing, f"{name} missing required columns: {missing}"


def assert_finite(df: pd.DataFrame, columns: list[str], name: str) -> None:
    """Assert numeric columns contain no NaN or infinite values."""
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce")
        assert values.notna().all(), f"{name}.{column} contains NaN values"
        assert np.isfinite(values).all(), f"{name}.{column} contains infinite values"


def main() -> None:
    """Run lightweight output-contract checks."""
    for path in FILES.values():
        assert path.exists(), f"Missing required output file: {path}"

    daily_features = read_csv("daily_features")
    method_results = read_csv("method_results")
    alerts = read_csv("alerts")
    contributors = read_csv("contributors")
    evaluation_summary = read_csv("evaluation_summary")

    assert_columns(
        daily_features,
        [
            "usage_date",
            "total_cost_usd",
            "is_anomaly",
            "anomaly_types",
            "planned_event",
            "top_service",
            "top_region",
        ],
        "daily_features",
    )
    assert len(daily_features) == 180, "daily_features.csv must have 180 rows"
    assert daily_features["usage_date"].is_unique, "daily_features has duplicate dates"
    assert_finite(
        daily_features,
        ["total_cost_usd", "total_usage_amount", "top_service_share", "top_region_share"],
        "daily_features",
    )

    assert_columns(
        method_results,
        [
            "usage_date",
            "method",
            "is_flagged",
            "score",
            "actual_cost",
            "expected_cost",
            "relative_deviation",
        ],
        "method_results",
    )
    assert len(method_results) == 540, "method_results.csv must have 540 rows"
    assert set(method_results["method"]) == {
        "zscore",
        "stl",
        "isolation_forest",
    }, "method_results has unexpected method names"
    method_counts = method_results.groupby("method").size()
    assert (method_counts == 180).all(), "Each detector must have 180 rows"
    assert set(method_results["is_flagged"]).issubset({0, 1}), "Invalid flags"
    assert_finite(
        method_results,
        ["score", "actual_cost", "expected_cost", "relative_deviation"],
        "method_results",
    )

    assert_columns(
        alerts,
        [
            "alert_id",
            "usage_date",
            "alert_level",
            "method_count",
            "actual_cost",
            "expected_cost",
            "relative_delta",
        ],
        "alerts",
    )
    assert len(alerts) >= 1, "alerts.csv must contain at least one alert"
    assert alerts["alert_id"].is_unique, "alert_id values must be unique"
    assert set(alerts["alert_level"]).issubset(
        {"warning", "critical"}
    ), "alert_level must be warning or critical"
    assert_finite(alerts, ["actual_cost", "expected_cost", "relative_delta"], "alerts")

    assert_columns(
        contributors,
        ["alert_id", "rank", "cost_usd", "previous_7d_avg_cost", "contribution_share"],
        "contributors",
    )
    assert set(alerts["alert_id"]).issubset(
        set(contributors["alert_id"])
    ), "contributors.csv must cover every alert_id"
    assert contributors.groupby("alert_id").size().le(5).all(), "At most 5 contributors per alert"
    assert (contributors.groupby("alert_id")["rank"].min() == 1).all(), "Each alert needs rank 1"
    assert contributors["contribution_share"].between(0, 1).all(), "Contribution shares out of range"
    assert_finite(
        contributors,
        ["cost_usd", "previous_7d_avg_cost", "contribution_share"],
        "contributors",
    )

    assert_columns(
        evaluation_summary,
        [
            "subject",
            "matching_mode",
            "total_days",
            "precision",
            "recall",
            "f1",
            "false_positives_per_30_days",
        ],
        "evaluation_summary",
    )
    assert len(evaluation_summary) == 8, "evaluation_summary.csv must have 8 rows"
    assert EXPECTED_SUBJECTS.issubset(
        set(evaluation_summary["subject"])
    ), "Missing evaluation subjects"
    assert EXPECTED_MATCHING_MODES.issubset(
        set(evaluation_summary["matching_mode"])
    ), "Missing matching modes"
    assert (evaluation_summary["total_days"] == 180).all(), "Expected 180 total days"
    assert_finite(
        evaluation_summary,
        ["precision", "recall", "f1", "false_positives_per_30_days"],
        "evaluation_summary",
    )
    for metric in ["precision", "recall", "f1"]:
        assert evaluation_summary[metric].between(0, 1).all(), f"{metric} out of range"

    print("Smoke check passed: generated output contracts are valid.")


if __name__ == "__main__":
    main()
