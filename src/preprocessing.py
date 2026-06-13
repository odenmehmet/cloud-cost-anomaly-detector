"""
Preprocessing for synthetic CUR-like billing data.

Phase 3 scope:
- validate raw synthetic billing rows
- aggregate daily cost views
- save detector-ready base tables
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import pandas as pd

try:
    from . import config
except ImportError:  # Allows: python src/preprocessing.py
    import config  # type: ignore


def _join_anomaly_types(types: pd.Series) -> str:
    """Join unique anomaly types, excluding the normal 'none' label."""
    anomaly_types = sorted(
        {
            str(value).strip()
            for value in types
            if pd.notna(value) and str(value).strip() not in {"", "none"}
        }
    )
    return "|".join(anomaly_types) if anomaly_types else "none"


def _join_planned_event_ids(values: pd.Series) -> str:
    """Join planned-event IDs while preserving 'none' for normal groups."""
    event_ids = sorted(
        {
            str(value).strip()
            for value in values
            if pd.notna(value) and str(value).strip() not in {"", "none", "nan"}
        }
    )
    return "|".join(event_ids) if event_ids else "none"


def load_raw_billing_data(path: Path = config.SYNTHETIC_CUR_LIKE_PATH) -> pd.DataFrame:
    """Load and normalize the raw synthetic CUR-like billing CSV."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Raw billing data not found: {path}")

    df = pd.read_csv(
        path,
        dtype={
            "anomaly_id": str,
            "planned_event_id": str,
            "usage_account_id": str,
        },
    )
    validate_raw_billing_data(df)

    normalized = df.copy()
    normalized["usage_date"] = (
        pd.to_datetime(normalized["usage_date"], errors="raise").dt.date.astype(str)
    )
    normalized["cost_usd"] = pd.to_numeric(
        normalized["cost_usd"],
        errors="raise",
    )
    normalized["usage_amount"] = pd.to_numeric(
        normalized["usage_amount"],
        errors="raise",
    )
    normalized["is_anomaly"] = pd.to_numeric(
        normalized["is_anomaly"],
        errors="raise",
    ).astype(int)
    normalized["planned_event"] = pd.to_numeric(
        normalized["planned_event"],
        errors="raise",
    ).astype(int)
    return normalized


