"""Operational alert generation from calibrated detector outputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # Allows: python src/alerts.py
    import config  # type: ignore


METHOD_ORDER = ["zscore", "stl", "isolation_forest"]
ALLOWED_ALERT_LEVELS = {"warning", "critical"}


def load_method_results(path: Path = config.METHOD_RESULTS_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Method results file not found: {path}")
    df = pd.read_csv(path)
    validate_method_results(df)
    df = df.sort_values(["usage_date", "method"]).reset_index(drop=True)
    df["usage_date"] = pd.to_datetime(df["usage_date"]).dt.date.astype(str)
    return df


def _load_daily_features(path: Path = config.DAILY_FEATURES_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Daily features file not found: {path}")
    df = pd.read_csv(path)
    required = {
        "usage_date",
        "is_anomaly",
        "anomaly_types",
        "planned_event",
        "planned_event_ids",
        "top_service",
        "top_region",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Daily features are missing columns: {missing}")
    df = df.sort_values("usage_date").reset_index(drop=True)
    df["usage_date"] = pd.to_datetime(df["usage_date"]).dt.date.astype(str)
    return df


def validate_method_results(df: pd.DataFrame) -> None:
    missing = sorted(set(config.DETECTOR_RESULT_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"method_results is missing columns: {missing}")
    if set(df["method"].unique()) != set(METHOD_ORDER):
        raise ValueError("method_results must contain all three required methods.")
    if len(df) != config.NUM_DAYS * len(METHOD_ORDER):
        raise ValueError("method_results row count is incorrect.")
    if df.duplicated(["usage_date", "method"]).any():
        raise ValueError("method_results contains duplicate date/method rows.")
    numeric = df[
        [
            "score",
            "threshold",
            "actual_cost",
            "expected_cost",
            "deviation",
            "relative_deviation",
        ]
    ].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("method_results contains non-finite values.")


def _ordered_triggered_methods(triggered: pd.DataFrame) -> list[str]:
    method_names = set(triggered["method"])
    return [method for method in METHOD_ORDER if method in method_names]


def _choose_expected_cost(group: pd.DataFrame, actual_cost: float) -> float:
    """Use the median method baseline so one decomposition cannot dominate."""
    expected = pd.to_numeric(group["expected_cost"], errors="coerce")
    expected = expected[np.isfinite(expected) & (expected > 0)]
    return float(expected.median()) if not expected.empty else actual_cost


def _candidate_level(
    method_count: int,
    relative_delta: float,
    severity_hints: str,
) -> str | None:
    """Apply explicit agreement and upward-deviation gates."""
    if relative_delta < config.ALERT_WARNING_RELATIVE_DELTA:
        return None
    if (
        method_count >= config.ALERT_CRITICAL_MIN_METHODS
        and relative_delta >= config.ALERT_CRITICAL_RELATIVE_DELTA
    ):
        return "critical"
    if method_count >= config.ALERT_WARNING_MIN_METHODS:
        return "warning"
    if (
        method_count == 1
        and relative_delta >= config.ALERT_STRONG_SINGLE_METHOD_DELTA
        and ":high" in severity_hints
    ):
        return "warning"
    return None


def build_alert_method_summary(
    method_results: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate raw detector rows to one policy-decision row per day."""
    context = daily_features[
        [
            "usage_date",
            "is_anomaly",
            "anomaly_types",
            "planned_event",
            "planned_event_ids",
            "top_service",
            "top_region",
        ]
    ].rename(
        columns={
            "is_anomaly": "is_true_anomaly",
            "anomaly_types": "anomaly_type",
        }
    )

    rows: list[dict[str, object]] = []
    for usage_date, group in method_results.groupby("usage_date", sort=True):
        triggered = group[group["is_flagged"] == 1].copy()
        methods = _ordered_triggered_methods(triggered)
        actual_cost = float(pd.to_numeric(group["actual_cost"]).median())
        expected_cost = _choose_expected_cost(group, actual_cost)
        relative_delta = (
            max(0.0, (actual_cost - expected_cost) / expected_cost)
            if expected_cost > 0
            else 0.0
        )

        if triggered.empty:
            max_method_score = 0.0
            severity_hints = "none"
            explanations = "No detector flagged this date."
        else:
            max_method_score = float(pd.to_numeric(triggered["score"]).abs().max())
            severity_hints = ",".join(
                f"{row.method}:{row.severity_hint}"
                for row in triggered.sort_values("method").itertuples(index=False)
            )
            explanations = " | ".join(
                f"{row.method}: {row.explanation}"
                for row in triggered.sort_values("method").itertuples(index=False)
            )

        rows.append(
            {
                "usage_date": usage_date,
                "methods_triggered": ",".join(methods),
                "method_count": len(methods),
                "actual_cost": round(actual_cost, 4),
                "expected_cost": round(expected_cost, 4),
                "relative_delta": round(relative_delta, 6),
                "max_method_score": round(max_method_score, 6),
                "max_relative_deviation": round(
                    float(pd.to_numeric(group["relative_deviation"]).max()),
                    6,
                ),
                "method_severity_hints": severity_hints,
                "detector_explanations": explanations,
            }
        )

    summary = pd.DataFrame(rows).merge(context, on="usage_date", how="left")
    summary["is_true_anomaly"] = summary["is_true_anomaly"].astype(int)
    summary["planned_event"] = summary["planned_event"].astype(int)
    return summary[config.ALERT_METHOD_SUMMARY_COLUMNS]


