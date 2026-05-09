"""
Feature engineering for detector-ready daily cost data.

Phase 3 scope only:
- calendar features
- trailing rolling statistics
- lagged change features
- top daily service and region contributors
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
except ImportError:  # Allows: python src/features.py
    import config  # type: ignore


def add_calendar_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Add day-of-week and weekend indicators to daily totals."""
    df = daily_df.copy().sort_values("usage_date").reset_index(drop=True)
    usage_dates = pd.to_datetime(df["usage_date"], errors="raise")
    df["day_of_week"] = usage_dates.dt.dayofweek.astype(int)
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    return df


def add_rolling_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Add trailing rolling cost and usage features using past/current data."""
    df = daily_df.copy().sort_values("usage_date").reset_index(drop=True)

    for window in [7, 14, 30]:
        cost_window = df["total_cost_usd"].rolling(window=window, min_periods=1)
        df[f"cost_rolling_mean_{window}"] = cost_window.mean().round(4)
        df[f"cost_rolling_std_{window}"] = cost_window.std().fillna(0.0).round(4)

    usage_window = df["total_usage_amount"].rolling(window=7, min_periods=1)
    df["usage_rolling_mean_7"] = usage_window.mean().round(4)
    df["usage_rolling_std_7"] = usage_window.std().fillna(0.0).round(4)
    return df


def add_change_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Add one-day and seven-day cost change features."""
    df = daily_df.copy().sort_values("usage_date").reset_index(drop=True)
    total_cost = df["total_cost_usd"]

    df["pct_change_1d"] = total_cost.pct_change(periods=1, fill_method=None)
    df["pct_change_7d"] = total_cost.pct_change(periods=7, fill_method=None)
    df["cost_diff_1d"] = total_cost.diff(periods=1)
    df["cost_diff_7d"] = total_cost.diff(periods=7)

    change_columns = [
        "pct_change_1d",
        "pct_change_7d",
        "cost_diff_1d",
        "cost_diff_7d",
    ]
    df[change_columns] = (
        df[change_columns].replace([np.inf, -np.inf], 0.0).fillna(0.0)
    )
    df["pct_change_1d"] = df["pct_change_1d"].round(6)
    df["pct_change_7d"] = df["pct_change_7d"].round(6)
    df["cost_diff_1d"] = df["cost_diff_1d"].round(4)
    df["cost_diff_7d"] = df["cost_diff_7d"].round(4)
    return df


def add_top_contributor_features(
    daily_df: pd.DataFrame,
    service_df: pd.DataFrame,
    region_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add top service and top region cost contributor features for each day."""
    df = daily_df.copy().sort_values("usage_date").reset_index(drop=True)

    top_service = (
        service_df.sort_values(
            ["usage_date", "service_cost_usd", "service"],
            ascending=[True, False, True],
        )
        .groupby("usage_date", as_index=False)
        .head(1)[["usage_date", "service", "service_cost_usd"]]
        .rename(
            columns={
                "service": "top_service",
                "service_cost_usd": "top_service_cost_usd",
            }
        )
    )

    top_region = (
        region_df.sort_values(
            ["usage_date", "region_cost_usd", "region"],
            ascending=[True, False, True],
        )
        .groupby("usage_date", as_index=False)
        .head(1)[["usage_date", "region", "region_cost_usd"]]
        .rename(
            columns={
                "region": "top_region",
                "region_cost_usd": "top_region_cost_usd",
            }
        )
    )

    df = df.merge(top_service, on="usage_date", how="left")
    df = df.merge(top_region, on="usage_date", how="left")

    positive_cost = df["total_cost_usd"] > 0
    df["top_service_share"] = np.where(
        positive_cost,
        df["top_service_cost_usd"] / df["total_cost_usd"],
        0.0,
    )
    df["top_region_share"] = np.where(
        positive_cost,
        df["top_region_cost_usd"] / df["total_cost_usd"],
        0.0,
    )

    contributor_cost_columns = ["top_service_cost_usd", "top_region_cost_usd"]
    df[contributor_cost_columns] = df[contributor_cost_columns].fillna(0.0).round(4)
    df["top_service_share"] = df["top_service_share"].clip(0, 1).round(6)
    df["top_region_share"] = df["top_region_share"].clip(0, 1).round(6)
    df["top_service"] = df["top_service"].fillna("none")
    df["top_region"] = df["top_region"].fillna("none")
    return df


def build_daily_features(
    daily_total_df: pd.DataFrame,
    service_df: pd.DataFrame,
    region_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build the full detector-ready daily feature dataset."""
    required_daily_columns = set(config.PROCESSED_DAILY_TOTAL_COST_COLUMNS)
    missing_daily_columns = required_daily_columns - set(daily_total_df.columns)
    if missing_daily_columns:
        raise ValueError(
            f"daily_total_df is missing columns: {sorted(missing_daily_columns)}"
        )

    df = daily_total_df.copy().sort_values("usage_date").reset_index(drop=True)
    df["usage_date"] = pd.to_datetime(df["usage_date"], errors="raise").dt.date.astype(
        str
    )

    df = add_calendar_features(df)
    df = add_rolling_features(df)
    df = add_change_features(df)
    df = add_top_contributor_features(df, service_df, region_df)
    df = df[config.DAILY_FEATURE_COLUMNS]
    validate_daily_features(df)
    return df


def validate_daily_features(df: pd.DataFrame) -> None:
    """Validate the final Phase 3 daily feature output."""
    missing_columns = sorted(set(config.DAILY_FEATURE_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"daily_features is missing columns: {missing_columns}")
    if len(df) != config.NUM_DAYS:
        raise ValueError(f"daily_features must contain {config.NUM_DAYS} rows.")
    if df["usage_date"].duplicated().any():
        raise ValueError("daily_features contains duplicate usage_date values.")
    if not df["usage_date"].is_monotonic_increasing:
        raise ValueError("daily_features must be sorted by usage_date.")
    if not df["day_of_week"].between(0, 6).all():
        raise ValueError("day_of_week must be between 0 and 6.")
    if not set(df["is_weekend"].unique()).issubset({0, 1}):
        raise ValueError("is_weekend must contain only 0/1.")
    if not df["top_service_share"].between(0, 1).all():
        raise ValueError("top_service_share must be between 0 and 1.")
    if not df["top_region_share"].between(0, 1).all():
        raise ValueError("top_region_share must be between 0 and 1.")

    numeric_df = df.select_dtypes(include=[np.number])
    if not np.isfinite(numeric_df.to_numpy()).all():
        raise ValueError("daily_features contains infinite or NaN numeric values.")

    required_finite_columns = [
        "pct_change_1d",
        "pct_change_7d",
        "cost_rolling_std_7",
        "cost_rolling_std_14",
        "cost_rolling_std_30",
        "usage_rolling_std_7",
    ]
    if not np.isfinite(df[required_finite_columns].to_numpy()).all():
        raise ValueError("Change and rolling std features must be finite.")


def run_feature_engineering() -> Path:
    """Run Phase 3 feature engineering and write daily_features.csv."""
    daily_total = pd.read_csv(config.DAILY_TOTAL_COST_PATH)
    service = pd.read_csv(config.DAILY_SERVICE_COST_PATH)
    region = pd.read_csv(config.DAILY_REGION_COST_PATH)

    features = build_daily_features(daily_total, service, region)
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(config.DAILY_FEATURES_PATH, index=False)
    return config.DAILY_FEATURES_PATH


def main() -> None:
    """CLI entry point for Phase 3 feature engineering."""
    path = run_feature_engineering()
    print("Feature engineering complete.")
    print(f"- {path}")


if __name__ == "__main__":
    main()
