"""
Evaluation metrics for detector and alert outputs.

Phase 6 scope only:
- exact-day and +/-1 day tolerant matching
- precision, recall, F1, false positives per 30 days
- recall by anomaly type
- event-level detection delay
- false-positive day listing
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
except ImportError:  # Allows: python src/evaluation.py
    import config  # type: ignore


PREDICTION_COLUMNS = {
    "zscore": "zscore_pred",
    "stl": "stl_pred",
    "isolation_forest": "isolation_forest_pred",
    "agreement_alert": "agreement_alert_pred",
}


def _iso_date_series(series: pd.Series) -> pd.Series:
    """Convert a date-like series to ISO date strings."""
    return pd.to_datetime(series, errors="raise").dt.date.astype(str)


def _safe_divide(numerator: float, denominator: float) -> float:
    """Safely divide two numbers, returning 0.0 for a zero denominator."""
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _split_anomaly_types(value: object) -> list[str]:
    """Split anomaly type strings that may use pipe, comma, or semicolon separators."""
    if pd.isna(value):
        return []
    normalized = str(value).replace("|", ",").replace(";", ",")
    return [
        item.strip()
        for item in normalized.split(",")
        if item.strip() and item.strip() != "none"
    ]


def load_evaluation_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load daily labels, method outputs, alerts, and anomaly catalog inputs."""
    required_paths = [
        config.DAILY_FEATURES_PATH,
        config.METHOD_RESULTS_PATH,
        config.ALERTS_PATH,
        config.ANOMALY_CATALOG_PATH,
    ]
    for path in required_paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"Evaluation input not found: {path}")

    daily_features = pd.read_csv(config.DAILY_FEATURES_PATH)
    method_results = pd.read_csv(config.METHOD_RESULTS_PATH)
    alerts = pd.read_csv(config.ALERTS_PATH)
    anomaly_catalog = pd.read_csv(config.ANOMALY_CATALOG_PATH)

    daily_features["usage_date"] = _iso_date_series(daily_features["usage_date"])
    method_results["usage_date"] = _iso_date_series(method_results["usage_date"])
    alerts["usage_date"] = _iso_date_series(alerts["usage_date"])
    anomaly_catalog["start_date"] = _iso_date_series(anomaly_catalog["start_date"])
    anomaly_catalog["end_date"] = _iso_date_series(anomaly_catalog["end_date"])

    return daily_features, method_results, alerts, anomaly_catalog


def build_daily_prediction_table(
    daily_features: pd.DataFrame,
    method_results: pd.DataFrame,
    alerts: pd.DataFrame,
) -> pd.DataFrame:
    """Build one daily table containing ground truth and all prediction subjects."""
    required_daily_columns = {
        "usage_date",
        "is_anomaly",
        "anomaly_types",
        "planned_event",
    }
    missing_daily_columns = required_daily_columns - set(daily_features.columns)
    if missing_daily_columns:
        raise ValueError(f"daily_features missing columns: {sorted(missing_daily_columns)}")

    daily = daily_features.copy().sort_values("usage_date").reset_index(drop=True)
    daily["usage_date"] = _iso_date_series(daily["usage_date"])
    daily["is_anomaly"] = pd.to_numeric(daily["is_anomaly"], errors="raise").astype(int)
    daily["planned_event"] = pd.to_numeric(
        daily["planned_event"],
        errors="raise",
    ).astype(int)

    prediction_table = daily[
        ["usage_date", "is_anomaly", "anomaly_types", "planned_event"]
    ].copy()

    for subject in ["zscore", "stl", "isolation_forest"]:
        subject_rows = method_results[method_results["method"] == subject]
        predicted_dates = set(
            subject_rows.loc[subject_rows["is_flagged"] == 1, "usage_date"]
        )
        prediction_table[PREDICTION_COLUMNS[subject]] = (
            prediction_table["usage_date"].isin(predicted_dates).astype(int)
        )

    alert_dates = set(alerts["usage_date"])
    prediction_table["agreement_alert_pred"] = (
        prediction_table["usage_date"].isin(alert_dates).astype(int)
    )

    prediction_table = prediction_table[config.EVALUATION_DAILY_PREDICTION_COLUMNS]
    if len(prediction_table) != config.NUM_DAYS:
        raise ValueError(f"Daily prediction table must contain {config.NUM_DAYS} rows.")
    return prediction_table


