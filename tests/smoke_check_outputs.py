"""Recompute and validate generated pipeline output contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src import config  # noqa: E402


FILES = {
    "raw": config.SYNTHETIC_CUR_LIKE_PATH,
    "anomaly_catalog": config.ANOMALY_CATALOG_PATH,
    "planned_catalog": config.PLANNED_EVENT_CATALOG_PATH,
    "daily_total": config.DAILY_TOTAL_COST_PATH,
    "daily_service": config.DAILY_SERVICE_COST_PATH,
    "daily_region": config.DAILY_REGION_COST_PATH,
    "daily_service_region": config.DAILY_SERVICE_REGION_COST_PATH,
    "daily_features": config.DAILY_FEATURES_PATH,
    "method_results": config.METHOD_RESULTS_PATH,
    "alerts": config.ALERTS_PATH,
    "suppressed": config.SUPPRESSED_ALERTS_PATH,
    "contributors": config.CONTRIBUTORS_PATH,
    "calibration": config.CALIBRATION_SUMMARY_PATH,
    "evaluation_summary": config.EVALUATION_SUMMARY_PATH,
    "evaluation_by_type": config.EVALUATION_BY_TYPE_PATH,
    "event_level": config.EVENT_LEVEL_EVALUATION_PATH,
    "detection_delay": config.DETECTION_DELAY_PATH,
    "false_positive_days": config.FALSE_POSITIVE_DAYS_PATH,
    "scenario_robustness": config.SCENARIO_ROBUSTNESS_PATH,
}


def read_csv(name: str) -> pd.DataFrame:
    path = FILES[name]
    assert path.exists(), f"Missing required output file: {path}"
    return pd.read_csv(path)


def assert_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = sorted(set(columns) - set(df.columns))
    assert not missing, f"{name} missing required columns: {missing}"


def assert_finite(df: pd.DataFrame, columns: list[str], name: str) -> None:
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    assert values.notna().all().all(), f"{name} contains NaN numeric values"
    assert np.isfinite(values.to_numpy()).all(), f"{name} contains infinite values"


def assert_close(actual: pd.Series, expected: pd.Series, message: str) -> None:
    assert np.allclose(actual, expected, rtol=0, atol=1e-4), message


def expected_catalog_dates(catalog: pd.DataFrame) -> set[str]:
    dates: set[str] = set()
    for row in catalog.itertuples(index=False):
        dates.update(pd.date_range(row.start_date, row.end_date).strftime("%Y-%m-%d"))
    return dates


def check_raw_and_catalogs(
    raw: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
    planned_catalog: pd.DataFrame,
) -> None:
    assert_columns(raw, config.CUR_LIKE_COLUMNS, "raw")
    assert list(anomaly_catalog.columns) == config.ANOMALY_CATALOG_COLUMNS
    assert list(planned_catalog.columns) == config.PLANNED_EVENT_CATALOG_COLUMNS
    assert len(raw) == (
        config.NUM_DAYS
        * len(config.SERVICES)
        * len(config.REGIONS)
        * len(config.TAG_ENVIRONMENTS)
        * len(config.TAG_TEAMS)
    )
    assert raw.duplicated(
        ["usage_date", "service", "region", "tag_environment", "tag_team"]
    ).sum() == 0
    assert set(raw["usage_account_id"].astype(str)) == set(
        config.ACCOUNT_BY_ENVIRONMENT.values()
    )
    expected_accounts = raw["tag_environment"].map(config.ACCOUNT_BY_ENVIRONMENT)
    assert (raw["usage_account_id"].astype(str) == expected_accounts).all()
    assert set(raw["billing_currency"]) == {"USD"}
    assert raw["source_record_count"].between(12, 159).all()
    assert (raw["cost_usd"] >= 0).all() and (raw["usage_amount"] >= 0).all()

    usage_dates = pd.to_datetime(raw["usage_date"])
    billing_starts = pd.to_datetime(raw["billing_period_start"])
    assert (
        billing_starts
        == usage_dates.dt.to_period("M").dt.to_timestamp()
    ).all(), "billing_period_start must be the first day of the usage month"

    anomaly_ids = set(raw.loc[raw["anomaly_id"] != "none", "anomaly_id"])
    planned_ids = set(raw.loc[raw["planned_event_id"] != "none", "planned_event_id"])
    assert anomaly_ids == set(anomaly_catalog["anomaly_id"])
    assert planned_ids == set(planned_catalog["planned_event_id"])
    assert not anomaly_ids.intersection(planned_ids)
    assert set(anomaly_catalog["anomaly_type"]) == set(config.REQUIRED_CATALOG_EVENT_TYPES)

    for event in anomaly_catalog.itertuples(index=False):
        rows = raw[raw["anomaly_id"] == event.anomaly_id]
        assert not rows.empty
        assert set(rows["service"]) == {event.affected_service}
        assert set(rows["region"]) == {event.affected_region}
        assert set(rows["anomaly_type"]) == {event.anomaly_type}
        assert set(rows["usage_date"]).issubset(
            set(pd.date_range(event.start_date, event.end_date).strftime("%Y-%m-%d"))
        )

    for event in planned_catalog.itertuples(index=False):
        rows = raw[raw["planned_event_id"] == event.planned_event_id]
        assert not rows.empty
        assert set(rows["service"]) == {event.affected_service}
        assert set(rows["region"]) == {event.affected_region}
        assert set(rows["usage_date"]).issubset(
            set(pd.date_range(event.start_date, event.end_date).strftime("%Y-%m-%d"))
        )
        assert (rows["is_anomaly"] == 0).all()


def check_aggregate(
    raw: pd.DataFrame,
    output: pd.DataFrame,
    group_columns: list[str],
    output_cost_column: str,
) -> None:
    expected = (
        raw.groupby(group_columns, as_index=False)["cost_usd"].sum().sort_values(group_columns)
    )
    actual = output[group_columns + [output_cost_column]].sort_values(group_columns)
    merged = actual.merge(expected, on=group_columns, how="outer", validate="one_to_one")
    assert len(merged) == len(actual) == len(expected)
    assert_close(
        merged[output_cost_column],
        merged["cost_usd"].round(4),
        f"{output_cost_column} does not reconcile to raw cost",
    )


def check_processed_and_features(
    raw: pd.DataFrame,
    anomaly_catalog: pd.DataFrame,
    planned_catalog: pd.DataFrame,
) -> None:
    daily_total = read_csv("daily_total")
    daily_service = read_csv("daily_service")
    daily_region = read_csv("daily_region")
    daily_service_region = read_csv("daily_service_region")
    features = read_csv("daily_features")

    check_aggregate(raw, daily_total, ["usage_date"], "total_cost_usd")
    check_aggregate(
        raw,
        daily_service,
        ["usage_date", "service"],
        "service_cost_usd",
    )
    check_aggregate(
        raw,
        daily_region,
        ["usage_date", "region"],
        "region_cost_usd",
    )
    check_aggregate(
        raw,
        daily_service_region,
        ["usage_date", "service", "region"],
        "service_region_cost_usd",
    )

    assert len(features) == config.NUM_DAYS
    assert features["usage_date"].is_unique
    assert (features["account_count"] == len(config.ACCOUNT_BY_ENVIRONMENT)).all()
    assert set(features.loc[features["is_anomaly"] == 1, "usage_date"]) == expected_catalog_dates(
        anomaly_catalog
    )
    assert set(features.loc[features["planned_event"] == 1, "usage_date"]) == expected_catalog_dates(
        planned_catalog
    )
    assert not (
        (features["is_anomaly"] == 1) & (features["planned_event"] == 1)
    ).any()
    assert_finite(
        features,
        [
            "total_cost_usd",
            "total_usage_amount",
            "cost_rolling_mean_7",
            "cost_rolling_mean_14",
            "top_service_share",
            "top_region_share",
            "cost_vs_rolling_mean_7",
            "cost_vs_rolling_mean_14",
        ],
        "daily_features",
    )

    costs = features["total_cost_usd"]
    expected_7 = costs.shift(1).rolling(7, min_periods=1).mean().fillna(costs).round(4)
    expected_14 = costs.shift(1).rolling(14, min_periods=1).mean().fillna(costs).round(4)
    assert_close(features["cost_rolling_mean_7"], expected_7, "7-day baseline leaks current cost")
    assert_close(features["cost_rolling_mean_14"], expected_14, "14-day baseline leaks current cost")
    ratio_7 = ((costs - expected_7) / expected_7).round(6)
    assert_close(features["cost_vs_rolling_mean_7"], ratio_7, "7-day cost ratio is incorrect")


def check_detection_calibration_and_alerts() -> None:
    methods = read_csv("method_results")
    calibration = read_csv("calibration")
    alerts = read_csv("alerts")
    suppressed = read_csv("suppressed")

    assert len(methods) == config.NUM_DAYS * 3
    assert set(methods["method"]) == {"zscore", "stl", "isolation_forest"}
    assert not methods.duplicated(["usage_date", "method"]).any()
    assert_finite(
        methods,
        ["score", "threshold", "actual_cost", "expected_cost", "relative_deviation"],
        "method_results",
    )
    selected = calibration[calibration["selected"] == 1]
    assert set(selected["method"]) == {"zscore", "stl", "isolation_forest"}
    assert (selected.groupby("method").size() == 1).all()
    for row in calibration.itertuples(index=False):
        json.loads(row.parameters)
    selected_counts = selected.set_index("method")["predicted_positive_days"]
    actual_counts = methods.groupby("method")["is_flagged"].sum()
    assert selected_counts.astype(int).to_dict() == actual_counts.astype(int).to_dict()

    assert not alerts.empty
    assert alerts["alert_id"].is_unique and alerts["usage_date"].is_unique
    assert (alerts["planned_event"] == 0).all()
    assert (alerts["relative_delta"] >= config.ALERT_WARNING_RELATIVE_DELTA).all()
    critical = alerts[alerts["alert_level"] == "critical"]
    assert (critical["relative_delta"] >= config.ALERT_CRITICAL_RELATIVE_DELTA).all()
    assert (critical["method_count"] >= config.ALERT_CRITICAL_MIN_METHODS).all()
    warnings = alerts[alerts["alert_level"] == "warning"]
    valid_warning = (
        warnings["method_count"].ge(config.ALERT_WARNING_MIN_METHODS)
        | (
            warnings["relative_delta"].ge(config.ALERT_STRONG_SINGLE_METHOD_DELTA)
            & warnings["method_severity_hints"].str.contains(":high", regex=False)
        )
    )
    assert valid_warning.all()

    assert not suppressed.empty
    assert suppressed["suppression_id"].is_unique
    assert set(suppressed["suppression_type"]) == {"explained_planned_event"}
    assert (suppressed["relative_delta"] >= config.ALERT_WARNING_RELATIVE_DELTA).all()
    planned_ids = set(read_csv("planned_catalog")["planned_event_id"])
    assert set(suppressed["planned_event_id"]).issubset(planned_ids)
    assert set(alerts["usage_date"]).isdisjoint(set(suppressed["usage_date"]))


def check_contributors() -> None:
    alerts = read_csv("alerts")
    contributors = read_csv("contributors")
    service_region = read_csv("daily_service_region")
    assert set(alerts["alert_id"]) == set(contributors["alert_id"])
    assert contributors.groupby("alert_id").size().le(config.TOP_CONTRIBUTOR_LIMIT).all()
    assert (contributors.groupby("alert_id")["rank"].min() == 1).all()
    assert contributors["contribution_share"].between(0, 1).all()
    assert set(contributors["contribution_basis"]).issubset(
        {"positive_delta", "current_cost_fallback"}
    )

    service_region["usage_date"] = pd.to_datetime(service_region["usage_date"])
    for alert in alerts.itertuples(index=False):
        alert_date = pd.Timestamp(alert.usage_date)
        current = service_region[service_region["usage_date"] == alert_date].copy()
        history = service_region[service_region["usage_date"] < alert_date]
        averages = (
            history.sort_values("usage_date")
            .groupby(["service", "region"], as_index=False)
            .tail(7)
            .groupby(["service", "region"])["service_region_cost_usd"]
            .mean()
        )
        current["previous"] = [
            averages.get((row.service, row.region), 0.0)
            for row in current.itertuples(index=False)
        ]
        current["delta"] = current["service_region_cost_usd"] - current["previous"]
        positive_sum = current["delta"].clip(lower=0).sum()
        rows = contributors[contributors["alert_id"] == alert.alert_id].sort_values("rank")

        for row in rows.itertuples(index=False):
            source = current[
                (current["service"] == row.service) & (current["region"] == row.region)
            ].iloc[0]
            assert abs(row.cost_usd - source["service_region_cost_usd"]) <= 1e-4
            assert abs(row.previous_7d_avg_cost - round(source["previous"], 4)) <= 1e-4
            assert abs(row.delta_cost - round(source["delta"], 4)) <= 1e-4
            if row.contribution_basis == "positive_delta":
                assert row.delta_cost > 0
                expected_share = source["delta"] / positive_sum
            else:
                expected_share = source["service_region_cost_usd"] / current[
                    "service_region_cost_usd"
                ].sum()
            assert abs(row.contribution_share - expected_share) <= 1e-5

        if positive_sum > 0:
            expected_top = current.sort_values(
                ["delta", "service_region_cost_usd", "service", "region"],
                ascending=[False, False, True, True],
            ).iloc[0]
            assert rows.iloc[0]["service"] == expected_top["service"]
            assert rows.iloc[0]["region"] == expected_top["region"]


def check_evaluation() -> None:
    summary = read_csv("evaluation_summary")
    event_level = read_csv("event_level")
    expected_subjects = set(config.EVALUATION_SUBJECTS)
    assert len(summary) == len(expected_subjects) * len(config.EVALUATION_MATCHING_MODES)
    assert set(summary["subject"]) == expected_subjects
    assert set(summary["matching_mode"]) == set(config.EVALUATION_MATCHING_MODES)
    assert (summary["total_days"] == config.NUM_DAYS).all()
    for row in summary.itertuples(index=False):
        precision = row.true_positives / max(row.true_positives + row.false_positives, 1)
        recall = row.true_positives / max(row.true_positives + row.false_negatives, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        assert abs(row.precision - precision) <= 1e-6
        assert abs(row.recall - recall) <= 1e-6
        assert abs(row.f1 - f1) <= 1e-6
        assert (
            row.true_positives
            + row.false_positives
            + row.true_negatives
            + row.false_negatives
            == config.NUM_DAYS
        )

    assert len(event_level) == len(expected_subjects) * len(config.EVENT_MATCHING_MODES)
    assert set(event_level["subject"]) == expected_subjects
    assert set(event_level["matching_mode"]) == set(config.EVENT_MATCHING_MODES)
    for row in event_level.itertuples(index=False):
        assert row.detected_events + row.missed_events == row.true_events
        assert row.detected_events + row.false_positive_events == row.predicted_events
        assert 0 <= row.event_precision <= 1
        assert 0 <= row.event_recall <= 1
        assert 0 <= row.event_f1 <= 1

    false_positives = read_csv("false_positive_days")
    suppressed_rows = false_positives[
        false_positives["prediction_source"] == "suppressed_alerts"
    ]
    assert not suppressed_rows.empty
    assert (suppressed_rows["planned_event"] == 1).all()
    assert "alerts" not in set(
        false_positives.loc[
            false_positives["subject"] == "agreement_alert",
            "prediction_source",
        ]
    )


def check_scenario_robustness() -> None:
    robustness = read_csv("scenario_robustness")
    assert list(robustness.columns) == config.SCENARIO_ROBUSTNESS_COLUMNS
    assert len(robustness) == 5
    assert robustness["scenario_id"].is_unique
    assert robustness["random_seed"].is_unique
    assert set(robustness["random_seed"]) == {7, 21, 42, 84, 126}
    assert set(robustness["calibration_mode"]) == {"fixed_main_scenario"}

    metric_columns = [
        "operational_precision",
        "operational_recall",
        "operational_f1",
        "event_precision",
        "event_recall",
        "event_f1",
    ]
    assert robustness[metric_columns].apply(
        lambda column: column.between(0, 1)
    ).all().all()
    assert robustness[
        [
            "operational_precision",
            "operational_recall",
            "operational_f1",
            "operational_false_positives_per_30_days",
            "event_precision",
            "event_recall",
            "event_f1",
        ]
    ].drop_duplicates().shape[0] > 1

    main = robustness[robustness["scenario_id"] == "seed_42_main"]
    assert len(main) == 1
    main = main.iloc[0]
    summary = read_csv("evaluation_summary")
    operational = summary[
        (summary["subject"] == "agreement_alert")
        & (summary["matching_mode"] == "exact_day")
    ].iloc[0]
    event_level = read_csv("event_level")
    event = event_level[
        (event_level["subject"] == "agreement_alert")
        & (event_level["matching_mode"] == "event_window")
    ].iloc[0]

    assert main["true_anomaly_days"] == operational["true_anomaly_days"]
    assert main["operational_alerts"] == operational["predicted_positive_days"]
    assert abs(main["operational_precision"] - operational["precision"]) <= 1e-6
    assert abs(main["operational_recall"] - operational["recall"]) <= 1e-6
    assert abs(main["operational_f1"] - operational["f1"]) <= 1e-6
    assert abs(
        main["operational_false_positives_per_30_days"]
        - operational["false_positives_per_30_days"]
    ) <= 1e-6
    assert main["true_anomaly_events"] == event["true_events"]
    assert abs(main["event_precision"] - event["event_precision"]) <= 1e-6
    assert abs(main["event_recall"] - event["event_recall"]) <= 1e-6
    assert abs(main["event_f1"] - event["event_f1"]) <= 1e-6
    assert main["suppressed_planned_candidates"] == len(read_csv("suppressed"))


def main() -> None:
    for path in FILES.values():
        assert path.exists(), f"Missing required output file: {path}"

    raw = read_csv("raw")
    anomaly_catalog = read_csv("anomaly_catalog")
    planned_catalog = read_csv("planned_catalog")
    check_raw_and_catalogs(raw, anomaly_catalog, planned_catalog)
    check_processed_and_features(raw, anomaly_catalog, planned_catalog)
    check_detection_calibration_and_alerts()
    check_contributors()
    check_evaluation()
    check_scenario_robustness()
    print("Smoke check passed: outputs reconcile to source data and policy contracts.")


if __name__ == "__main__":
    main()
