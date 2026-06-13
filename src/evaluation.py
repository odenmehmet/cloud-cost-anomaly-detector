"""Day-level and event-level evaluation for detectors and operational alerts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # Allows: python src/evaluation.py
    import config  # type: ignore


PREDICTION_COLUMNS = {
    "zscore": "zscore_pred",
    "stl": "stl_pred",
    "isolation_forest": "isolation_forest_pred",
    "raw_alert_candidate": "raw_alert_candidate_pred",
    "agreement_alert": "agreement_alert_pred",
}


def _iso_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="raise").dt.date.astype(str)


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _split_anomaly_types(value: object) -> list[str]:
    if pd.isna(value):
        return []
    normalized = str(value).replace("|", ",").replace(";", ",")
    return [
        item.strip()
        for item in normalized.split(",")
        if item.strip() and item.strip() != "none"
    ]


def load_evaluation_inputs() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    required_paths = [
        config.DAILY_FEATURES_PATH,
        config.METHOD_RESULTS_PATH,
        config.ALERTS_PATH,
        config.SUPPRESSED_ALERTS_PATH,
        config.ANOMALY_CATALOG_PATH,
    ]
    for path in required_paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"Evaluation input not found: {path}")

    daily_features = pd.read_csv(config.DAILY_FEATURES_PATH)
    method_results = pd.read_csv(config.METHOD_RESULTS_PATH)
    alerts = pd.read_csv(config.ALERTS_PATH)
    suppressed = pd.read_csv(config.SUPPRESSED_ALERTS_PATH)
    anomaly_catalog = pd.read_csv(config.ANOMALY_CATALOG_PATH)

    for frame, column in [
        (daily_features, "usage_date"),
        (method_results, "usage_date"),
        (alerts, "usage_date"),
        (suppressed, "usage_date"),
        (anomaly_catalog, "start_date"),
        (anomaly_catalog, "end_date"),
    ]:
        if column in frame.columns and not frame.empty:
            frame[column] = _iso_date_series(frame[column])
    return daily_features, method_results, alerts, suppressed, anomaly_catalog


def build_daily_prediction_table(
    daily_features: pd.DataFrame,
    method_results: pd.DataFrame,
    alerts: pd.DataFrame,
    suppressed_alerts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build daily truth, raw detector flags, candidates, and final alerts."""
    required = {
        "usage_date",
        "is_anomaly",
        "anomaly_types",
        "planned_event",
        "planned_event_ids",
    }
    missing = required - set(daily_features.columns)
    if missing:
        raise ValueError(f"daily_features missing columns: {sorted(missing)}")

    daily = daily_features.sort_values("usage_date").reset_index(drop=True).copy()
    daily["usage_date"] = _iso_date_series(daily["usage_date"])
    daily["is_anomaly"] = daily["is_anomaly"].astype(int)
    daily["planned_event"] = daily["planned_event"].astype(int)
    predictions = daily[
        [
            "usage_date",
            "is_anomaly",
            "anomaly_types",
            "planned_event",
            "planned_event_ids",
        ]
    ].copy()

    for subject in ["zscore", "stl", "isolation_forest"]:
        subject_rows = method_results[method_results["method"] == subject]
        dates = set(subject_rows.loc[subject_rows["is_flagged"] == 1, "usage_date"])
        predictions[PREDICTION_COLUMNS[subject]] = (
            predictions["usage_date"].isin(dates).astype(int)
        )

    alert_dates = set(alerts["usage_date"])
    suppressed_dates = (
        set(suppressed_alerts["usage_date"])
        if suppressed_alerts is not None and not suppressed_alerts.empty
        else set()
    )
    predictions["raw_alert_candidate_pred"] = (
        predictions["usage_date"].isin(alert_dates | suppressed_dates).astype(int)
    )
    predictions["agreement_alert_pred"] = (
        predictions["usage_date"].isin(alert_dates).astype(int)
    )
    predictions = predictions[config.EVALUATION_DAILY_PREDICTION_COLUMNS]
    if len(predictions) != config.NUM_DAYS:
        raise ValueError(f"Daily prediction table must contain {config.NUM_DAYS} rows.")
    return predictions


