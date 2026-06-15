"""Evaluate the fixed main detector configuration across synthetic seeds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config
from .alerts import generate_alert_outputs
from .data_generator import generate_synthetic_dataset
from .detectors.isolation_forest import build_isolation_forest_results
from .detectors.stl import build_stl_outputs
from .detectors.zscore import build_zscore_results
from .evaluation import (
    build_daily_prediction_table,
    compute_evaluation_summary,
    compute_event_level_evaluation,
)
from .features import build_daily_features
from .preprocessing import (
    build_daily_region_cost,
    build_daily_service_cost,
    build_daily_total_cost,
)


SCENARIOS = [
    ("seed_42_main", config.DEFAULT_RANDOM_SEED),
    ("seed_7", 7),
    ("seed_21", 21),
    ("seed_84", 84),
    ("seed_126", 126),
]
CALIBRATION_MODE = "fixed_main_scenario"


def load_main_detector_settings(
    calibration_path: Path = config.CALIBRATION_SUMMARY_PATH,
) -> dict[str, dict[str, Any]]:
    """Load the one selected setting per detector from the main scenario."""
    calibration_path = Path(calibration_path)
    if not calibration_path.exists():
        raise FileNotFoundError(
            "Main calibration output is missing. Run python run_pipeline.py first: "
            f"{calibration_path}"
        )

    calibration = pd.read_csv(calibration_path)
    required = {"method", "parameters", "selected"}
    missing = sorted(required - set(calibration.columns))
    if missing:
        raise ValueError(f"Calibration summary is missing columns: {missing}")

    selected = calibration[calibration["selected"] == 1]
    expected_methods = {"zscore", "stl", "isolation_forest"}
    if set(selected["method"]) != expected_methods:
        raise ValueError("Main calibration must select all three detectors.")
    if not (selected.groupby("method").size() == 1).all():
        raise ValueError("Main calibration must select one setting per detector.")

    return {
        str(row.method): json.loads(str(row.parameters))
        for row in selected.itertuples(index=False)
    }


def _build_method_results(
    daily_features: pd.DataFrame,
    settings: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    zscore = build_zscore_results(daily_features, **settings["zscore"])
    stl, _ = build_stl_outputs(daily_features, **settings["stl"])
    isolation = build_isolation_forest_results(
        daily_features,
        **settings["isolation_forest"],
    )
    return (
        pd.concat([zscore, stl, isolation], ignore_index=True)
        .sort_values(["usage_date", "method"])
        .reset_index(drop=True)
    )


def _single_metric_row(
    frame: pd.DataFrame,
    subject: str,
    matching_mode: str,
) -> pd.Series:
    rows = frame[
        (frame["subject"] == subject)
        & (frame["matching_mode"] == matching_mode)
    ]
    if len(rows) != 1:
        raise ValueError(
            f"Expected one {subject}/{matching_mode} metric row, found {len(rows)}."
        )
    return rows.iloc[0]


def evaluate_scenario(
    scenario_id: str,
    random_seed: int,
    detector_settings: dict[str, dict[str, Any]],
) -> dict[str, object]:
    """Run one synthetic seed fully in memory and return final-alert metrics."""
    generated = generate_synthetic_dataset(
        seed=random_seed,
        write_files=False,
        verbose=False,
    )
    raw = generated["cur_like"]
    daily_total = build_daily_total_cost(raw)
    daily_service = build_daily_service_cost(raw)
    daily_region = build_daily_region_cost(raw)
    daily_features = build_daily_features(
        daily_total,
        daily_service,
        daily_region,
    )
    method_results = _build_method_results(daily_features, detector_settings)
    _, alerts, suppressed = generate_alert_outputs(
        method_results,
        daily_features,
    )
    daily_predictions = build_daily_prediction_table(
        daily_features,
        method_results,
        alerts,
        suppressed,
    )
    day_metrics = _single_metric_row(
        compute_evaluation_summary(daily_predictions),
        "agreement_alert",
        "exact_day",
    )
    event_metrics = _single_metric_row(
        compute_event_level_evaluation(
            daily_predictions,
            generated["anomaly_catalog"],
        ),
        "agreement_alert",
        "event_window",
    )

    return {
        "scenario_id": scenario_id,
        "random_seed": random_seed,
        "calibration_mode": CALIBRATION_MODE,
        "true_anomaly_days": int(daily_features["is_anomaly"].sum()),
        "true_anomaly_events": int(len(generated["anomaly_catalog"])),
        "operational_alerts": int(len(alerts)),
        "suppressed_planned_candidates": int(len(suppressed)),
        "operational_precision": float(day_metrics["precision"]),
        "operational_recall": float(day_metrics["recall"]),
        "operational_f1": float(day_metrics["f1"]),
        "operational_false_positives_per_30_days": float(
            day_metrics["false_positives_per_30_days"]
        ),
        "event_precision": float(event_metrics["event_precision"]),
        "event_recall": float(event_metrics["event_recall"]),
        "event_f1": float(event_metrics["event_f1"]),
    }


def validate_scenario_robustness(results: pd.DataFrame) -> None:
    """Validate the deterministic scenario report contract."""
    if list(results.columns) != config.SCENARIO_ROBUSTNESS_COLUMNS:
        raise ValueError("Scenario robustness columns do not match the schema.")
    if len(results) != len(SCENARIOS):
        raise ValueError("Scenario robustness row count is incorrect.")
    if results["scenario_id"].duplicated().any():
        raise ValueError("Scenario IDs must be unique.")
    if results["random_seed"].duplicated().any():
        raise ValueError("Scenario seeds must be unique.")
    scenario_pairs = set(
        results[["scenario_id", "random_seed"]].itertuples(index=False, name=None)
    )
    if scenario_pairs != set(SCENARIOS):
        raise ValueError("Scenario IDs and seeds do not match the declared scenarios.")
    if set(results["calibration_mode"]) != {CALIBRATION_MODE}:
        raise ValueError("All scenarios must use the fixed main calibration.")

    metric_columns = [
        "operational_precision",
        "operational_recall",
        "operational_f1",
        "event_precision",
        "event_recall",
        "event_f1",
    ]
    metrics_in_range = results[metric_columns].apply(
        lambda column: column.between(0, 1)
    )
    if not metrics_in_range.all().all():
        raise ValueError("Scenario robustness metrics must be between 0 and 1.")
    numeric = results.drop(columns=["scenario_id", "calibration_mode"]).apply(
        pd.to_numeric,
        errors="raise",
    )
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Scenario robustness contains non-finite values.")


def run_scenario_robustness(
    output_path: Path = config.SCENARIO_ROBUSTNESS_PATH,
) -> pd.DataFrame:
    """Evaluate all predeclared seeds and write only the robustness report."""
    detector_settings = load_main_detector_settings()
    results = pd.DataFrame(
        [
            evaluate_scenario(scenario_id, seed, detector_settings)
            for scenario_id, seed in SCENARIOS
        ],
        columns=config.SCENARIO_ROBUSTNESS_COLUMNS,
    )
    validate_scenario_robustness(results)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
    return results


def main() -> None:
    results = run_scenario_robustness()
    print("Scenario robustness evaluation complete.")
    print(results.to_string(index=False))
    print(f"- {config.SCENARIO_ROBUSTNESS_PATH}")


if __name__ == "__main__":
    main()
