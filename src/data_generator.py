"""Deterministic synthetic CUR-like billing data with labeled events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # Allows: python src/data_generator.py
    import config  # type: ignore


def _date_for_day_offset(day_offset: int) -> pd.Timestamp:
    return pd.Timestamp(config.START_DATE) + pd.Timedelta(days=day_offset)


def _event_dates(event: dict[str, Any]) -> tuple[str, str]:
    start_date = _date_for_day_offset(int(event["start_day"]))
    end_date = start_date + pd.Timedelta(days=int(event["duration_days"]) - 1)
    return start_date.date().isoformat(), end_date.date().isoformat()


def _build_baseline_rows(rng: np.random.Generator) -> pd.DataFrame:
    """Create daily service/region/tag rows with moderate CUR-like metadata."""
    rows: list[dict[str, Any]] = []
    start_date = pd.Timestamp(config.START_DATE)

    for day_index in range(config.NUM_DAYS):
        usage_date = start_date + pd.Timedelta(days=day_index)
        seasonality = config.WEEKLY_SEASONALITY_MULTIPLIERS[usage_date.weekday()]
        trend = 1.0 + (config.LONG_TERM_TREND_DAILY_RATE * day_index)
        billing_period_start = usage_date.replace(day=1).date().isoformat()
        daily_multiplier = rng.normal(
            loc=1.0,
            scale=config.DAILY_GLOBAL_NOISE_STDDEV,
        )
        service_multipliers = {
            service: rng.normal(
                loc=1.0,
                scale=config.SERVICE_DAILY_NOISE_STDDEV,
            )
            for service in config.SERVICES
        }

        for service in config.SERVICES:
            metadata = config.SERVICE_METADATA[service]
            for region in config.REGIONS:
                region_cost_multiplier = config.REGION_COST_MULTIPLIERS[region]
                for environment in config.TAG_ENVIRONMENTS:
                    environment_multiplier = config.ENVIRONMENT_USAGE_MULTIPLIERS[
                        environment
                    ]
                    for team in config.TAG_TEAMS:
                        expected_usage = (
                            metadata["base_usage"]
                            * environment_multiplier
                            * config.TEAM_USAGE_MULTIPLIERS[team]
                            * seasonality
                            * trend
                            * daily_multiplier
                            * service_multipliers[service]
                        )
                        usage_amount = max(
                            float(
                                expected_usage
                                * rng.normal(
                                    loc=1.0,
                                    scale=config.USAGE_NOISE_STDDEV,
                                )
                            ),
                            0.0001,
                        )
                        cost_usd = max(
                            float(
                                usage_amount
                                * metadata["unit_rate"]
                                * region_cost_multiplier
                                * rng.normal(
                                    loc=1.0,
                                    scale=config.COST_NOISE_STDDEV,
                                )
                            ),
                            0.0,
                        )
                        rows.append(
                            {
                                "usage_date": usage_date.date().isoformat(),
                                "billing_period_start": billing_period_start,
                                "usage_account_id": config.ACCOUNT_BY_ENVIRONMENT[
                                    environment
                                ],
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
                                "billing_currency": "USD",
                                "source_record_count": int(rng.integers(12, 160)),
                                "is_anomaly": 0,
                                "anomaly_type": "none",
                                "anomaly_id": "none",
                                "planned_event": 0,
                                "planned_event_id": "none",
                            }
                        )

    return pd.DataFrame(rows, columns=config.CUR_LIKE_COLUMNS)


def _event_row_mask(df: pd.DataFrame, event: dict[str, Any]) -> pd.Series:
    start_date, end_date = _event_dates(event)
    usage_dates = pd.to_datetime(df["usage_date"])
    return (
        (df["service"] == event["affected_service"])
        & (df["region"] == event["affected_region"])
        & usage_dates.between(pd.Timestamp(start_date), pd.Timestamp(end_date))
    )


def _event_multipliers(
    df: pd.DataFrame,
    mask: pd.Series,
    event: dict[str, Any],
) -> np.ndarray:
    if event.get("anomaly_type") != "gradual_drift":
        return np.full(mask.sum(), float(event["magnitude"]))

    start_date, _ = _event_dates(event)
    daily_multipliers = np.linspace(
        float(event["start_magnitude"]),
        float(event["magnitude"]),
        num=int(event["duration_days"]),
    )
    day_offsets = (
        pd.to_datetime(df.loc[mask, "usage_date"]) - pd.Timestamp(start_date)
    ).dt.days
    return daily_multipliers[day_offsets.to_numpy()]


def _multiply_event_rows(
    df: pd.DataFrame,
    event: dict[str, Any],
) -> tuple[pd.DataFrame, pd.Series]:
    mask = _event_row_mask(df, event)
    event_id = event.get("anomaly_id", event.get("planned_event_id", "unknown"))
    if not mask.any():
        raise ValueError(f"Event matched no rows: {event_id}")
    multipliers = _event_multipliers(df, mask, event)
    df.loc[mask, "usage_amount"] = (
        df.loc[mask, "usage_amount"].to_numpy() * multipliers
    ).round(4)
    df.loc[mask, "cost_usd"] = (
        df.loc[mask, "cost_usd"].to_numpy() * multipliers
    ).round(4)
    return df, mask


def _apply_events(
    baseline: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Inject anomaly labels and planned-event metadata separately."""
    df = baseline.copy()
    anomaly_catalog_rows: list[dict[str, Any]] = []
    planned_catalog_rows: list[dict[str, Any]] = []

    for event in config.ANOMALY_EVENTS:
        df, mask = _multiply_event_rows(df, event)
        df.loc[mask, "is_anomaly"] = 1
        df.loc[mask, "anomaly_type"] = event["anomaly_type"]
        df.loc[mask, "anomaly_id"] = event["anomaly_id"]
        start_date, end_date = _event_dates(event)
        anomaly_catalog_rows.append(
            {
                "anomaly_id": event["anomaly_id"],
                "anomaly_type": event["anomaly_type"],
                "start_date": start_date,
                "end_date": end_date,
                "affected_service": event["affected_service"],
                "affected_region": event["affected_region"],
                "magnitude": float(event["magnitude"]),
                "description": event["description"],
            }
        )

    for event in config.PLANNED_EVENTS:
        df, mask = _multiply_event_rows(df, event)
        if df.loc[mask, "is_anomaly"].any():
            raise ValueError("Planned events must not overlap injected anomalies.")
        df.loc[mask, "planned_event"] = 1
        df.loc[mask, "planned_event_id"] = event["planned_event_id"]
        start_date, end_date = _event_dates(event)
        planned_catalog_rows.append(
            {
                "planned_event_id": event["planned_event_id"],
                "planned_event_type": event["planned_event_type"],
                "start_date": start_date,
                "end_date": end_date,
                "affected_service": event["affected_service"],
                "affected_region": event["affected_region"],
                "magnitude": float(event["magnitude"]),
                "description": event["description"],
            }
        )

    anomaly_catalog = pd.DataFrame(
        anomaly_catalog_rows,
        columns=config.ANOMALY_CATALOG_COLUMNS,
    )
    planned_catalog = pd.DataFrame(
        planned_catalog_rows,
        columns=config.PLANNED_EVENT_CATALOG_COLUMNS,
    )
    return df[config.CUR_LIKE_COLUMNS], anomaly_catalog, planned_catalog