def compute_binary_counts(y_true: pd.Series, y_pred: pd.Series) -> dict[str, int]:
    truth = pd.to_numeric(y_true, errors="raise").astype(int)
    predicted = pd.to_numeric(y_pred, errors="raise").astype(int)
    return {
        "true_positives": int(((truth == 1) & (predicted == 1)).sum()),
        "false_positives": int(((truth == 0) & (predicted == 1)).sum()),
        "true_negatives": int(((truth == 0) & (predicted == 0)).sum()),
        "false_negatives": int(((truth == 1) & (predicted == 0)).sum()),
    }


def compute_precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def _summary_row(
    subject: str,
    matching_mode: str,
    total_days: int,
    true_anomaly_days: int,
    predicted_positive_days: int,
    counts: dict[str, int],
) -> dict[str, Any]:
    metrics = compute_precision_recall_f1(
        counts["true_positives"],
        counts["false_positives"],
        counts["false_negatives"],
    )
    return {
        "subject": subject,
        "matching_mode": matching_mode,
        "total_days": total_days,
        "true_anomaly_days": true_anomaly_days,
        "predicted_positive_days": predicted_positive_days,
        **counts,
        **metrics,
        "false_positives_per_30_days": round(
            _safe_divide(counts["false_positives"] * 30, total_days),
            6,
        ),
    }


def _match_with_tolerance(
    true_dates: list[pd.Timestamp],
    predicted_dates: list[pd.Timestamp],
    tolerance_days: int = 1,
) -> tuple[int, int, int]:
    """One prediction can match at most one true day."""
    sorted_true = sorted(true_dates)
    unmatched = set(range(len(sorted_true)))
    matches = 0
    for predicted_date in sorted(predicted_dates):
        candidates = [
            (abs((predicted_date - sorted_true[index]).days), index)
            for index in unmatched
            if abs((predicted_date - sorted_true[index]).days) <= tolerance_days
        ]
        if candidates:
            _, matched_index = min(candidates)
            unmatched.remove(matched_index)
            matches += 1
    return matches, len(predicted_dates) - matches, len(true_dates) - matches


