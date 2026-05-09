"""
STL decomposition anomaly detector for daily cloud cost.
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
from statsmodels.tsa.seasonal import STL

try:
    from .. import config
except ImportError:  # Allows: python src/detectors/stl.py
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src import config  # type: ignore


def _load_daily_features(path: Path) -> pd.DataFrame:
    """Load daily feature input for the STL detector."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Daily features file not found: {path}")

    df = pd.read_csv(path)
    required_columns = {
        "usage_date",
        "total_cost_usd",
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


def _robust_residual_score(residual: pd.Series) -> pd.Series:
    """
    Score residuals using scaled median absolute deviation.

    The MAD scale is robust to a small number of injected anomalies. If the MAD
    is zero, the residual standard deviation is used as a safe fallback.
    """
    residual_median = float(residual.median())
    mad = float(np.median(np.abs(residual - residual_median)))
    scale = mad * 1.4826
    if scale <= 0:
        scale = float(residual.std(ddof=0))
    if scale <= 0:
        scale = 1.0
    return ((residual - residual_median).abs() / scale).replace(
        [np.inf, -np.inf],
        0.0,
    )


def _severity_from_score(score: float) -> str:
    """Convert residual anomaly score to a method-local severity hint."""
    if score >= 4.0:
        return "high"
    if score >= 3.0:
        return "medium"
    if score >= 2.0:
        return "low"
    return "none"


def _stl_explanation(score: float) -> str:
    """Build a concise explanation for an STL result row."""
    if score >= config.STL_RESIDUAL_THRESHOLD:
        return (
            "STL residual is unusually high compared with the weekly seasonal "
            "baseline."
        )
    return "Observed cost is close to STL expected cost."


def build_stl_outputs(
    daily_features: pd.DataFrame,
    period: int = config.STL_PERIOD,
    residual_threshold: float = config.STL_RESIDUAL_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build STL detector results and decomposition components."""
    df = daily_features.copy().sort_values("usage_date").reset_index(drop=True)
    actual_cost = pd.to_numeric(df["total_cost_usd"], errors="raise")

    series = pd.Series(
        actual_cost.to_numpy(),
        index=pd.to_datetime(df["usage_date"], errors="raise"),
    )
    stl_result = STL(series, period=period, robust=True).fit()

    trend = pd.Series(stl_result.trend.to_numpy(), index=df.index)
    seasonal = pd.Series(stl_result.seasonal.to_numpy(), index=df.index)
    residual = pd.Series(stl_result.resid.to_numpy(), index=df.index)
    expected_cost = trend + seasonal
    residual_score = _robust_residual_score(residual).fillna(0.0)
    is_flagged = (residual_score >= residual_threshold).astype(int)
    deviation = actual_cost - expected_cost
    relative_deviation = np.where(
        expected_cost > 0,
        np.abs(deviation) / expected_cost,
        0.0,
    )

    results = pd.DataFrame(
        {
            "usage_date": df["usage_date"],
            "method": "stl",
            "is_flagged": is_flagged,
            "score": residual_score.round(6),
            "threshold": float(residual_threshold),
            "actual_cost": actual_cost.round(4),
            "expected_cost": expected_cost.round(4),
            "deviation": deviation.round(4),
            "relative_deviation": pd.Series(relative_deviation).round(6),
            "severity_hint": [_severity_from_score(score) for score in residual_score],
            "explanation": [_stl_explanation(score) for score in residual_score],
        }
    )

    for column in config.DETECTOR_OPTIONAL_CONTEXT_COLUMNS:
        results[column] = df[column]

    components = pd.DataFrame(
        {
            "usage_date": df["usage_date"],
            "actual_cost": actual_cost.round(4),
            "trend": trend.round(4),
            "seasonal": seasonal.round(4),
            "residual": residual.round(4),
            "expected_cost": expected_cost.round(4),
            "residual_score": residual_score.round(6),
            "is_flagged": is_flagged,
        }
    )

    results = results[config.DETECTOR_RESULT_WITH_CONTEXT_COLUMNS]
    components = components[config.STL_COMPONENT_COLUMNS]
    validate_stl_outputs(results, components)
    return results, components


def validate_stl_outputs(results: pd.DataFrame, components: pd.DataFrame) -> None:
    """Validate STL result and component outputs."""
    missing_columns = sorted(set(config.DETECTOR_RESULT_COLUMNS) - set(results.columns))
    if missing_columns:
        raise ValueError(f"STL output is missing columns: {missing_columns}")
    if list(components.columns) != config.STL_COMPONENT_COLUMNS:
        raise ValueError("STL components columns do not match the required schema.")
    if len(results) != config.NUM_DAYS or len(components) != config.NUM_DAYS:
        raise ValueError(f"STL outputs must contain {config.NUM_DAYS} rows.")
    if not results["usage_date"].is_monotonic_increasing:
        raise ValueError("STL output must be sorted by usage_date.")
    if not set(results["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError("STL is_flagged must contain only 0/1.")
    if not set(components["is_flagged"].unique()).issubset({0, 1}):
        raise ValueError("STL components is_flagged must contain only 0/1.")

    numeric_columns = [
        "score",
        "threshold",
        "actual_cost",
        "expected_cost",
        "deviation",
        "relative_deviation",
    ]
    if not np.isfinite(results[numeric_columns].to_numpy()).all():
        raise ValueError("STL output contains non-finite numeric values.")
    component_numeric = components.drop(columns=["usage_date"])
    if not np.isfinite(component_numeric.to_numpy()).all():
        raise ValueError("STL components contain non-finite numeric values.")
    if (results["actual_cost"] < 0).any():
        raise ValueError("STL actual_cost contains negative values.")
    if (results["relative_deviation"] < 0).any():
        raise ValueError("STL relative_deviation contains negative values.")

    allowed_severities = {"none", "low", "medium", "high"}
    if not set(results["severity_hint"].unique()).issubset(allowed_severities):
        raise ValueError("STL severity_hint contains invalid values.")
    if results["explanation"].astype(str).str.strip().eq("").any():
        raise ValueError("STL explanation contains blank values.")


def run_stl_detector(
    input_path: Path = config.DAILY_FEATURES_PATH,
    output_path: Path = config.STL_RESULTS_PATH,
    components_path: Path = config.STL_COMPONENTS_PATH,
) -> Path:
    """Run the STL detector and write result/component CSV outputs."""
    daily_features = _load_daily_features(input_path)
    results, components = build_stl_outputs(daily_features)

    output_path = Path(output_path)
    components_path = Path(components_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
    components.to_csv(components_path, index=False)
    return output_path


def main() -> None:
    """CLI entry point for the STL detector."""
    path = run_stl_detector()
    print("STL detector complete.")
    print(f"- {path}")
    print(f"- {config.STL_COMPONENTS_PATH}")


if __name__ == "__main__":
    main()
