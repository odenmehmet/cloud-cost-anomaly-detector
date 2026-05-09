"""
Pipeline entry point for implemented phases only.

Implemented:
- Phase 2: synthetic CUR-like data generation
- Phase 3: preprocessing and feature engineering
- Phase 4: detection methods
- Phase 5: alert layer and contributor analysis
- Phase 6: evaluation metrics

Not implemented here: real cloud integrations, notification delivery, or
Streamlit dashboard logic.
"""

from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import pandas as pd
import numpy as np

from src import config
from src.alerts import run_alert_generation
from src.contributors import run_contributor_analysis
from src.data_generator import generate_synthetic_dataset
from src.detectors.isolation_forest import run_isolation_forest_detector
from src.detectors.stl import run_stl_detector
from src.detectors.zscore import run_zscore_detector
from src.evaluation import run_evaluation
from src.features import run_feature_engineering
from src.preprocessing import run_preprocessing


def _validate_method_output(df: pd.DataFrame, method: str) -> None:
    """Validate one method-specific detector result output."""
    missing_columns = sorted(set(config.DETECTOR_RESULT_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"{method} output is missing columns: {missing_columns}")
    if len(df) != config.NUM_DAYS:
        raise ValueError(f"{method} output must contain {config.NUM_DAYS} rows.")
    if not df["usage_date"].is_monotonic_increasing:
        raise ValueError(f"{method} output must be sorted by usage_date.")
    if set(df["method"].unique()) != {method}:
        raise ValueError(f"{method} output has unexpected method values.")
    if not set(df["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError(f"{method} is_flagged must contain only 0/1.")
    numeric_columns = [
        "score",
        "threshold",
        "actual_cost",
        "relative_deviation",
    ]
    numeric_values = df[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric_values.to_numpy()).all():
        raise ValueError(f"{method} output contains non-finite values.")
    if (df["actual_cost"] < 0).any():
        raise ValueError(f"{method} actual_cost contains negative values.")
    if (df["relative_deviation"] < 0).any():
        raise ValueError(f"{method} relative_deviation contains negative values.")
    allowed_severities = {"none", "low", "medium", "high"}
    if not set(df["severity_hint"].unique()).issubset(allowed_severities):
        raise ValueError(f"{method} severity_hint contains invalid values.")
    if df["explanation"].astype(str).str.strip().eq("").any():
        raise ValueError(f"{method} explanation contains blank values.")

    flagged_count = int(df["is_flagged"].sum())
    if flagged_count <= 0:
        raise ValueError(f"{method} should flag at least one day.")
    if flagged_count >= config.NUM_DAYS * 0.5:
        raise ValueError(f"{method} flagged too many days for this phase.")


def _validate_unified_method_results(method_results: pd.DataFrame) -> None:
    """Validate the stacked detector output table."""
    missing_columns = sorted(
        set(config.DETECTOR_RESULT_COLUMNS) - set(method_results.columns)
    )
    if missing_columns:
        raise ValueError(f"method_results is missing columns: {missing_columns}")
    expected_methods = {"zscore", "stl", "isolation_forest"}
    if len(method_results) != config.NUM_DAYS * len(expected_methods):
        raise ValueError("method_results row count is incorrect.")
    if set(method_results["method"].unique()) != expected_methods:
        raise ValueError("method_results must contain exactly three methods.")
    counts = method_results.groupby("method").size().to_dict()
    if any(count != config.NUM_DAYS for count in counts.values()):
        raise ValueError("Each detector must contribute 180 rows.")
    if method_results.duplicated(["usage_date", "method"]).any():
        raise ValueError("method_results contains duplicate usage_date + method rows.")
    if not set(method_results["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError("method_results is_flagged must contain only 0/1.")
    scores = pd.to_numeric(method_results["score"], errors="raise")
    if not np.isfinite(scores.to_numpy()).all():
        raise ValueError("method_results score contains non-finite values.")


def _write_method_results(method_paths: list[Path]) -> pd.DataFrame:
    """Stack method-specific detector outputs into method_results.csv."""
    method_frames = [pd.read_csv(path) for path in method_paths]
    method_results = pd.concat(method_frames, ignore_index=True)
    method_results = method_results.sort_values(["usage_date", "method"]).reset_index(
        drop=True
    )

    for method in ["zscore", "stl", "isolation_forest"]:
        _validate_method_output(
            method_results[method_results["method"] == method].reset_index(drop=True),
            method,
        )
    _validate_unified_method_results(method_results)

    config.OUTPUTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    method_results.to_csv(config.METHOD_RESULTS_PATH, index=False)
    return method_results


def _print_pipeline_summary(
    raw_rows: int,
    daily_features: pd.DataFrame,
    method_results: pd.DataFrame,
    alerts: pd.DataFrame,
    contributors: pd.DataFrame,
    evaluation_result: dict,
    output_paths: list[Path],
) -> None:
    """Print the required Phase 2 through Phase 6 pipeline summary."""
    print("Pipeline complete: Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 only.")
    print("No dashboard ran.")
    print(f"Raw rows: {raw_rows}")
    print(f"Daily feature rows: {len(daily_features)}")
    for method in ["zscore", "stl", "isolation_forest"]:
        flagged_days = int(
            method_results.loc[method_results["method"] == method, "is_flagged"].sum()
        )
        print(f"{method} flagged days: {flagged_days}")
    print(f"Total method result rows: {len(method_results)}")
    print(f"Total alerts: {len(alerts)}")
    print(f"Warning alerts: {int((alerts['alert_level'] == 'warning').sum())}")
    print(f"Critical alerts: {int((alerts['alert_level'] == 'critical').sum())}")
    print(f"Contributor rows: {len(contributors)}")
    print(f"Evaluation summary rows: {len(evaluation_result['evaluation_summary'])}")
    print(f"Evaluation by type rows: {len(evaluation_result['evaluation_by_type'])}")
    print(f"Detection delay rows: {len(evaluation_result['detection_delay'])}")
    print(f"False positive day rows: {len(evaluation_result['false_positive_days'])}")
    print(
        f"Date range: {daily_features['usage_date'].min()} "
        f"to {daily_features['usage_date'].max()}"
    )
    print("Generated output paths:")
    for path in output_paths:
        print(f"- {path}")


def main() -> None:
    """Run implemented phases in order through Phase 6."""
    generation_result = generate_synthetic_dataset(verbose=False)
    preprocessing_result = run_preprocessing()
    feature_path = run_feature_engineering()
    daily_features = pd.read_csv(feature_path)

    zscore_path = run_zscore_detector()
    stl_path = run_stl_detector()
    isolation_path = run_isolation_forest_detector()
    method_results = _write_method_results([zscore_path, stl_path, isolation_path])
    alerts_path = run_alert_generation()
    contributors_path = run_contributor_analysis()
    alerts = pd.read_csv(alerts_path)
    contributors = pd.read_csv(contributors_path)
    evaluation_result = run_evaluation()

    output_paths = [
        generation_result["paths"]["synthetic_cur_like_daily"],
        generation_result["paths"]["anomaly_catalog"],
        config.DAILY_TOTAL_COST_PATH,
        config.DAILY_SERVICE_COST_PATH,
        config.DAILY_REGION_COST_PATH,
        config.DAILY_SERVICE_REGION_COST_PATH,
        config.DAILY_FEATURES_PATH,
        config.ZSCORE_RESULTS_PATH,
        config.STL_RESULTS_PATH,
        config.ISOLATION_FOREST_RESULTS_PATH,
        config.STL_COMPONENTS_PATH,
        config.METHOD_RESULTS_PATH,
        config.ALERT_METHOD_SUMMARY_PATH,
        config.ALERTS_PATH,
        config.CONTRIBUTORS_PATH,
        config.EVALUATION_SUMMARY_PATH,
        config.EVALUATION_BY_TYPE_PATH,
        config.DETECTION_DELAY_PATH,
        config.FALSE_POSITIVE_DAYS_PATH,
        config.EVALUATION_DAILY_PREDICTIONS_PATH,
    ]

    _print_pipeline_summary(
        raw_rows=len(preprocessing_result["raw"]),
        daily_features=daily_features,
        method_results=method_results,
        alerts=alerts,
        contributors=contributors,
        evaluation_result=evaluation_result,
        output_paths=output_paths,
    )


if __name__ == "__main__":
    main()
