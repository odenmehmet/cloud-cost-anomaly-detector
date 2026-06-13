"""Small, transparent detector sensitivity sweep on synthetic labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from . import config
from .detectors.isolation_forest import build_isolation_forest_results
from .detectors.stl import build_stl_outputs
from .detectors.zscore import build_zscore_results


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _candidate_metrics(
    results: pd.DataFrame,
    daily_features: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
) -> dict[str, float | int]:
    merged = daily_features[["usage_date", "is_anomaly"]].merge(
        results[["usage_date", "is_flagged"]],
        on="usage_date",
        how="left",
        validate="one_to_one",
    )
    truth = merged["is_anomaly"].astype(int)
    predicted = merged["is_flagged"].astype(int)
    tp = int(((truth == 1) & (predicted == 1)).sum())
    fp = int(((truth == 0) & (predicted == 1)).sum())
    fn = int(((truth == 1) & (predicted == 0)).sum())
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)

    predicted_dates = set(results.loc[results["is_flagged"] == 1, "usage_date"])
    detected_events = 0
    for event in anomaly_catalog.itertuples(index=False):
        event_dates = set(
            pd.date_range(event.start_date, event.end_date).strftime("%Y-%m-%d")
        )
        if predicted_dates & event_dates:
            detected_events += 1
    event_recall = _safe_divide(detected_events, len(anomaly_catalog))

    # Day-level F1 remains primary; event recall keeps long-window events from
    # being ignored by a candidate that only catches isolated spikes.
    selection_score = (0.75 * f1) + (0.25 * event_recall)
    return {
        "predicted_positive_days": int(predicted.sum()),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "event_recall": round(event_recall, 6),
        "selection_score": round(selection_score, 6),
    }


def _choose_selected(rows: list[dict[str, Any]], method: str) -> str:
    method_rows = [row for row in rows if row["method"] == method]
    selected = max(
        method_rows,
        key=lambda row: (
            row["selection_score"],
            row["precision"],
            row["recall"],
            -row["predicted_positive_days"],
            row["candidate_id"],
        ),
    )
    return str(selected["candidate_id"])


def run_calibration(
    daily_features: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
    output_path: Path = config.CALIBRATION_SUMMARY_PATH,
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    """Run bounded candidate grids and return selected detector settings."""
    rows: list[dict[str, Any]] = []
    settings_by_candidate: dict[str, dict[str, Any]] = {}

    def add_candidate(
        method: str,
        candidate_id: str,
        parameters: dict[str, Any],
        builder: Callable[[], pd.DataFrame],
    ) -> None:
        results = builder()
        metrics = _candidate_metrics(results, daily_features, anomaly_catalog)
        rows.append(
            {
                "method": method,
                "candidate_id": candidate_id,
                "parameters": json.dumps(parameters, sort_keys=True),
                **metrics,
                "selected": 0,
            }
        )
        settings_by_candidate[candidate_id] = parameters

    for window in config.CALIBRATION_ZSCORE_WINDOWS:
        for threshold in config.CALIBRATION_ZSCORE_THRESHOLDS:
            candidate_id = f"zscore-w{window}-t{threshold:.1f}"
            parameters = {
                "rolling_window": window,
                "min_periods": config.ZSCORE_MIN_PERIODS,
                "z_threshold": threshold,
            }
            add_candidate(
                "zscore",
                candidate_id,
                parameters,
                lambda parameters=parameters: build_zscore_results(
                    daily_features,
                    **parameters,
                ),
            )

    for threshold in config.CALIBRATION_STL_THRESHOLDS:
        candidate_id = f"stl-p{config.STL_PERIOD}-t{threshold:.1f}"
        parameters = {
            "period": config.STL_PERIOD,
            "residual_threshold": threshold,
        }
        add_candidate(
            "stl",
            candidate_id,
            parameters,
            lambda parameters=parameters: build_stl_outputs(
                daily_features,
                **parameters,
            )[0],
        )

    for contamination in config.CALIBRATION_ISOLATION_CONTAMINATIONS:
        candidate_id = f"isolation-c{contamination:.2f}"
        parameters = {
            "n_estimators": config.ISOLATION_FOREST_N_ESTIMATORS,
            "contamination": contamination,
            "random_state": config.DEFAULT_RANDOM_SEED,
        }
        add_candidate(
            "isolation_forest",
            candidate_id,
            parameters,
            lambda parameters=parameters: build_isolation_forest_results(
                daily_features,
                **parameters,
            ),
        )

    selected_ids = {
        method: _choose_selected(rows, method)
        for method in ["zscore", "stl", "isolation_forest"]
    }
    for row in rows:
        row["selected"] = int(selected_ids[row["method"]] == row["candidate_id"])

    summary = pd.DataFrame(rows, columns=config.CALIBRATION_SUMMARY_COLUMNS)
    summary = summary.sort_values(["method", "candidate_id"]).reset_index(drop=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False)
    selected_settings = {
        method: settings_by_candidate[candidate_id]
        for method, candidate_id in selected_ids.items()
    }
    return selected_settings, summary
