"""
Service-region contributor analysis for alert dates.

This module performs lightweight contributor analysis only. It does not claim
causal root-cause attribution.
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
except ImportError:  # Allows: python src/contributors.py
    import config  # type: ignore


def load_service_region_cost(
    path: Path = config.DAILY_SERVICE_REGION_COST_PATH,
) -> pd.DataFrame:
    """Load daily service-region cost data for contributor analysis."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Daily service-region cost file not found: {path}")

    df = pd.read_csv(path)
    missing_columns = sorted(
        set(config.DAILY_SERVICE_REGION_COST_COLUMNS) - set(df.columns)
    )
    if missing_columns:
        raise ValueError(f"Service-region cost data is missing: {missing_columns}")

    df = df.copy().sort_values(["usage_date", "service", "region"]).reset_index(
        drop=True
    )
    df["usage_date"] = pd.to_datetime(df["usage_date"], errors="raise").dt.date.astype(
        str
    )
    df["service_region_cost_usd"] = pd.to_numeric(
        df["service_region_cost_usd"],
        errors="raise",
    )
    if (df["service_region_cost_usd"] < 0).any():
        raise ValueError("service_region_cost_usd must be non-negative.")
    return df


def _load_alerts(path: Path = config.ALERTS_PATH) -> pd.DataFrame:
    """Load generated alerts for contributor analysis."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Alerts file not found: {path}")

    alerts = pd.read_csv(path)
    missing_columns = sorted(set(config.ALERT_COLUMNS) - set(alerts.columns))
    if missing_columns:
        raise ValueError(f"Alerts data is missing columns: {missing_columns}")
    alerts = alerts.copy().sort_values("usage_date").reset_index(drop=True)
    alerts["usage_date"] = pd.to_datetime(
        alerts["usage_date"],
        errors="raise",
    ).dt.date.astype(str)
    return alerts


def compute_previous_7d_average(
    service_region_df: pd.DataFrame,
    alert_date: str | pd.Timestamp,
    service: str,
    region: str,
) -> float:
    """Compute previous seven available days average for one service-region pair."""
    df = service_region_df.copy()
    if "_usage_timestamp" not in df.columns:
        df["_usage_timestamp"] = pd.to_datetime(df["usage_date"], errors="raise")

    alert_timestamp = pd.Timestamp(alert_date)
    history = df[
        (df["_usage_timestamp"] < alert_timestamp)
        & (df["service"] == service)
        & (df["region"] == region)
    ].sort_values("_usage_timestamp")

    if history.empty:
        return 0.0

    previous_values = history.tail(7)["service_region_cost_usd"]
    return round(float(previous_values.mean()), 4)


def _contributor_reason(row: pd.Series) -> str:
    """Build a concise non-causal contributor explanation."""
    share_percent = row["contribution_share"] * 100
    if row["contribution_basis"] == "positive_delta":
        return (
            f"{row['service']} in {row['region']} contributed "
            f"{share_percent:.1f}% of the positive cost increase versus its "
            "previous 7-day average."
        )
    return (
        f"{row['service']} in {row['region']} was among the largest current "
        f"service-region costs on this alert date, contributing "
        f"{share_percent:.1f}% of current alert-date cost."
    )


def build_contributors(
    alerts: pd.DataFrame,
    service_region_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build top service-region contributors for each alert date."""
    service_region = service_region_df.copy()
    service_region["_usage_timestamp"] = pd.to_datetime(
        service_region["usage_date"],
        errors="raise",
    )

    contributor_rows: list[dict[str, object]] = []
    for alert in alerts.sort_values("usage_date").itertuples(index=False):
        alert_date = str(alert.usage_date)
        current = service_region[service_region["usage_date"] == alert_date].copy()
        if current.empty:
            raise ValueError(f"No service-region rows found for alert date {alert_date}.")

        current["cost_usd"] = current["service_region_cost_usd"].round(4)
        previous_averages: list[float] = []
        for row in current.itertuples(index=False):
            previous_averages.append(
                compute_previous_7d_average(
                    service_region,
                    alert_date,
                    row.service,
                    row.region,
                )
            )

        current["previous_7d_avg_cost"] = previous_averages
        current["delta_cost"] = (
            current["cost_usd"] - current["previous_7d_avg_cost"]
        ).round(4)
        current["positive_delta_cost"] = current["delta_cost"].clip(lower=0.0)
        positive_delta_sum = float(current["positive_delta_cost"].sum())

        if positive_delta_sum > 0:
            current["contribution_share"] = (
                current["positive_delta_cost"] / positive_delta_sum
            )
            current["contribution_basis"] = "positive_delta"
            ranked = current[current["positive_delta_cost"] > 0].sort_values(
                ["positive_delta_cost", "cost_usd", "service", "region"],
                ascending=[False, False, True, True],
            ).head(config.TOP_CONTRIBUTOR_LIMIT)
        else:
            total_current_cost = float(current["cost_usd"].sum())
            if total_current_cost > 0:
                current["contribution_share"] = current["cost_usd"] / total_current_cost
            else:
                current["contribution_share"] = 0.0
            current["contribution_basis"] = "current_cost_fallback"
            ranked = current.sort_values(
                ["cost_usd", "service", "region"],
                ascending=[False, True, True],
            ).head(config.TOP_CONTRIBUTOR_LIMIT)

        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            row_series = pd.Series(row._asdict())
            contributor_rows.append(
                {
                    "alert_id": alert.alert_id,
                    "usage_date": alert_date,
                    "alert_level": alert.alert_level,
                    "service": row.service,
                    "region": row.region,
                    "cost_usd": round(float(row.cost_usd), 4),
                    "previous_7d_avg_cost": round(
                        float(row.previous_7d_avg_cost),
                        4,
                    ),
                    "delta_cost": round(float(row.delta_cost), 4),
                    "contribution_share": round(
                        float(np.clip(row.contribution_share, 0.0, 1.0)),
                        6,
                    ),
                    "contribution_basis": row.contribution_basis,
                    "rank": rank,
                    "contributor_reason": _contributor_reason(row_series),
                }
            )

    contributors = pd.DataFrame(contributor_rows, columns=config.CONTRIBUTOR_COLUMNS)
    validate_contributors(contributors, alerts)
    return contributors