def compute_evaluation_summary(daily_predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total_days = len(daily_predictions)
    true_days = int(daily_predictions["is_anomaly"].sum())
    true_dates = pd.to_datetime(
        daily_predictions.loc[daily_predictions["is_anomaly"] == 1, "usage_date"]
    ).tolist()

    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        exact_counts = compute_binary_counts(
            daily_predictions["is_anomaly"],
            daily_predictions[pred_col],
        )
        predicted_dates = pd.to_datetime(
            daily_predictions.loc[daily_predictions[pred_col] == 1, "usage_date"]
        ).tolist()
        rows.append(
            _summary_row(
                subject,
                "exact_day",
                total_days,
                true_days,
                len(predicted_dates),
                exact_counts,
            )
        )
        tp, fp, fn = _match_with_tolerance(true_dates, predicted_dates)
        rows.append(
            _summary_row(
                subject,
                "tolerance_1_day",
                total_days,
                true_days,
                len(predicted_dates),
                {
                    "true_positives": tp,
                    "false_positives": fp,
                    "true_negatives": total_days - tp - fp - fn,
                    "false_negatives": fn,
                },
            )
        )
    return pd.DataFrame(rows, columns=config.EVALUATION_SUMMARY_COLUMNS).sort_values(
        ["subject", "matching_mode"]
    ).reset_index(drop=True)


def compute_evaluation_by_type(daily_predictions: pd.DataFrame) -> pd.DataFrame:
    type_dates: dict[str, list[pd.Timestamp]] = {}
    for row in daily_predictions[daily_predictions["is_anomaly"] == 1].itertuples(
        index=False
    ):
        for anomaly_type in _split_anomaly_types(row.anomaly_types):
            type_dates.setdefault(anomaly_type, []).append(pd.Timestamp(row.usage_date))

    rows: list[dict[str, Any]] = []
    for subject in config.EVALUATION_SUBJECTS:
        predicted_dates = pd.to_datetime(
            daily_predictions.loc[
                daily_predictions[PREDICTION_COLUMNS[subject]] == 1,
                "usage_date",
            ]
        ).tolist()
        predicted_set = set(predicted_dates)
        for anomaly_type, anomaly_dates in sorted(type_dates.items()):
            exact = sum(date in predicted_set for date in anomaly_dates)
            tolerant, _, _ = _match_with_tolerance(
                anomaly_dates,
                predicted_dates,
                tolerance_days=1,
            )
            true_days = len(anomaly_dates)
            rows.append(
                {
                    "subject": subject,
                    "anomaly_type": anomaly_type,
                    "true_days": true_days,
                    "detected_days_exact": exact,
                    "detected_days_tolerance_1_day": tolerant,
                    "recall_exact": round(_safe_divide(exact, true_days), 6),
                    "recall_tolerance_1_day": round(
                        _safe_divide(tolerant, true_days),
                        6,
                    ),
                }
            )
    return pd.DataFrame(rows, columns=config.EVALUATION_BY_TYPE_COLUMNS).sort_values(
        ["subject", "anomaly_type"]
    ).reset_index(drop=True)


def _prediction_runs(dates: list[pd.Timestamp]) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if not dates:
        return []
    sorted_dates = sorted(set(dates))
    runs: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = previous = sorted_dates[0]
    for date in sorted_dates[1:]:
        if (date - previous).days > 1:
            runs.append((start, previous))
            start = date
        previous = date
    runs.append((start, previous))
    return runs


def _match_event_runs(
    anomaly_catalog: pd.DataFrame,
    predicted_dates: list[pd.Timestamp],
    tolerance_days: int,
) -> tuple[int, int, int]:
    events = [
        (
            pd.Timestamp(row.start_date) - pd.Timedelta(days=tolerance_days),
            pd.Timestamp(row.end_date) + pd.Timedelta(days=tolerance_days),
        )
        for row in anomaly_catalog.sort_values("start_date").itertuples(index=False)
    ]
    runs = _prediction_runs(predicted_dates)
    unmatched_events = set(range(len(events)))
    detected = 0
    for run_start, run_end in runs:
        matches = [
            index
            for index in unmatched_events
            if run_start <= events[index][1] and run_end >= events[index][0]
        ]
        if matches:
            matched = min(matches, key=lambda index: events[index][0])
            unmatched_events.remove(matched)
            detected += 1
    return detected, len(runs) - detected, len(events) - detected


def compute_event_level_evaluation(
    daily_predictions: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in config.EVALUATION_SUBJECTS:
        predicted_dates = pd.to_datetime(
            daily_predictions.loc[
                daily_predictions[PREDICTION_COLUMNS[subject]] == 1,
                "usage_date",
            ]
        ).tolist()
        predicted_events = len(_prediction_runs(predicted_dates))
        for mode, tolerance in [("event_window", 0), ("event_window_tolerance_1_day", 1)]:
            detected, false_events, missed = _match_event_runs(
                anomaly_catalog,
                predicted_dates,
                tolerance,
            )
            metrics = compute_precision_recall_f1(
                detected,
                false_events,
                missed,
            )
            rows.append(
                {
                    "subject": subject,
                    "matching_mode": mode,
                    "true_events": len(anomaly_catalog),
                    "predicted_events": predicted_events,
                    "detected_events": detected,
                    "false_positive_events": false_events,
                    "missed_events": missed,
                    "event_precision": metrics["precision"],
                    "event_recall": metrics["recall"],
                    "event_f1": metrics["f1"],
                }
            )
    return pd.DataFrame(
        rows,
        columns=config.EVENT_LEVEL_EVALUATION_COLUMNS,
    ).sort_values(["subject", "matching_mode"]).reset_index(drop=True)


def compute_detection_delay(
    daily_predictions: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject in config.EVALUATION_SUBJECTS:
        predicted_dates = sorted(
            pd.to_datetime(
                daily_predictions.loc[
                    daily_predictions[PREDICTION_COLUMNS[subject]] == 1,
                    "usage_date",
                ]
            ).tolist()
        )
        for event in anomaly_catalog.sort_values("start_date").itertuples(index=False):
            start = pd.Timestamp(event.start_date)
            end = pd.Timestamp(event.end_date)
            in_window = [date for date in predicted_dates if start <= date <= end]
            first = min(in_window) if in_window else None
            rows.append(
                {
                    "subject": subject,
                    "anomaly_id": event.anomaly_id,
                    "anomaly_type": event.anomaly_type,
                    "start_date": start.date().isoformat(),
                    "end_date": end.date().isoformat(),
                    "detected": int(first is not None),
                    "first_detection_date": (
                        first.date().isoformat() if first is not None else ""
                    ),
                    "detection_delay_days": (
                        int((first - start).days) if first is not None else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows, columns=config.DETECTION_DELAY_COLUMNS).sort_values(
        ["subject", "start_date", "anomaly_id"]
    ).reset_index(drop=True)


def compute_false_positive_days(
    daily_predictions: pd.DataFrame,
    method_results: pd.DataFrame,
    alerts: pd.DataFrame,
    suppressed_alerts: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    context = daily_features[
        ["usage_date", "anomaly_types", "planned_event"]
    ].set_index("usage_date")
    method_index = method_results.set_index(["method", "usage_date"])
    alerts_by_date = alerts.set_index("usage_date")
    suppressed_by_date = suppressed_alerts.set_index("usage_date")
    rows: list[dict[str, Any]] = []

    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        fp_dates = daily_predictions.loc[
            (daily_predictions[pred_col] == 1)
            & (daily_predictions["is_anomaly"] == 0),
            "usage_date",
        ]
        for usage_date in fp_dates:
            planned = int(context.loc[usage_date, "planned_event"])
            if subject in {"zscore", "stl", "isolation_forest"}:
                source = method_index.loc[(subject, usage_date)]
                prediction_source = "method_results"
                alert_level = ""
                methods_triggered = ""
                actual_cost = float(source["actual_cost"])
                expected_cost = float(source["expected_cost"])
                relative_delta = float(source["relative_deviation"])
            elif usage_date in alerts_by_date.index:
                source = alerts_by_date.loc[usage_date]
                prediction_source = "alerts"
                alert_level = source["alert_level"]
                methods_triggered = source["methods_triggered"]
                actual_cost = float(source["actual_cost"])
                expected_cost = float(source["expected_cost"])
                relative_delta = float(source["relative_delta"])
            else:
                source = suppressed_by_date.loc[usage_date]
                prediction_source = "suppressed_alerts"
                alert_level = "suppressed"
                methods_triggered = source["methods_triggered"]
                actual_cost = float(source["actual_cost"])
                expected_cost = float(source["expected_cost"])
                relative_delta = float(source["relative_delta"])

            rows.append(
                {
                    "subject": subject,
                    "usage_date": usage_date,
                    "prediction_source": prediction_source,
                    "planned_event": planned,
                    "anomaly_type": context.loc[usage_date, "anomaly_types"],
                    "alert_level": alert_level,
                    "methods_triggered": methods_triggered,
                    "actual_cost": round(actual_cost, 4),
                    "expected_cost": round(expected_cost, 4),
                    "relative_delta": round(relative_delta, 6),
                    "reason": (
                        "Prediction occurred during a cataloged planned event."
                        if planned
                        else "Prediction occurred on a non-anomaly day."
                    ),
                }
            )
    return pd.DataFrame(rows, columns=config.FALSE_POSITIVE_DAYS_COLUMNS).sort_values(
        ["subject", "usage_date"]
    ).reset_index(drop=True)


def validate_evaluation_outputs(
    evaluation_summary: pd.DataFrame,
    evaluation_by_type: pd.DataFrame,
    event_level_evaluation: pd.DataFrame,
    detection_delay: pd.DataFrame,
    false_positive_days: pd.DataFrame,
    daily_predictions: pd.DataFrame,
) -> None:
    if list(evaluation_summary.columns) != config.EVALUATION_SUMMARY_COLUMNS:
        raise ValueError("evaluation_summary columns do not match the schema.")
    expected_summary_rows = len(config.EVALUATION_SUBJECTS) * len(
        config.EVALUATION_MATCHING_MODES
    )
    if len(evaluation_summary) != expected_summary_rows:
        raise ValueError("evaluation_summary row count is incorrect.")
    for metric in ["precision", "recall", "f1"]:
        if not evaluation_summary[metric].between(0, 1).all():
            raise ValueError(f"{metric} must be between 0 and 1.")
    if list(event_level_evaluation.columns) != config.EVENT_LEVEL_EVALUATION_COLUMNS:
        raise ValueError("event_level_evaluation columns do not match the schema.")
    expected_event_rows = len(config.EVALUATION_SUBJECTS) * len(
        config.EVENT_MATCHING_MODES
    )
    if len(event_level_evaluation) != expected_event_rows:
        raise ValueError("event_level_evaluation row count is incorrect.")
    for metric in ["event_precision", "event_recall", "event_f1"]:
        if not event_level_evaluation[metric].between(0, 1).all():
            raise ValueError(f"{metric} must be between 0 and 1.")
    if list(evaluation_by_type.columns) != config.EVALUATION_BY_TYPE_COLUMNS:
        raise ValueError("evaluation_by_type columns do not match the schema.")
    if list(detection_delay.columns) != config.DETECTION_DELAY_COLUMNS:
        raise ValueError("detection_delay columns do not match the schema.")
    if list(false_positive_days.columns) != config.FALSE_POSITIVE_DAYS_COLUMNS:
        raise ValueError("false_positive_days columns do not match the schema.")
    if list(daily_predictions.columns) != config.EVALUATION_DAILY_PREDICTION_COLUMNS:
        raise ValueError("daily prediction columns do not match the schema.")


def save_evaluation_reports(
    evaluation_summary: pd.DataFrame,
    evaluation_by_type: pd.DataFrame,
    event_level_evaluation: pd.DataFrame,
    detection_delay: pd.DataFrame,
    false_positive_days: pd.DataFrame,
    daily_predictions: pd.DataFrame,
) -> dict[str, Path]:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "evaluation_summary": (evaluation_summary, config.EVALUATION_SUMMARY_PATH),
        "evaluation_by_type": (evaluation_by_type, config.EVALUATION_BY_TYPE_PATH),
        "event_level_evaluation": (
            event_level_evaluation,
            config.EVENT_LEVEL_EVALUATION_PATH,
        ),
        "detection_delay": (detection_delay, config.DETECTION_DELAY_PATH),
        "false_positive_days": (
            false_positive_days,
            config.FALSE_POSITIVE_DAYS_PATH,
        ),
        "evaluation_daily_predictions": (
            daily_predictions,
            config.EVALUATION_DAILY_PREDICTIONS_PATH,
        ),
    }
    for frame, path in outputs.values():
        frame.to_csv(path, index=False)
    return {name: path for name, (_, path) in outputs.items()}


def run_evaluation() -> dict[str, Any]:
    (
        daily_features,
        method_results,
        alerts,
        suppressed_alerts,
        anomaly_catalog,
    ) = load_evaluation_inputs()
    daily_predictions = build_daily_prediction_table(
        daily_features,
        method_results,
        alerts,
        suppressed_alerts,
    )
    evaluation_summary = compute_evaluation_summary(daily_predictions)
    evaluation_by_type = compute_evaluation_by_type(daily_predictions)
    event_level_evaluation = compute_event_level_evaluation(
        daily_predictions,
        anomaly_catalog,
    )
    detection_delay = compute_detection_delay(daily_predictions, anomaly_catalog)
    false_positive_days = compute_false_positive_days(
        daily_predictions,
        method_results,
        alerts,
        suppressed_alerts,
        daily_features,
    )
    validate_evaluation_outputs(
        evaluation_summary,
        evaluation_by_type,
        event_level_evaluation,
        detection_delay,
        false_positive_days,
        daily_predictions,
    )
    paths = save_evaluation_reports(
        evaluation_summary,
        evaluation_by_type,
        event_level_evaluation,
        detection_delay,
        false_positive_days,
        daily_predictions,
    )
    return {
        "paths": paths,
        "evaluation_summary": evaluation_summary,
        "evaluation_by_type": evaluation_by_type,
        "event_level_evaluation": event_level_evaluation,
        "detection_delay": detection_delay,
        "false_positive_days": false_positive_days,
        "daily_predictions": daily_predictions,
    }


def main() -> None:
    result = run_evaluation()
    print("Evaluation complete.")
    for path in result["paths"].values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