def validate_raw_billing_data(df: pd.DataFrame) -> None:
    """Validate the raw synthetic billing input before aggregation."""
    missing_columns = sorted(set(config.CUR_LIKE_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Raw billing data is missing columns: {missing_columns}")

    usage_dates = pd.to_datetime(df["usage_date"], errors="raise")
    if usage_dates.dt.date.nunique() != config.NUM_DAYS:
        raise ValueError(f"Raw billing data must contain {config.NUM_DAYS} dates.")

    costs = pd.to_numeric(df["cost_usd"], errors="raise")
    if (costs < 0).any():
        raise ValueError("Raw billing data contains negative cost_usd values.")

    usage_amounts = pd.to_numeric(df["usage_amount"], errors="raise")
    if (usage_amounts <= 0).any():
        raise ValueError("Raw billing data contains non-positive usage_amount values.")

    anomaly_values = set(pd.to_numeric(df["is_anomaly"], errors="raise").unique())
    if not anomaly_values.issubset({0, 1}):
        raise ValueError("Raw is_anomaly must contain only 0/1.")

    planned_values = set(pd.to_numeric(df["planned_event"], errors="raise").unique())
    if not planned_values.issubset({0, 1}):
        raise ValueError("Raw planned_event must contain only 0/1.")
    if df["usage_account_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Raw usage_account_id must be non-empty.")
    if not (df.loc[df["planned_event"] == 0, "planned_event_id"] == "none").all():
        raise ValueError("Normal rows must use planned_event_id='none'.")


def build_daily_total_cost(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw billing rows to one row per usage date."""
    daily = (
        df.groupby("usage_date", as_index=False)
        .agg(
            total_cost_usd=("cost_usd", "sum"),
            total_usage_amount=("usage_amount", "sum"),
            service_count=("service", "nunique"),
            region_count=("region", "nunique"),
            account_count=("usage_account_id", "nunique"),
            row_count=("usage_date", "size"),
            is_anomaly=("is_anomaly", "max"),
            anomaly_types=("anomaly_type", _join_anomaly_types),
            planned_event=("planned_event", "max"),
            planned_event_ids=("planned_event_id", _join_planned_event_ids),
        )
        .sort_values("usage_date")
        .reset_index(drop=True)
    )
    daily["total_cost_usd"] = daily["total_cost_usd"].round(4)
    daily["total_usage_amount"] = daily["total_usage_amount"].round(4)
    daily["is_anomaly"] = daily["is_anomaly"].astype(int)
    daily["planned_event"] = daily["planned_event"].astype(int)
    return daily[config.PROCESSED_DAILY_TOTAL_COST_COLUMNS]


def build_daily_service_cost(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw billing rows to daily service-level cost."""
    daily_service = (
        df.groupby(["usage_date", "service"], as_index=False)
        .agg(
            service_cost_usd=("cost_usd", "sum"),
            service_usage_amount=("usage_amount", "sum"),
            row_count=("usage_date", "size"),
            is_anomaly=("is_anomaly", "max"),
            anomaly_types=("anomaly_type", _join_anomaly_types),
            planned_event=("planned_event", "max"),
            planned_event_ids=("planned_event_id", _join_planned_event_ids),
        )
        .sort_values(["usage_date", "service"])
        .reset_index(drop=True)
    )
    daily_service["service_cost_usd"] = daily_service["service_cost_usd"].round(4)
    daily_service["service_usage_amount"] = daily_service[
        "service_usage_amount"
    ].round(4)
    daily_service["is_anomaly"] = daily_service["is_anomaly"].astype(int)
    daily_service["planned_event"] = daily_service["planned_event"].astype(int)
    return daily_service[config.DAILY_SERVICE_COST_COLUMNS]


def build_daily_region_cost(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw billing rows to daily region-level cost."""
    daily_region = (
        df.groupby(["usage_date", "region"], as_index=False)
        .agg(
            region_cost_usd=("cost_usd", "sum"),
            region_usage_amount=("usage_amount", "sum"),
            row_count=("usage_date", "size"),
            is_anomaly=("is_anomaly", "max"),
            anomaly_types=("anomaly_type", _join_anomaly_types),
            planned_event=("planned_event", "max"),
            planned_event_ids=("planned_event_id", _join_planned_event_ids),
        )
        .sort_values(["usage_date", "region"])
        .reset_index(drop=True)
    )
    daily_region["region_cost_usd"] = daily_region["region_cost_usd"].round(4)
    daily_region["region_usage_amount"] = daily_region[
        "region_usage_amount"
    ].round(4)
    daily_region["is_anomaly"] = daily_region["is_anomaly"].astype(int)
    daily_region["planned_event"] = daily_region["planned_event"].astype(int)
    return daily_region[config.DAILY_REGION_COST_COLUMNS]


def build_daily_service_region_cost(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw billing rows to daily service-region cost."""
    daily_service_region = (
        df.groupby(["usage_date", "service", "region"], as_index=False)
        .agg(
            service_region_cost_usd=("cost_usd", "sum"),
            service_region_usage_amount=("usage_amount", "sum"),
            row_count=("usage_date", "size"),
            is_anomaly=("is_anomaly", "max"),
            anomaly_types=("anomaly_type", _join_anomaly_types),
            planned_event=("planned_event", "max"),
            planned_event_ids=("planned_event_id", _join_planned_event_ids),
        )
        .sort_values(["usage_date", "service", "region"])
        .reset_index(drop=True)
    )
    daily_service_region["service_region_cost_usd"] = daily_service_region[
        "service_region_cost_usd"
    ].round(4)
    daily_service_region["service_region_usage_amount"] = daily_service_region[
        "service_region_usage_amount"
    ].round(4)
    daily_service_region["is_anomaly"] = daily_service_region["is_anomaly"].astype(int)
    daily_service_region["planned_event"] = daily_service_region[
        "planned_event"
    ].astype(int)
    return daily_service_region[config.DAILY_SERVICE_REGION_COST_COLUMNS]


def validate_daily_total_cost(df: pd.DataFrame) -> None:
    """Validate the official Phase 3 daily total cost output."""
    if list(df.columns) != config.PROCESSED_DAILY_TOTAL_COST_COLUMNS:
        raise ValueError("daily_total_cost columns do not match the Phase 3 schema.")
    if len(df) != config.NUM_DAYS:
        raise ValueError(f"daily_total_cost must contain {config.NUM_DAYS} rows.")
    if df["usage_date"].duplicated().any():
        raise ValueError("daily_total_cost contains duplicate usage_date values.")
    if not df["usage_date"].is_monotonic_increasing:
        raise ValueError("daily_total_cost must be sorted by usage_date.")
    if (df["total_cost_usd"] < 0).any():
        raise ValueError("daily_total_cost contains negative total_cost_usd values.")
    if (df["total_usage_amount"] <= 0).any():
        raise ValueError("daily_total_cost contains non-positive usage totals.")
    if df["anomaly_types"].astype(str).str.strip().eq("").any():
        raise ValueError("daily_total_cost contains blank anomaly_types values.")
    if not set(df["is_anomaly"].unique()).issubset({0, 1}):
        raise ValueError("daily_total_cost is_anomaly must contain only 0/1.")
    if not set(df["planned_event"].unique()).issubset({0, 1}):
        raise ValueError("daily_total_cost planned_event must contain only 0/1.")
    if df["planned_event_ids"].astype(str).str.strip().eq("").any():
        raise ValueError("daily_total_cost contains blank planned_event_ids.")


def validate_processed_outputs(
    daily_total: pd.DataFrame,
    daily_service: pd.DataFrame,
    daily_region: pd.DataFrame,
    daily_service_region: pd.DataFrame,
) -> None:
    """Validate Phase 3 processed aggregate outputs."""
    validate_daily_total_cost(daily_total)

    expected_columns = {
        "daily_service_cost": (
            daily_service,
            config.DAILY_SERVICE_COST_COLUMNS,
            ["usage_date", "service"],
        ),
        "daily_region_cost": (
            daily_region,
            config.DAILY_REGION_COST_COLUMNS,
            ["usage_date", "region"],
        ),
        "daily_service_region_cost": (
            daily_service_region,
            config.DAILY_SERVICE_REGION_COST_COLUMNS,
            ["usage_date", "service", "region"],
        ),
    }

    for name, (output, columns, keys) in expected_columns.items():
        if list(output.columns) != columns:
            raise ValueError(f"{name} columns do not match the required schema.")
        if output.duplicated(keys).any():
            raise ValueError(f"{name} contains duplicate key rows.")
        if output["anomaly_types"].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name} contains blank anomaly_types values.")
        if not set(output["is_anomaly"].unique()).issubset({0, 1}):
            raise ValueError(f"{name} is_anomaly must contain only 0/1.")
        if not set(output["planned_event"].unique()).issubset({0, 1}):
            raise ValueError(f"{name} planned_event must contain only 0/1.")
        if output["planned_event_ids"].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name} contains blank planned_event_ids.")


def save_processed_outputs(
    daily_total: pd.DataFrame,
    daily_service: pd.DataFrame,
    daily_region: pd.DataFrame,
    daily_service_region: pd.DataFrame,
) -> dict[str, Path]:
    """Save Phase 3 processed aggregate CSV files and return their paths."""
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "daily_total_cost": config.DAILY_TOTAL_COST_PATH,
        "daily_service_cost": config.DAILY_SERVICE_COST_PATH,
        "daily_region_cost": config.DAILY_REGION_COST_PATH,
        "daily_service_region_cost": config.DAILY_SERVICE_REGION_COST_PATH,
    }
    daily_total.to_csv(paths["daily_total_cost"], index=False)
    daily_service.to_csv(paths["daily_service_cost"], index=False)
    daily_region.to_csv(paths["daily_region_cost"], index=False)
    daily_service_region.to_csv(paths["daily_service_region_cost"], index=False)
    return paths


def run_preprocessing(
    raw_path: Path = config.SYNTHETIC_CUR_LIKE_PATH,
    write_files: bool = True,
) -> dict[str, Any]:
    """Run the full Phase 3 preprocessing workflow."""
    raw_df = load_raw_billing_data(raw_path)
    daily_total = build_daily_total_cost(raw_df)
    daily_service = build_daily_service_cost(raw_df)
    daily_region = build_daily_region_cost(raw_df)
    daily_service_region = build_daily_service_region_cost(raw_df)
    validate_processed_outputs(
        daily_total,
        daily_service,
        daily_region,
        daily_service_region,
    )

    paths: dict[str, Path] = {}
    if write_files:
        paths = save_processed_outputs(
            daily_total,
            daily_service,
            daily_region,
            daily_service_region,
        )

    return {
        "paths": paths,
        "raw": raw_df,
        "daily_total": daily_total,
        "daily_service": daily_service,
        "daily_region": daily_region,
        "daily_service_region": daily_service_region,
    }


def main() -> None:
    """CLI entry point for Phase 3 preprocessing."""
    result = run_preprocessing()
    print("Preprocessing complete.")
    for path in result["paths"].values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
