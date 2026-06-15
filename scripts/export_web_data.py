"""Export existing pipeline CSV outputs as static JSON for the web dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "generated"

# The raw CUR-like file has tens of thousands of rows, so only a small,
# representative sample is exported for the dashboard data preview.
RAW_CUR_LIKE_PATH = PROJECT_ROOT / "data" / "raw" / "synthetic_cur_like_daily.csv"
RAW_SAMPLE_ROWS = 200

SOURCE_FILES = {
    "daily_features": PROJECT_ROOT / "data" / "processed" / "daily_features.csv",
    "method_results": PROJECT_ROOT / "data" / "outputs" / "method_results.csv",
    "alerts": PROJECT_ROOT / "data" / "outputs" / "alerts.csv",
    "suppressed_alerts": PROJECT_ROOT / "data" / "outputs" / "suppressed_alerts.csv",
    "contributors": PROJECT_ROOT / "data" / "outputs" / "contributors.csv",
    "stl_components": PROJECT_ROOT / "data" / "outputs" / "stl_components.csv",
    "calibration_summary": PROJECT_ROOT / "reports" / "calibration_summary.csv",
    "evaluation_summary": PROJECT_ROOT / "reports" / "evaluation_summary.csv",
    "event_level_evaluation": PROJECT_ROOT / "reports" / "event_level_evaluation.csv",
    "evaluation_by_type": PROJECT_ROOT / "reports" / "evaluation_by_type.csv",
    "detection_delay": PROJECT_ROOT / "reports" / "detection_delay.csv",
    "false_positive_days": PROJECT_ROOT / "reports" / "false_positive_days.csv",
    "scenario_robustness": PROJECT_ROOT / "reports" / "scenario_robustness.csv",
}


def dataframe_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Return JSON-safe records without changing values in the source frame."""
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    missing = [str(path) for path in SOURCE_FILES.values() if not path.exists()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Required pipeline outputs are missing. Run python run_pipeline.py first:\n"
            f"{joined}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = {name: pd.read_csv(path) for name, path in SOURCE_FILES.items()}

    for name, frame in frames.items():
        write_json(OUTPUT_DIR / f"{name}.json", dataframe_records(frame))

    raw_sample_rows = 0
    if RAW_CUR_LIKE_PATH.exists():
        raw_sample = pd.read_csv(RAW_CUR_LIKE_PATH, nrows=RAW_SAMPLE_ROWS)
        raw_sample_rows = int(len(raw_sample))
        with RAW_CUR_LIKE_PATH.open(encoding="utf-8") as handle:
            total_rows = sum(1 for _ in handle) - 1  # exclude header
        write_json(
            OUTPUT_DIR / "synthetic_cur_sample.json",
            {
                "sample_rows": raw_sample_rows,
                "total_rows": int(total_rows),
                "columns": list(raw_sample.columns),
                "rows": dataframe_records(raw_sample),
            },
        )

    daily = frames["daily_features"]
    alerts = frames["alerts"]
    suppressed = frames["suppressed_alerts"]
    manifest = {
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "total_days": int(daily["usage_date"].nunique()),
        "total_alerts": int(len(alerts)),
        "warning_alerts": int((alerts["alert_level"] == "warning").sum()),
        "critical_alerts": int((alerts["alert_level"] == "critical").sum()),
        "suppressed_planned_events": int(len(suppressed)),
        "true_anomaly_days": int(
            daily.loc[daily["is_anomaly"] == 1, "usage_date"].nunique()
        ),
        "planned_event_days": int(
            daily.loc[daily["planned_event"] == 1, "usage_date"].nunique()
        ),
        "data_files_available": [
            f"{name}.json" for name in SOURCE_FILES
        ],
    }
    write_json(OUTPUT_DIR / "dashboard_manifest.json", manifest)

    extra = 2 if raw_sample_rows else 1
    print(f"Exported {len(SOURCE_FILES) + extra} JSON files to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