def validate_contributors(
    contributors: pd.DataFrame,
    alerts: pd.DataFrame,
) -> None:
    """Validate generated contributor rows."""
    if list(contributors.columns) != config.CONTRIBUTOR_COLUMNS:
        raise ValueError("contributors columns do not match the required schema.")
    if contributors.empty:
        raise ValueError("contributors must contain at least one row.")

    alert_ids = set(alerts["alert_id"])
    contributor_alert_ids = set(contributors["alert_id"])
    if not contributor_alert_ids.issubset(alert_ids):
        raise ValueError("Every contributor alert_id must exist in alerts.csv.")
    if not alert_ids.issubset(contributor_alert_ids):
        raise ValueError("Every alert must have at least one contributor row.")

    if not (contributors.groupby("alert_id")["rank"].min() == 1).all():
        raise ValueError("Each alert must have rank 1 contributor.")
    if (contributors.groupby("alert_id").size() > config.TOP_CONTRIBUTOR_LIMIT).any():
        raise ValueError("Each alert can have at most five contributors.")

    for alert_id, group in contributors.groupby("alert_id"):
        expected_ranks = list(range(1, len(group) + 1))
        actual_ranks = sorted(group["rank"].astype(int).tolist())
        if actual_ranks != expected_ranks:
            raise ValueError(f"Contributor ranks are not consecutive for {alert_id}.")

    numeric_columns = [
        "cost_usd",
        "previous_7d_avg_cost",
        "delta_cost",
        "contribution_share",
    ]
    numeric_values = contributors[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric_values.to_numpy()).all():
        raise ValueError("contributors contains non-finite numeric values.")
    if (numeric_values["cost_usd"] < 0).any():
        raise ValueError("cost_usd must be non-negative.")
    if (numeric_values["previous_7d_avg_cost"] < 0).any():
        raise ValueError("previous_7d_avg_cost must be non-negative.")
    if not contributors["contribution_share"].between(0, 1).all():
        raise ValueError("contribution_share must be between 0 and 1.")
    allowed_bases = {"positive_delta", "current_cost_fallback"}
    if not set(contributors["contribution_basis"]).issubset(allowed_bases):
        raise ValueError("contribution_basis contains invalid values.")
    positive_rows = contributors["contribution_basis"] == "positive_delta"
    if (contributors.loc[positive_rows, "delta_cost"] <= 0).any():
        raise ValueError("positive_delta contributors must have positive delta_cost.")
    if contributors["contributor_reason"].astype(str).str.strip().eq("").any():
        raise ValueError("contributor_reason must be non-empty.")


def save_contributors(
    contributors: pd.DataFrame,
    path: Path = config.CONTRIBUTORS_PATH,
) -> Path:
    """Save contributor analysis rows to CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    contributors.to_csv(path, index=False)
    return path


def run_contributor_analysis() -> Path:
    """Run Phase 5 contributor analysis and write contributors.csv."""
    alerts = _load_alerts(config.ALERTS_PATH)
    service_region = load_service_region_cost(config.DAILY_SERVICE_REGION_COST_PATH)
    contributors = build_contributors(alerts, service_region)
    return save_contributors(contributors, config.CONTRIBUTORS_PATH)


def main() -> None:
    """CLI entry point for Phase 5 contributor analysis."""
    path = run_contributor_analysis()
    print("Contributor analysis complete.")
    print(f"- {path}")


if __name__ == "__main__":
    main()
