"""
Isolation Forest anomaly detector for daily cloud cost features.
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
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

try:
    from .. import config
except ImportError:  # Allows: python src/detectors/isolation_forest.py
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src import config  # type: ignore


def _load_daily_features(path: Path) -> pd.DataFrame:
    """Load daily feature input for the Isolation Forest detector."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Daily features file not found: {path}")

    df = pd.read_csv(path)
    required_columns = {
        "usage_date",
        "cost_rolling_mean_14",
        *config.ISOLATION_FOREST_FEATURE_COLUMNS,
        *config.DETECTOR_OPTIONAL_CONTEXT_COLUMNS,
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Daily features are missing columns: {missing_columns}")

    df = df.sort_values("usage_date").reset_index(drop=True)
    df["usage_date"] = pd.to_datetime(df["usage_date"], errors="raise").dt.date.astype(
        str
    )
    return df


def _severity_hints(
    anomaly_score: np.ndarray,
    is_flagged: np.ndarray,
    threshold: float,
) -> list[str]:
    """Convert Isolation Forest scores to method-local severity hints."""
    top_one_percent = float(np.quantile(anomaly_score, 0.99))
    near_threshold = float(np.quantile(anomaly_score, 0.90))
    severities: list[str] = []

    for score, flagged in zip(anomaly_score, is_flagged):
        if flagged and score >= top_one_percent:
            severities.append("high")
        elif flagged:
            severities.append("medium")
        elif score >= max(near_threshold, threshold * 0.85):
            severities.append("low")
        else:
            severities.append("none")

    return severities


def _isolation_explanation(is_flagged: int) -> str:
    """Build a concise explanation for an Isolation Forest result row."""
    if is_flagged:
        return (
            "Isolation Forest marked this day as unusual based on cost, "
            "change, and contributor-share features."
        )
    return "Feature pattern is within the learned normal range."


def build_isolation_forest_results(
    daily_features: pd.DataFrame,
    n_estimators: int = config.ISOLATION_FOREST_N_ESTIMATORS,
    contamination: float = config.ISOLATION_FOREST_CONTAMINATION,
    random_state: int = config.DEFAULT_RANDOM_SEED,
) -> pd.DataFrame:
    """Build Isolation Forest detector results from daily feature rows."""
    df = daily_features.copy().sort_values("usage_date").reset_index(drop=True)
    feature_df = df[config.ISOLATION_FOREST_FEATURE_COLUMNS].apply(
        pd.to_numeric,
        errors="raise",
    )
    if not np.isfinite(feature_df.to_numpy()).all():
        raise ValueError("Isolation Forest input features must be finite.")

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_df)
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    predictions = model.fit_predict(scaled_features)
    is_flagged = (predictions == -1).astype(int)
    anomaly_score = -model.decision_function(scaled_features)

    if is_flagged.any():
        threshold = float(anomaly_score[is_flagged == 1].min())
    else:
        threshold = float(anomaly_score.max())

    actual_cost = pd.to_numeric(df["total_cost_usd"], errors="raise")
    expected_cost = pd.to_numeric(df["cost_rolling_mean_14"], errors="raise")
    deviation = actual_cost - expected_cost
    relative_deviation = np.where(
        expected_cost > 0,
        np.abs(deviation) / expected_cost,
        0.0,
    )

    results = pd.DataFrame(
        {
            "usage_date": df["usage_date"],
            "method": "isolation_forest",
            "is_flagged": is_flagged,
            "score": pd.Series(anomaly_score).round(6),
            "threshold": round(threshold, 6),
            "actual_cost": actual_cost.round(4),
            "expected_cost": expected_cost.round(4),
            "deviation": deviation.round(4),
            "relative_deviation": pd.Series(relative_deviation).round(6),
            "severity_hint": _severity_hints(anomaly_score, is_flagged, threshold),
            "explanation": [
                _isolation_explanation(flagged) for flagged in is_flagged
            ],
        }
    )

    for column in config.DETECTOR_OPTIONAL_CONTEXT_COLUMNS:
        results[column] = df[column]

    results = results[config.DETECTOR_RESULT_WITH_CONTEXT_COLUMNS]
    validate_isolation_forest_results(results)
    return results


def validate_isolation_forest_results(results: pd.DataFrame) -> None:
    """Validate the Isolation Forest detector output schema and values."""
    missing_columns = sorted(set(config.DETECTOR_RESULT_COLUMNS) - set(results.columns))
    if missing_columns:
        raise ValueError(
            f"Isolation Forest output is missing columns: {missing_columns}"
        )
    if len(results) != config.NUM_DAYS:
        raise ValueError(
            f"Isolation Forest output must contain {config.NUM_DAYS} rows."
        )
    if not results["usage_date"].is_monotonic_increasing:
        raise ValueError("Isolation Forest output must be sorted by usage_date.")
    if not set(results["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError("Isolation Forest is_flagged must contain only 0/1.")

    numeric_columns = [
        "score",
        "threshold",
        "actual_cost",
        "expected_cost",
        "deviation",
        "relative_deviation",
    ]
    if not np.isfinite(results[numeric_columns].to_numpy()).all():
        raise ValueError("Isolation Forest output contains non-finite numeric values.")
    if (results["actual_cost"] < 0).any():
        raise ValueError("Isolation Forest actual_cost contains negative values.")
    if (results["relative_deviation"] < 0).any():
        raise ValueError(
            "Isolation Forest relative_deviation contains negative values."
        )

    allowed_severities = {"none", "low", "medium", "high"}
    if not set(results["severity_hint"].unique()).issubset(allowed_severities):
        raise ValueError("Isolation Forest severity_hint contains invalid values.")
    if results["explanation"].astype(str).str.strip().eq("").any():
        raise ValueError("Isolation Forest explanation contains blank values.")


def run_isolation_forest_detector(
    input_path: Path = config.DAILY_FEATURES_PATH,
    output_path: Path = config.ISOLATION_FOREST_RESULTS_PATH,
    n_estimators: int = config.ISOLATION_FOREST_N_ESTIMATORS,
    contamination: float = config.ISOLATION_FOREST_CONTAMINATION,
    random_state: int = config.DEFAULT_RANDOM_SEED,
) -> Path:
    """Run the Isolation Forest detector and write its CSV output."""
    daily_features = _load_daily_features(input_path)
    results = build_isolation_forest_results(
        daily_features,
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    """CLI entry point for the Isolation Forest detector."""
    path = run_isolation_forest_detector()
    print("Isolation Forest detector complete.")
    print(f"- {path}")


if __name__ == "__main__":
    main()