def _join_values(values: pd.Series, excluded: set[str]) -> str:
    unique_values = sorted(
        {
            str(value).strip()
            for value in values
            if pd.notna(value) and str(value).strip().lower() not in excluded
        }
    )
    return "|".join(unique_values) if unique_values else "none"


def build_daily_total_cost(df: pd.DataFrame) -> pd.DataFrame:
    daily = (
        df.groupby("usage_date", as_index=False)
        .agg(
            total_cost_usd=("cost_usd", "sum"),
            is_anomaly=("is_anomaly", "max"),
            anomaly_types=(
                "anomaly_type",
                lambda values: _join_values(values, {"", "none", "nan"}),
            ),
            planned_event=("planned_event", "max"),
            planned_event_ids=(
                "planned_event_id",
                lambda values: _join_values(values, {"", "none", "nan"}),
            ),
        )
        .sort_values("usage_date")
        .reset_index(drop=True)
    )
    daily["total_cost_usd"] = daily["total_cost_usd"].round(4)
    daily["is_anomaly"] = daily["is_anomaly"].astype(int)
    daily["planned_event"] = daily["planned_event"].astype(int)
    return daily[config.DAILY_TOTAL_COST_COLUMNS]


def _catalog_dates(catalog: pd.DataFrame, id_column: str) -> dict[str, set[str]]:
    return {
        str(row[id_column]): set(
            pd.date_range(row["start_date"], row["end_date"]).strftime("%Y-%m-%d")
        )
        for _, row in catalog.iterrows()
    }


