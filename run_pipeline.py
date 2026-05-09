"""
Pipeline entry point for implemented phases only.

Implemented:
- Phase 2: synthetic CUR-like data generation
- Phase 3: preprocessing and feature engineering

Not implemented here: detectors, alerts, contributor analysis, evaluation,
real cloud integrations, or Streamlit dashboard logic.
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

from src import config
from src.data_generator import generate_synthetic_dataset
from src.features import run_feature_engineering
from src.preprocessing import run_preprocessing


def _print_top_cost_days(daily_total: pd.DataFrame) -> None:
    """Print the five highest-cost days from the daily total output."""
    top_days = daily_total.nlargest(5, "total_cost_usd")[
        ["usage_date", "total_cost_usd", "is_anomaly", "anomaly_types", "planned_event"]
    ]
    print("Top 5 highest cost days:")
    for row in top_days.itertuples(index=False):
        print(
            f"- {row.usage_date}: ${row.total_cost_usd:.4f} "
            f"(is_anomaly={row.is_anomaly}, "
            f"anomaly_types={row.anomaly_types}, "
            f"planned_event={row.planned_event})"
        )


def _print_pipeline_summary(
    raw_rows: int,
    daily_total: pd.DataFrame,
    daily_service: pd.DataFrame,
    daily_region: pd.DataFrame,
    daily_service_region: pd.DataFrame,
    daily_features: pd.DataFrame,
    output_paths: list[Path],
) -> None:
    """Print the required Phase 2 + Phase 3 pipeline summary."""
    print("Pipeline complete: Phase 2 + Phase 3 only.")
    print("No detectors, alerts, evaluation, contributor analysis, or dashboard ran.")
    print(f"Raw rows: {raw_rows}")
    print(f"Daily total rows: {len(daily_total)}")
    print(f"Daily service rows: {len(daily_service)}")
    print(f"Daily region rows: {len(daily_region)}")
    print(f"Daily service-region rows: {len(daily_service_region)}")
    print(f"Daily feature rows: {len(daily_features)}")
    print(
        f"Date range: {daily_total['usage_date'].min()} "
        f"to {daily_total['usage_date'].max()}"
    )
    print(f"Anomaly days: {int(daily_total['is_anomaly'].sum())}")
    print(f"Planned event days: {int(daily_total['planned_event'].sum())}")
    _print_top_cost_days(daily_total)
    print("Generated output paths:")
    for path in output_paths:
        print(f"- {path}")


def main() -> None:
    """Run implemented phases in order: generation, preprocessing, features."""
    generation_result = generate_synthetic_dataset(verbose=False)
    preprocessing_result = run_preprocessing()
    feature_path = run_feature_engineering()
    daily_features = pd.read_csv(feature_path)

    output_paths = [
        generation_result["paths"]["synthetic_cur_like_daily"],
        generation_result["paths"]["anomaly_catalog"],
        config.DAILY_TOTAL_COST_PATH,
        config.DAILY_SERVICE_COST_PATH,
        config.DAILY_REGION_COST_PATH,
        config.DAILY_SERVICE_REGION_COST_PATH,
        config.DAILY_FEATURES_PATH,
    ]

    _print_pipeline_summary(
        raw_rows=len(preprocessing_result["raw"]),
        daily_total=preprocessing_result["daily_total"],
        daily_service=preprocessing_result["daily_service"],
        daily_region=preprocessing_result["daily_region"],
        daily_service_region=preprocessing_result["daily_service_region"],
        daily_features=daily_features,
        output_paths=output_paths,
    )


if __name__ == "__main__":
    main()
