"""
Rolling Z-score anomaly detector for daily cloud cost.
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
    from .. import config
except ImportError:  # Allows: python src/detectors/zscore.py
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src import config  # type: ignore


def _load_daily_features(path: Path) -> pd.DataFrame:
    """Load daily feature input for the Z-score detector."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Daily features file not found: {path}")

    df = pd.read_csv(path)
    required_columns = {
        "usage_date",
        "total_cost_usd",
        "day_of_week",
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


def _severity_from_z_score(abs_z_score: float) -> str:
    """Convert absolute Z-score to a method-local severity hint."""
    if abs_z_score >= 4.0:
        return "high"
    if abs_z_score >= 3.0:
        return "medium"
    if abs_z_score >= 2.0:
        return "low"
    return "none"


def _zscore_explanation(z_score: float, threshold: float) -> str:
    """Build a concise explanation for a Z-score result row."""
    if abs(z_score) >= threshold:
        direction = "above" if z_score > 0 else "below"
        return (
            f"Daily cost is {abs(z_score):.2f} standard deviations "
            f"{direction} rolling baseline."
        )
    return "Daily cost is within rolling baseline."


def _weekday_matched_rolling_baseline(
    df: pd.DataFrame,
    actual_cost: pd.Series,
    rolling_window: int,
    min_periods: int,
) -> tuple[pd.Series, pd.Series]:
    """
    Build a past-only rolling baseline matched by weekday.

    The synthetic data has explicit weekly seasonality, so this compares each
    day with previous observations from the same day of week. A standard
    past-only rolling baseline is used until enough weekday history exists.
    """
    fallback_mean = actual_cost.shift(1).rolling(
        window=rolling_window,
        min_periods=min_periods,
    ).mean()
    fallback_std = actual_cost.shift(1).rolling(
        window=rolling_window,
        min_periods=min_periods,
    ).std()

    same_weekday_means: list[float] = []
    same_weekday_stds: list[float] = []
    for row_index, row in df.iterrows():
        history = df.iloc[:row_index]
        history = history[history["day_of_week"] == row["day_of_week"]].tail(
            rolling_window
        )
        if len(history) >= min_periods:
            same_weekday_cost = pd.to_numeric(
                history["total_cost_usd"],
                errors="raise",
            )
            same_weekday_means.append(float(same_weekday_cost.mean()))
            same_weekday_stds.append(float(same_weekday_cost.std()))
        else:
            same_weekday_means.append(np.nan)
            same_weekday_stds.append(np.nan)

    past_cost = actual_cost.shift(1)
    expanding_mean = past_cost.expanding(min_periods=1).mean()
    expanding_std = past_cost.expanding(min_periods=2).std()
    baseline_mean = (
        pd.Series(same_weekday_means, index=df.index)
        .fillna(fallback_mean)
        .fillna(expanding_mean)
        .fillna(actual_cost)
    )
    baseline_std = (
        pd.Series(same_weekday_stds, index=df.index)
        .fillna(fallback_std)
        .fillna(expanding_std)
        .fillna(0.0)
    )
    return baseline_mean, baseline_std


def build_zscore_results(
    daily_features: pd.DataFrame,
    rolling_window: int = config.ZSCORE_ROLLING_WINDOW,
    min_periods: int = config.ZSCORE_MIN_PERIODS,
    z_threshold: float = config.ZSCORE_THRESHOLD,
) -> pd.DataFrame:
    """Build Z-score detector results from daily feature rows."""
    df = daily_features.copy().sort_values("usage_date").reset_index(drop=True)
    actual_cost = pd.to_numeric(df["total_cost_usd"], errors="raise")

    expected_cost, safe_std = _weekday_matched_rolling_baseline(
        df,
        actual_cost,
        rolling_window,
        min_periods,
    )
    safe_std = safe_std.mask(safe_std <= 0, np.nan)

    z_score = ((actual_cost - expected_cost) / safe_std).replace(
        [np.inf, -np.inf],
        0.0,
    )
    z_score = z_score.fillna(0.0)
    deviation = actual_cost - expected_cost
    relative_deviation = np.where(
        expected_cost > 0,
        np.abs(deviation) / expected_cost,
        0.0,
    )

    abs_z = np.abs(z_score)
    results = pd.DataFrame(
        {
            "usage_date": df["usage_date"],
            "method": "zscore",
            "is_flagged": (abs_z >= z_threshold).astype(int),
            "score": z_score.round(6),
            "threshold": float(z_threshold),
            "actual_cost": actual_cost.round(4),
            "expected_cost": expected_cost.round(4),
            "deviation": deviation.round(4),
            "relative_deviation": pd.Series(relative_deviation).round(6),
            "severity_hint": [_severity_from_z_score(score) for score in abs_z],
            "explanation": [
                _zscore_explanation(score, z_threshold) for score in z_score
            ],
        }
    )

    for column in config.DETECTOR_OPTIONAL_CONTEXT_COLUMNS:
        results[column] = df[column]

    results = results[config.DETECTOR_RESULT_WITH_CONTEXT_COLUMNS]
    validate_zscore_results(results)
    return results


def validate_zscore_results(results: pd.DataFrame) -> None:
    """Validate the Z-score detector output schema and values."""
    missing_columns = sorted(set(config.DETECTOR_RESULT_COLUMNS) - set(results.columns))
    if missing_columns:
        raise ValueError(f"Z-score output is missing columns: {missing_columns}")
    if len(results) != config.NUM_DAYS:
        raise ValueError(f"Z-score output must contain {config.NUM_DAYS} rows.")
    if not results["usage_date"].is_monotonic_increasing:
        raise ValueError("Z-score output must be sorted by usage_date.")
    if not set(results["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError("Z-score is_flagged must contain only 0/1.")
    numeric_columns = [
        "score",
        "threshold",
        "actual_cost",
        "expected_cost",
        "deviation",
        "relative_deviation",
    ]
    if not np.isfinite(results[numeric_columns].to_numpy()).all():
        raise ValueError("Z-score output contains non-finite numeric values.")
    if (results["actual_cost"] < 0).any():
        raise ValueError("Z-score actual_cost contains negative values.")
    if (results["relative_deviation"] < 0).any():
        raise ValueError("Z-score relative_deviation contains negative values.")
    allowed_severities = {"none", "low", "medium", "high"}
    if not set(results["severity_hint"].unique()).issubset(allowed_severities):
        raise ValueError("Z-score severity_hint contains invalid values.")
    if results["explanation"].astype(str).str.strip().eq("").any():
        raise ValueError("Z-score explanation contains blank values.")


def run_zscore_detector(
    input_path: Path = config.DAILY_FEATURES_PATH,
    output_path: Path = config.ZSCORE_RESULTS_PATH,
    rolling_window: int = config.ZSCORE_ROLLING_WINDOW,
    min_periods: int = config.ZSCORE_MIN_PERIODS,
    z_threshold: float = config.ZSCORE_THRESHOLD,
) -> Path:
    """Run the Rolling Z-score detector and write its CSV output."""
    daily_features = _load_daily_features(input_path)
    results = build_zscore_results(
        daily_features,
        rolling_window=rolling_window,
        min_periods=min_periods,
        z_threshold=z_threshold,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    """CLI entry point for the Z-score detector."""
    path = run_zscore_detector()
    print("Z-score detector complete.")
    print(f"- {path}")


if __name__ == "__main__":
    main()