def _alert_reason(row: pd.Series) -> str:
    return (
        f"{row['alert_level'].title()} operational alert: "
        f"{int(row['method_count'])} detector(s) flagged an upward cost deviation "
        f"of {float(row['relative_delta']) * 100:.1f}%."
    )


def generate_alert_outputs(
    method_results: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return daily summaries, operational alerts, and planned suppressions."""
    summary = build_alert_method_summary(method_results, daily_features)
    alert_rows: list[dict[str, object]] = []
    suppressed_rows: list[dict[str, object]] = []

    for row in summary.itertuples(index=False):
        level = _candidate_level(
            int(row.method_count),
            float(row.relative_delta),
            str(row.method_severity_hints),
        )
        if level is None:
            continue
        if int(row.planned_event) == 1:
            suppressed_rows.append(
                {
                    "suppression_id": "",
                    "usage_date": row.usage_date,
                    "suppression_type": "explained_planned_event",
                    "methods_triggered": row.methods_triggered,
                    "method_count": int(row.method_count),
                    "actual_cost": float(row.actual_cost),
                    "expected_cost": float(row.expected_cost),
                    "relative_delta": float(row.relative_delta),
                    "planned_event_id": row.planned_event_ids,
                    "suppression_reason": (
                        "Detector candidate suppressed because the date belongs "
                        "to a cataloged planned usage event."
                    ),
                }
            )
            continue

        alert_row = {
            "alert_id": "",
            "usage_date": row.usage_date,
            "alert_level": level,
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
            "planned_event": 0,
            "top_service": row.top_service,
            "top_region": row.top_region,
        }
        alert_row["alert_reason"] = _alert_reason(pd.Series(alert_row))
        alert_rows.append(alert_row)

    alerts = pd.DataFrame(alert_rows, columns=config.ALERT_COLUMNS)
    suppressed = pd.DataFrame(
        suppressed_rows,
        columns=config.SUPPRESSED_ALERT_COLUMNS,
    )
    if not alerts.empty:
        alerts = alerts.sort_values("usage_date").reset_index(drop=True)
        alerts["alert_id"] = [
            f"ALERT-{index + 1:04d}" for index in range(len(alerts))
        ]
    if not suppressed.empty:
        suppressed = suppressed.sort_values("usage_date").reset_index(drop=True)
        suppressed["suppression_id"] = [
            f"SUPPRESSED-{index + 1:04d}" for index in range(len(suppressed))
        ]
    validate_alerts(alerts)
    validate_suppressed_alerts(suppressed)
    return summary, alerts, suppressed


def generate_alerts(
    method_results: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    """Compatibility helper returning only operational alerts."""
    return generate_alert_outputs(method_results, daily_features)[1]


def validate_alerts(alerts: pd.DataFrame) -> None:
    if list(alerts.columns) != config.ALERT_COLUMNS:
        raise ValueError("alerts columns do not match the required schema.")
    if alerts.empty:
        raise ValueError("At least one operational alert is required.")
    if alerts["alert_id"].duplicated().any() or alerts["usage_date"].duplicated().any():
        raise ValueError("Operational alert IDs and dates must be unique.")
    if not set(alerts["alert_level"]).issubset(ALLOWED_ALERT_LEVELS):
        raise ValueError("alert_level must be warning or critical.")
    if (alerts["planned_event"] != 0).any():
        raise ValueError("Planned-event candidates must not be operational alerts.")
    if (alerts["relative_delta"] < config.ALERT_WARNING_RELATIVE_DELTA).any():
        raise ValueError("Operational alerts must meet the warning deviation floor.")
    critical = alerts[alerts["alert_level"] == "critical"]
    if not critical.empty:
        if (
            critical["relative_delta"] < config.ALERT_CRITICAL_RELATIVE_DELTA
        ).any():
            raise ValueError("Critical alerts must meet the critical deviation floor.")
        if (
            critical["method_count"] < config.ALERT_CRITICAL_MIN_METHODS
        ).any():
            raise ValueError("Critical alerts require strong method agreement.")


def validate_suppressed_alerts(suppressed: pd.DataFrame) -> None:
    if list(suppressed.columns) != config.SUPPRESSED_ALERT_COLUMNS:
        raise ValueError("suppressed_alerts columns do not match the schema.")
    if suppressed.empty:
        return
    if suppressed["suppression_id"].duplicated().any():
        raise ValueError("suppression_id must be unique.")
    if (suppressed["planned_event_id"].astype(str).str.strip() == "").any():
        raise ValueError("Suppressed planned candidates require planned_event_id.")


def run_alert_generation() -> dict[str, Path]:
    method_results = load_method_results()
    daily_features = _load_daily_features()
    summary, alerts, suppressed = generate_alert_outputs(
        method_results,
        daily_features,
    )
    config.OUTPUTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(config.ALERT_METHOD_SUMMARY_PATH, index=False)
    alerts.to_csv(config.ALERTS_PATH, index=False)
    suppressed.to_csv(config.SUPPRESSED_ALERTS_PATH, index=False)
    return {
        "alert_method_summary": config.ALERT_METHOD_SUMMARY_PATH,
        "alerts": config.ALERTS_PATH,
        "suppressed_alerts": config.SUPPRESSED_ALERTS_PATH,
    }


def main() -> None:
    paths = run_alert_generation()
    print("Alert generation complete.")
    for path in paths.values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