def compute_binary_counts(y_true: pd.Series, y_pred: pd.Series) -> dict[str, int]:
    """Compute exact-day binary confusion counts."""
    true_values = pd.to_numeric(y_true, errors="raise").astype(int)
    pred_values = pd.to_numeric(y_pred, errors="raise").astype(int)
    tp = int(((true_values == 1) & (pred_values == 1)).sum())
    fp = int(((true_values == 0) & (pred_values == 1)).sum())
    tn = int(((true_values == 0) & (pred_values == 0)).sum())
    fn = int(((true_values == 1) & (pred_values == 0)).sum())
    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
    }


def compute_precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    """Compute precision, recall, and F1 with safe zero-denominator handling."""
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
    """Build one evaluation summary row."""
    metrics = compute_precision_recall_f1(
        counts["true_positives"],
        counts["false_positives"],
        counts["false_negatives"],
    )
    false_positives_per_30_days = _safe_divide(
        counts["false_positives"] * 30,
        total_days,
    )
    return {
        "subject": subject,
        "matching_mode": matching_mode,
        "total_days": total_days,
        "true_anomaly_days": true_anomaly_days,
        "predicted_positive_days": predicted_positive_days,
        **counts,
        **metrics,
        "false_positives_per_30_days": round(false_positives_per_30_days, 6),
    }


