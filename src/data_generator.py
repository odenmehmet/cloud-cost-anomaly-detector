"""
Synthetic CUR-like labeled billing data generator.

Phase 2 scope only:
- generate deterministic synthetic billing rows
- inject labeled ground-truth events
- write raw and daily aggregate CSV outputs
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

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # Allows: python src/data_generator.py
    import config  # type: ignore


def _date_for_day_offset(day_offset: int) -> pd.Timestamp:
    """Return the configured start date plus a day offset."""
    return pd.Timestamp(config.START_DATE) + pd.Timedelta(days=day_offset)


def _event_dates(event: dict[str, Any]) -> tuple[str, str]:
    """Return inclusive start and end dates for an event as ISO strings."""
    start_date = _date_for_day_offset(int(event["start_day"]))
    end_date = start_date + pd.Timedelta(days=int(event["duration_days"]) - 1)
    return start_date.date().isoformat(), end_date.date().isoformat()


def _build_baseline_rows(rng: np.random.Generator) -> pd.DataFrame:
    """Create deterministic daily service/region/tag billing rows."""
    rows: list[dict[str, Any]] = []
    start_date = pd.Timestamp(config.START_DATE)

    for day_index in range(config.NUM_DAYS):
        usage_date = start_date + pd.Timedelta(days=day_index)
        seasonality = config.WEEKLY_SEASONALITY_MULTIPLIERS[usage_date.weekday()]
        trend = 1.0 + (config.LONG_TERM_TREND_DAILY_RATE * day_index)

        for service in config.SERVICES:
            metadata = config.SERVICE_METADATA[service]
            for region in config.REGIONS:
                region_cost_multiplier = config.REGION_COST_MULTIPLIERS[region]
                for environment in config.TAG_ENVIRONMENTS:
                    environment_multiplier = config.ENVIRONMENT_USAGE_MULTIPLIERS[
                        environment
                    ]
                    for team in config.TAG_TEAMS:
                        team_multiplier = config.TEAM_USAGE_MULTIPLIERS[team]
                        expected_usage = (
                            metadata["base_usage"]
                            * environment_multiplier
                            * team_multiplier
                            * seasonality
                            * trend
                        )
                        usage_amount = expected_usage * rng.normal(
                            loc=1.0,
                            scale=config.USAGE_NOISE_STDDEV,
                        )
                        usage_amount = max(float(usage_amount), 0.0001)

                        cost_usd = (
                            usage_amount
                            * metadata["unit_rate"]
                            * region_cost_multiplier
                            * rng.normal(loc=1.0, scale=config.COST_NOISE_STDDEV)
                        )
                        cost_usd = max(float(cost_usd), 0.0)

                        rows.append(
                            {
                                "usage_date": usage_date.date().isoformat(),
                                "service": service,
                                "region": region,
                                "usage_amount": round(usage_amount, 4),
                                "usage_unit": metadata["usage_unit"],
                                "cost_usd": round(cost_usd, 4),
                                "operation": metadata["operation"],
                                "usage_type": metadata["usage_type"],
                                "tag_environment": environment,
                                "tag_team": team,
                                "line_item_type": "Usage",
                                "source_record_count": int(rng.integers(12, 160)),
                                "is_anomaly": 0,
                                "anomaly_type": "none",
                                "anomaly_id": "none",
                                "planned_event": 0,
                            }
                        )

    return pd.DataFrame(rows, columns=config.CUR_LIKE_COLUMNS)


def _event_row_mask(df: pd.DataFrame, event: dict[str, Any]) -> pd.Series:
    """Return rows affected by an event definition."""
    start_date, end_date = _event_dates(event)
    usage_dates = pd.to_datetime(df["usage_date"])
    return (
        (df["service"] == event["affected_service"])
        & (df["region"] == event["affected_region"])
        & (usage_dates >= pd.Timestamp(start_date))
        & (usage_dates <= pd.Timestamp(end_date))
    )


def _event_multipliers(
    df: pd.DataFrame,
    mask: pd.Series,
    event: dict[str, Any],
) -> np.ndarray:
    """Return per-row cost and usage multipliers for an event."""
    if event["anomaly_type"] != "gradual_drift":
        return np.full(mask.sum(), float(event["magnitude"]))

    start_date, _ = _event_dates(event)
    duration_days = int(event["duration_days"])
    daily_multipliers = np.linspace(
        float(event["start_magnitude"]),
        float(event["magnitude"]),
        num=duration_days,
    )
    day_offsets = (
        pd.to_datetime(df.loc[mask, "usage_date"]) - pd.Timestamp(start_date)
    ).dt.days
    return daily_multipliers[day_offsets.to_numpy()]


def _apply_events(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inject true anomalies and planned usage events into the baseline data."""
    df = df.copy()
    catalog_rows: list[dict[str, Any]] = []

    for event in config.ANOMALY_EVENTS:
        mask = _event_row_mask(df, event)
        if not mask.any():
            raise ValueError(f"Event matched no rows: {event['anomaly_id']}")

        multipliers = _event_multipliers(df, mask, event)
        df.loc[mask, "usage_amount"] = (
            df.loc[mask, "usage_amount"].to_numpy() * multipliers
        ).round(4)
        df.loc[mask, "cost_usd"] = (
            df.loc[mask, "cost_usd"].to_numpy() * multipliers
        ).round(4)

        if int(event["planned_event"]) == 1:
            df.loc[mask, "planned_event"] = 1
        else:
            df.loc[mask, "is_anomaly"] = 1
            df.loc[mask, "anomaly_type"] = event["anomaly_type"]
            df.loc[mask, "anomaly_id"] = event["anomaly_id"]

        start_date, end_date = _event_dates(event)
        catalog_rows.append(
            {
                "anomaly_id": event["anomaly_id"],
                "anomaly_type": event["anomaly_type"],
                "start_date": start_date,
                "end_date": end_date,
                "affected_service": event["affected_service"],
                "affected_region": event["affected_region"],
                "magnitude": float(event["magnitude"]),
                "planned_event": int(event["planned_event"]),
                "description": event["description"],
            }
        )

    catalog = pd.DataFrame(catalog_rows, columns=config.ANOMALY_CATALOG_COLUMNS)
    return df[config.CUR_LIKE_COLUMNS], catalog