def validate_generated_data(
    df: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
    planned_catalog: pd.DataFrame,
    daily_total: pd.DataFrame,
) -> None:
    """Validate raw labels, catalogs, and daily totals before writing."""
    if list(df.columns) != config.CUR_LIKE_COLUMNS:
        raise ValueError("Main dataset columns do not match the required schema.")
    if list(anomaly_catalog.columns) != config.ANOMALY_CATALOG_COLUMNS:
        raise ValueError("Anomaly catalog columns do not match the required schema.")
    if list(planned_catalog.columns) != config.PLANNED_EVENT_CATALOG_COLUMNS:
        raise ValueError("Planned-event catalog columns do not match the schema.")
    if list(daily_total.columns) != config.DAILY_TOTAL_COST_COLUMNS:
        raise ValueError("Daily total columns do not match the required schema.")

    parsed_dates = pd.to_datetime(df["usage_date"], errors="raise")
    if parsed_dates.dt.date.nunique() != config.NUM_DAYS:
        raise ValueError(f"Generated date count must be {config.NUM_DAYS}.")
    if df.duplicated(
        ["usage_date", "service", "region", "tag_environment", "tag_team"]
    ).any():
        raise ValueError("Generated data contains duplicate billing dimension rows.")
    if (df["cost_usd"] < 0).any() or (df["usage_amount"] <= 0).any():
        raise ValueError("Generated costs and usage amounts must be positive.")
    if set(df["usage_account_id"]) != set(config.ACCOUNT_BY_ENVIRONMENT.values()):
        raise ValueError("Generated account IDs do not match configured accounts.")
    if set(df["billing_currency"]) != {"USD"}:
        raise ValueError("billing_currency must be USD.")

    anomaly_rows = df[df["is_anomaly"] == 1]
    planned_rows = df[df["planned_event"] == 1]
    if anomaly_rows.empty or planned_rows.empty:
        raise ValueError("Both anomaly and planned-event rows are required.")
    if planned_rows["is_anomaly"].any():
        raise ValueError("Planned-event rows must not be anomaly ground truth.")
    if not (df.loc[df["is_anomaly"] == 0, "anomaly_type"] == "none").all():
        raise ValueError("Normal rows must use anomaly_type='none'.")
    if anomaly_rows["anomaly_id"].isin(["", "none"]).any():
        raise ValueError("True anomaly rows require anomaly_id.")
    if planned_rows["planned_event_id"].isin(["", "none"]).any():
        raise ValueError("Planned-event rows require planned_event_id.")

    anomaly_dates = _catalog_dates(anomaly_catalog, "anomaly_id")
    for anomaly_id, expected_dates in anomaly_dates.items():
        actual_dates = set(
            anomaly_rows.loc[anomaly_rows["anomaly_id"] == anomaly_id, "usage_date"]
        )
        if actual_dates != expected_dates:
            raise ValueError(f"Anomaly catalog dates do not match {anomaly_id}.")
    planned_dates = _catalog_dates(planned_catalog, "planned_event_id")
    for planned_event_id, expected_dates in planned_dates.items():
        actual_dates = set(
            planned_rows.loc[
                planned_rows["planned_event_id"] == planned_event_id,
                "usage_date",
            ]
        )
        if actual_dates != expected_dates:
            raise ValueError(
                f"Planned-event catalog dates do not match {planned_event_id}."
            )

    if set(anomaly_catalog["anomaly_type"]) != set(
        config.REQUIRED_CATALOG_EVENT_TYPES
    ):
        raise ValueError("Anomaly catalog event types are incomplete.")
    if pd.to_datetime(daily_total["usage_date"]).dt.date.nunique() != config.NUM_DAYS:
        raise ValueError("Daily total output must contain one row per day.")


def _write_outputs(
    df: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
    planned_catalog: pd.DataFrame,
    daily_total: pd.DataFrame,
    paths: dict[str, Path],
) -> None:
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["synthetic_cur_like_daily"], index=False)
    anomaly_catalog.to_csv(paths["anomaly_catalog"], index=False)
    planned_catalog.to_csv(paths["planned_event_catalog"], index=False)
    daily_total.to_csv(paths["daily_total_cost"], index=False)


def generate_synthetic_dataset(
    seed: int = config.DEFAULT_RANDOM_SEED,
    write_files: bool = True,
    verbose: bool = True,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    paths = {
        "synthetic_cur_like_daily": config.SYNTHETIC_CUR_LIKE_PATH,
        "anomaly_catalog": config.ANOMALY_CATALOG_PATH,
        "planned_event_catalog": config.PLANNED_EVENT_CATALOG_PATH,
        "daily_total_cost": config.DAILY_TOTAL_COST_PATH,
    }
    baseline = _build_baseline_rows(rng)
    cur_like, anomaly_catalog, planned_catalog = _apply_events(baseline)
    daily_total = build_daily_total_cost(cur_like)
    validate_generated_data(
        cur_like,
        anomaly_catalog,
        planned_catalog,
        daily_total,
    )
    if write_files:
        _write_outputs(
            cur_like,
            anomaly_catalog,
            planned_catalog,
            daily_total,
            paths,
        )

    summary = {
        "rows_generated": int(len(cur_like)),
        "days": int(cur_like["usage_date"].nunique()),
        "anomaly_rows": int(cur_like["is_anomaly"].sum()),
        "anomaly_days": int((daily_total["is_anomaly"] == 1).sum()),
        "planned_event_rows": int(cur_like["planned_event"].sum()),
        "planned_event_days": int((daily_total["planned_event"] == 1).sum()),
    }
    if verbose:
        print("Synthetic CUR-like data generation complete.")
        for key, value in summary.items():
            print(f"{key}: {value}")
        for path in paths.values():
            print(f"- {path}")

    return {
        "paths": paths,
        "summary": summary,
        "cur_like": cur_like,
        "anomaly_catalog": anomaly_catalog,
        "planned_event_catalog": planned_catalog,
        "daily_total": daily_total,
    }


def main() -> None:
    generate_synthetic_dataset()


if __name__ == "__main__":
    main()