def compute_exact_metrics(daily_predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute exact-day metrics for all evaluation subjects."""
    rows: list[dict[str, Any]] = []
    total_days = len(daily_predictions)
    true_anomaly_days = int(daily_predictions["is_anomaly"].sum())

    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        counts = compute_binary_counts(daily_predictions["is_anomaly"], daily_predictions[pred_col])
        rows.append(
            _summary_row(
                subject,
                "exact_day",
                total_days,
                true_anomaly_days,
                int(daily_predictions[pred_col].sum()),
                counts,
            )
        )

    return pd.DataFrame(rows, columns=config.EVALUATION_SUMMARY_COLUMNS)


def _match_with_tolerance(
    true_dates: list[pd.Timestamp],
    predicted_dates: list[pd.Timestamp],
    tolerance_days: int = 1,
) -> tuple[int, int, int]:
    """One-to-one match predicted dates to nearest unmatched true dates."""
    sorted_true_dates = sorted(true_dates)
    unmatched_indices = set(range(len(sorted_true_dates)))
    true_positive_matches = 0

    for predicted_date in sorted(predicted_dates):
        candidates: list[tuple[int, pd.Timestamp, int]] = []
        for index in unmatched_indices:
            true_date = sorted_true_dates[index]
            distance = abs((predicted_date - true_date).days)
            if distance <= tolerance_days:
                candidates.append((distance, true_date, index))
        if not candidates:
            continue
        _, _, matched_index = sorted(candidates)[0]
        unmatched_indices.remove(matched_index)
        true_positive_matches += 1

    false_positives = len(predicted_dates) - true_positive_matches
    false_negatives = len(true_dates) - true_positive_matches
    return true_positive_matches, false_positives, false_negatives


def compute_tolerance_metrics(daily_predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute +/-1 day tolerant metrics for all evaluation subjects."""
    rows: list[dict[str, Any]] = []
    total_days = len(daily_predictions)
    true_anomaly_days = int(daily_predictions["is_anomaly"].sum())
    true_dates = pd.to_datetime(
        daily_predictions.loc[daily_predictions["is_anomaly"] == 1, "usage_date"]
    ).tolist()

    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        predicted_dates = pd.to_datetime(
            daily_predictions.loc[daily_predictions[pred_col] == 1, "usage_date"]
        ).tolist()
        tp, fp, fn = _match_with_tolerance(true_dates, predicted_dates)
        tn = total_days - tp - fp - fn
        counts = {
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        }
        rows.append(
            _summary_row(
                subject,
                "tolerance_1_day",
                total_days,
                true_anomaly_days,
                len(predicted_dates),
                counts,
            )
        )

    return pd.DataFrame(rows, columns=config.EVALUATION_SUMMARY_COLUMNS)


def compute_evaluation_summary(daily_predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute exact-day and +/-1 day tolerant summary metrics."""
    summary = pd.concat(
        [
            compute_exact_metrics(daily_predictions),
            compute_tolerance_metrics(daily_predictions),
        ],
        ignore_index=True,
    )
    summary = summary.sort_values(["subject", "matching_mode"]).reset_index(drop=True)
    return summary[config.EVALUATION_SUMMARY_COLUMNS]


def compute_evaluation_by_type(daily_predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute recall by anomaly type for every evaluation subject."""
    true_rows = daily_predictions[daily_predictions["is_anomaly"] == 1]
    type_dates: dict[str, list[pd.Timestamp]] = {}
    for row in true_rows.itertuples(index=False):
        for anomaly_type in _split_anomaly_types(row.anomaly_types):
            type_dates.setdefault(anomaly_type, []).append(pd.Timestamp(row.usage_date))

    rows: list[dict[str, Any]] = []
    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        predicted_dates = set(
            pd.to_datetime(
                daily_predictions.loc[daily_predictions[pred_col] == 1, "usage_date"]
            )
        )

        for anomaly_type, anomaly_dates in sorted(type_dates.items()):
            exact_detected = sum(date in predicted_dates for date in anomaly_dates)
            tolerance_detected = 0
            for anomaly_date in anomaly_dates:
                if any(abs((predicted_date - anomaly_date).days) <= 1 for predicted_date in predicted_dates):
                    tolerance_detected += 1
            true_days = len(anomaly_dates)
            rows.append(
                {
                    "subject": subject,
                    "anomaly_type": anomaly_type,
                    "true_days": true_days,
                    "detected_days_exact": int(exact_detected),
                    "detected_days_tolerance_1_day": int(tolerance_detected),
                    "recall_exact": round(_safe_divide(exact_detected, true_days), 6),
                    "recall_tolerance_1_day": round(
                        _safe_divide(tolerance_detected, true_days),
                        6,
                    ),
                }
            )

    by_type = pd.DataFrame(rows, columns=config.EVALUATION_BY_TYPE_COLUMNS)
    return by_type.sort_values(["subject", "anomaly_type"]).reset_index(drop=True)


def compute_detection_delay(
    daily_predictions: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
) -> pd.DataFrame:
    """Compute event-level detection delay for true anomaly catalog events."""
    true_events = anomaly_catalog[
        pd.to_numeric(anomaly_catalog["planned_event"], errors="raise") == 0
    ].copy()
    rows: list[dict[str, Any]] = []

    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        predicted_dates = sorted(
            pd.to_datetime(
                daily_predictions.loc[daily_predictions[pred_col] == 1, "usage_date"]
            ).tolist()
        )

        for event in true_events.sort_values("start_date").itertuples(index=False):
            start_date = pd.Timestamp(event.start_date)
            end_date = pd.Timestamp(event.end_date)
            in_window = [
                predicted_date
                for predicted_date in predicted_dates
                if start_date <= predicted_date <= end_date
            ]
            if in_window:
                first_detection = min(in_window)
                detected = 1
                first_detection_date = first_detection.date().isoformat()
                detection_delay_days: int | float | str = int(
                    (first_detection - start_date).days
                )
            else:
                detected = 0
                first_detection_date = ""
                detection_delay_days = np.nan

            rows.append(
                {
                    "subject": subject,
                    "anomaly_id": event.anomaly_id,
                    "anomaly_type": event.anomaly_type,
                    "start_date": start_date.date().isoformat(),
                    "end_date": end_date.date().isoformat(),
                    "detected": detected,
                    "first_detection_date": first_detection_date,
                    "detection_delay_days": detection_delay_days,
                }
            )

    delay = pd.DataFrame(rows, columns=config.DETECTION_DELAY_COLUMNS)
    return delay.sort_values(["subject", "start_date", "anomaly_id"]).reset_index(drop=True)


def compute_false_positive_days(
    daily_predictions: pd.DataFrame,
    method_results: pd.DataFrame,
    alerts: pd.DataFrame,
    daily_features: pd.DataFrame,
) -> pd.DataFrame:
    """List exact-day false-positive prediction dates for each subject."""
    feature_context = daily_features[
        ["usage_date", "total_cost_usd", "anomaly_types", "planned_event", "is_anomaly"]
    ].copy()
    feature_context["usage_date"] = _iso_date_series(feature_context["usage_date"])
    alerts_by_date = alerts.set_index("usage_date", drop=False)
    method_index = method_results.set_index(["method", "usage_date"], drop=False)

    rows: list[dict[str, Any]] = []
    for subject in config.EVALUATION_SUBJECTS:
        pred_col = PREDICTION_COLUMNS[subject]
        fp_dates = daily_predictions.loc[
            (daily_predictions[pred_col] == 1) & (daily_predictions["is_anomaly"] == 0),
            "usage_date",
        ].tolist()

        for usage_date in fp_dates:
            context_row = feature_context[feature_context["usage_date"] == usage_date].iloc[0]
            if subject == "agreement_alert":
                alert_row = alerts_by_date.loc[usage_date]
                prediction_source = "alerts"
                alert_level = alert_row["alert_level"]
                methods_triggered = alert_row["methods_triggered"]
                actual_cost = float(alert_row["actual_cost"])
                expected_cost = float(alert_row["expected_cost"])
                relative_delta = float(alert_row["relative_delta"])
            else:
                method_row = method_index.loc[(subject, usage_date)]
                prediction_source = "method_results"
                alert_level = ""
                methods_triggered = ""
                actual_cost = float(method_row["actual_cost"])
                expected_cost = float(method_row["expected_cost"])
                relative_delta = float(method_row["relative_deviation"])

            if int(context_row["planned_event"]) == 1:
                reason = (
                    "Predicted anomaly on a planned event day; this is useful "
                    "for false-positive analysis."
                )
            else:
                reason = "Predicted anomaly on a non-anomaly day."

            rows.append(
                {
                    "subject": subject,
                    "usage_date": usage_date,
                    "prediction_source": prediction_source,
                    "planned_event": int(context_row["planned_event"]),
                    "anomaly_type": context_row["anomaly_types"],
                    "alert_level": alert_level,
                    "methods_triggered": methods_triggered,
                    "actual_cost": round(actual_cost, 4),
                    "expected_cost": round(expected_cost, 4),
                    "relative_delta": round(relative_delta, 6),
                    "reason": reason,
                }
            )

    false_positive_days = pd.DataFrame(rows, columns=config.FALSE_POSITIVE_DAYS_COLUMNS)
    return false_positive_days.sort_values(["subject", "usage_date"]).reset_index(drop=True)


def validate_evaluation_outputs(
    evaluation_summary: pd.DataFrame,
    evaluation_by_type: pd.DataFrame,
    detection_delay: pd.DataFrame,
    false_positive_days: pd.DataFrame,
    daily_predictions: pd.DataFrame,
) -> None:
    """Validate all Phase 6 evaluation outputs before saving."""
    if list(evaluation_summary.columns) != config.EVALUATION_SUMMARY_COLUMNS:
        raise ValueError("evaluation_summary columns do not match the required schema.")
    if len(evaluation_summary) != len(config.EVALUATION_SUBJECTS) * len(config.EVALUATION_MATCHING_MODES):
        raise ValueError("evaluation_summary must contain exactly 8 rows.")
    if set(evaluation_summary["subject"]) != set(config.EVALUATION_SUBJECTS):
        raise ValueError("evaluation_summary contains unexpected subjects.")
    if set(evaluation_summary["matching_mode"]) != set(config.EVALUATION_MATCHING_MODES):
        raise ValueError("evaluation_summary contains unexpected matching modes.")
    if not (evaluation_summary["total_days"] == config.NUM_DAYS).all():
        raise ValueError("evaluation_summary total_days must be 180.")
    if evaluation_summary["true_anomaly_days"].nunique() != 1:
        raise ValueError("true_anomaly_days must be consistent across summary rows.")

    count_columns = [
        "predicted_positive_days",
        "true_positives",
        "false_positives",
        "true_negatives",
        "false_negatives",
    ]
    if (evaluation_summary[count_columns] < 0).any().any():
        raise ValueError("evaluation_summary counts must be non-negative.")
    metric_columns = ["precision", "recall", "f1", "false_positives_per_30_days"]
    if not np.isfinite(evaluation_summary[metric_columns].to_numpy()).all():
        raise ValueError("evaluation_summary metrics must be finite.")
    if (evaluation_summary[metric_columns] < 0).any().any():
        raise ValueError("evaluation_summary metrics must be non-negative.")
    for metric in ["precision", "recall", "f1"]:
        if not evaluation_summary[metric].between(0, 1).all():
            raise ValueError(f"{metric} must be between 0 and 1.")

    if list(evaluation_by_type.columns) != config.EVALUATION_BY_TYPE_COLUMNS:
        raise ValueError("evaluation_by_type columns do not match the required schema.")
    if evaluation_by_type.empty:
        raise ValueError("evaluation_by_type must contain at least one row.")
    if (evaluation_by_type["anomaly_type"] == "none").any():
        raise ValueError("evaluation_by_type must exclude anomaly_type='none'.")
    if not evaluation_by_type["recall_exact"].between(0, 1).all():
        raise ValueError("recall_exact must be between 0 and 1.")
    if not evaluation_by_type["recall_tolerance_1_day"].between(0, 1).all():
        raise ValueError("recall_tolerance_1_day must be between 0 and 1.")

    if list(detection_delay.columns) != config.DETECTION_DELAY_COLUMNS:
        raise ValueError("detection_delay columns do not match the required schema.")
    if detection_delay.empty:
        raise ValueError("detection_delay must contain at least one row.")
    if not set(detection_delay["detected"].unique()).issubset({0, 1}):
        raise ValueError("detection_delay detected must contain only 0/1.")
    detected_delays = pd.to_numeric(
        detection_delay.loc[detection_delay["detected"] == 1, "detection_delay_days"],
        errors="raise",
    )
    if (detected_delays < 0).any():
        raise ValueError("detection_delay_days must be non-negative when detected.")

    if list(false_positive_days.columns) != config.FALSE_POSITIVE_DAYS_COLUMNS:
        raise ValueError("false_positive_days columns do not match the required schema.")
    if not false_positive_days.empty:
        true_by_date = daily_predictions.set_index("usage_date")["is_anomaly"]
        listed_truth = false_positive_days["usage_date"].map(true_by_date)
        if not (listed_truth == 0).all():
            raise ValueError("All false_positive_days rows must be non-anomaly days.")


def save_evaluation_reports(
    evaluation_summary: pd.DataFrame,
    evaluation_by_type: pd.DataFrame,
    detection_delay: pd.DataFrame,
    false_positive_days: pd.DataFrame,
    daily_predictions: pd.DataFrame,
) -> dict[str, Path]:
    """Save Phase 6 evaluation report CSV files."""
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "evaluation_summary": config.EVALUATION_SUMMARY_PATH,
        "evaluation_by_type": config.EVALUATION_BY_TYPE_PATH,
        "detection_delay": config.DETECTION_DELAY_PATH,
        "false_positive_days": config.FALSE_POSITIVE_DAYS_PATH,
        "evaluation_daily_predictions": config.EVALUATION_DAILY_PREDICTIONS_PATH,
    }
    evaluation_summary.to_csv(paths["evaluation_summary"], index=False)
    evaluation_by_type.to_csv(paths["evaluation_by_type"], index=False)
    detection_delay.to_csv(paths["detection_delay"], index=False)
    false_positive_days.to_csv(paths["false_positive_days"], index=False)
    daily_predictions.to_csv(paths["evaluation_daily_predictions"], index=False)
    return paths


def run_evaluation() -> dict[str, Any]:
    """Run Phase 6 evaluation and save report CSV files."""
    daily_features, method_results, alerts, anomaly_catalog = load_evaluation_inputs()
    daily_predictions = build_daily_prediction_table(
        daily_features,
        method_results,
        alerts,
    )
    evaluation_summary = compute_evaluation_summary(daily_predictions)
    evaluation_by_type = compute_evaluation_by_type(daily_predictions)
    detection_delay = compute_detection_delay(daily_predictions, anomaly_catalog)
    false_positive_days = compute_false_positive_days(
        daily_predictions,
        method_results,
        alerts,
        daily_features,
    )
    validate_evaluation_outputs(
        evaluation_summary,
        evaluation_by_type,
        detection_delay,
        false_positive_days,
        daily_predictions,
    )
    paths = save_evaluation_reports(
        evaluation_summary,
        evaluation_by_type,
        detection_delay,
        false_positive_days,
        daily_predictions,
    )
    return {
        "paths": paths,
        "evaluation_summary": evaluation_summary,
        "evaluation_by_type": evaluation_by_type,
        "detection_delay": detection_delay,
        "false_positive_days": false_positive_days,
        "daily_predictions": daily_predictions,
    }


def main() -> None:
    """CLI entry point for Phase 6 evaluation."""
    result = run_evaluation()
    print("Evaluation complete.")
    for path in result["paths"].values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