def build_daily_total_cost(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate CUR-like rows into the Phase 2 daily total cost output."""

    def joined_anomaly_types(types: pd.Series) -> str:
        unique_types = sorted(t for t in types.unique() if t != "none")
        return "|".join(unique_types)

    daily = (
        df.groupby("usage_date", as_index=False)
        .agg(
            total_cost_usd=("cost_usd", "sum"),
            is_anomaly=("is_anomaly", "max"),
            anomaly_types=("anomaly_type", joined_anomaly_types),
            planned_event=("planned_event", "max"),
        )
        .sort_values("usage_date")
    )
    daily["total_cost_usd"] = daily["total_cost_usd"].round(4)
    daily["is_anomaly"] = daily["is_anomaly"].astype(int)
    daily["planned_event"] = daily["planned_event"].astype(int)
    return daily[config.DAILY_TOTAL_COST_COLUMNS]


def validate_generated_data(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    daily_total: pd.DataFrame,
) -> None:
    """Validate generated Phase 2 outputs before writing CSV files."""
    if list(df.columns) != config.CUR_LIKE_COLUMNS:
        raise ValueError("Main dataset columns do not match the required schema.")
    if list(catalog.columns) != config.ANOMALY_CATALOG_COLUMNS:
        raise ValueError("Anomaly catalog columns do not match the required schema.")
    if list(daily_total.columns) != config.DAILY_TOTAL_COST_COLUMNS:
        raise ValueError("Daily total columns do not match the required schema.")

    parsed_dates = pd.to_datetime(df["usage_date"], errors="raise")
    if parsed_dates.dt.date.nunique() != config.NUM_DAYS:
        raise ValueError(f"Generated date count must be {config.NUM_DAYS}.")

    if (df["cost_usd"] < 0).any():
        raise ValueError("cost_usd contains negative values.")
    if (df["usage_amount"] <= 0).any():
        raise ValueError("usage_amount contains non-positive values.")
    if not set(df["is_anomaly"].unique()).issubset({0, 1}):
        raise ValueError("is_anomaly must contain only 0/1.")
    if not set(df["planned_event"].unique()).issubset({0, 1}):
        raise ValueError("planned_event must contain only 0/1.")

    anomaly_rows = df["is_anomaly"] == 1
    anomaly_ids = df.loc[anomaly_rows, "anomaly_id"].astype(str).str.strip()
    invalid_normal_ids = {"", "none", "nan"}
    if anomaly_ids.empty or anomaly_ids.str.lower().isin(invalid_normal_ids).any():
        raise ValueError("All true anomaly rows must have a non-empty anomaly_id.")

    normalized_ids = df["anomaly_id"].astype(str).str.strip()
    used_ids = set(
        df.loc[~normalized_ids.str.lower().isin(invalid_normal_ids), "anomaly_id"]
    )
    catalog_ids = set(catalog["anomaly_id"])
    missing_catalog_ids = sorted(used_ids - catalog_ids)
    if missing_catalog_ids:
        raise ValueError(
            f"Main dataset uses anomaly_id values missing from catalog: "
            f"{missing_catalog_ids}"
        )

    if not (df.loc[df["is_anomaly"] == 0, "anomaly_type"] == "none").all():
        raise ValueError("Rows with is_anomaly=0 must use anomaly_type='none'.")

    catalog_types = set(catalog["anomaly_type"])
    missing_types = sorted(set(config.REQUIRED_CATALOG_EVENT_TYPES) - catalog_types)
    if missing_types:
        raise ValueError(f"Catalog is missing required event types: {missing_types}")

    planned_catalog = catalog[catalog["anomaly_type"] == "legitimate_usage_increase"]
    if planned_catalog.empty or not (planned_catalog["planned_event"] == 1).all():
        raise ValueError("legitimate_usage_increase must exist as a planned event.")

    planned_rows = df["planned_event"] == 1
    if not planned_rows.any():
        raise ValueError("Main dataset must contain planned_event rows.")
    if not (df.loc[planned_rows, "is_anomaly"] == 0).all():
        raise ValueError("Planned usage increase rows must not be true anomalies.")
    if not (df.loc[planned_rows, "anomaly_type"] == "none").all():
        raise ValueError("Planned usage increase rows must keep anomaly_type='none'.")

    if pd.to_datetime(daily_total["usage_date"]).dt.date.nunique() != config.NUM_DAYS:
        raise ValueError("Daily total output must contain exactly one row per day.")


def _ensure_output_directories(paths: dict[str, Path]) -> None:
    """Create output directories if they do not already exist."""
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_outputs(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    daily_total: pd.DataFrame,
    paths: dict[str, Path],
) -> None:
    """Write generated datasets to disk."""
    _ensure_output_directories(paths)
    df.to_csv(paths["synthetic_cur_like_daily"], index=False)
    catalog.to_csv(paths["anomaly_catalog"], index=False)
    daily_total.to_csv(paths["daily_total_cost"], index=False)


def _build_summary(df: pd.DataFrame, daily_total: pd.DataFrame) -> dict[str, int]:
    """Build console summary statistics for generated outputs."""
    return {
        "rows_generated": int(len(df)),
        "days": int(df["usage_date"].nunique()),
        "anomaly_rows": int(df["is_anomaly"].sum()),
        "anomaly_days": int((daily_total["is_anomaly"] == 1).sum()),
        "planned_event_rows": int(df["planned_event"].sum()),
    }


def print_generation_summary(summary: dict[str, int], paths: dict[str, Path]) -> None:
    """Print the required Phase 2 generation summary."""
    print("Synthetic CUR-like data generation complete.")
    print(f"Rows generated: {summary['rows_generated']}")
    print(f"Days: {summary['days']}")
    print(f"Anomaly rows: {summary['anomaly_rows']}")
    print(f"Anomaly days: {summary['anomaly_days']}")
    print(f"Planned event rows: {summary['planned_event_rows']}")
    print("Output paths:")
    for path in paths.values():
        print(f"- {path}")


def generate_synthetic_dataset(
    seed: int = config.DEFAULT_RANDOM_SEED,
    write_files: bool = True,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Generate deterministic synthetic CUR-like billing data and Phase 2 outputs.

    Returns a dictionary containing output paths, summary statistics, and the
    generated DataFrames for callers that want to inspect the data in memory.
    """
    rng = np.random.default_rng(seed)
    paths = {
        "synthetic_cur_like_daily": config.SYNTHETIC_CUR_LIKE_PATH,
        "anomaly_catalog": config.ANOMALY_CATALOG_PATH,
        "daily_total_cost": config.DAILY_TOTAL_COST_PATH,
    }

    baseline = _build_baseline_rows(rng)
    cur_like, anomaly_catalog = _apply_events(baseline)
    daily_total = build_daily_total_cost(cur_like)
    validate_generated_data(cur_like, anomaly_catalog, daily_total)

    if write_files:
        _write_outputs(cur_like, anomaly_catalog, daily_total, paths)

    summary = _build_summary(cur_like, daily_total)
    if verbose:
        print_generation_summary(summary, paths)

    return {
        "paths": paths,
        "summary": summary,
        "cur_like": cur_like,
        "anomaly_catalog": anomaly_catalog,
        "daily_total": daily_total,
    }


def main() -> None:
    """CLI entry point for Phase 2 data generation."""
    generate_synthetic_dataset()


if __name__ == "__main__":
    main()
