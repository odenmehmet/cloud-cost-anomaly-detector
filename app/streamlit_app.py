"""
Main Streamlit application entry point for the project dashboard.
"""

from pathlib import Path
import warnings

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "daily_features.csv"
ALERTS_PATH = PROJECT_ROOT / "data" / "outputs" / "alerts.csv"


st.set_page_config(
    page_title="Cloud Cost Anomaly Detection",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file with cached Streamlit data loading."""
    return pd.read_csv(path)


def require_files(paths: list[Path]) -> bool:
    """Return True if all required files exist, otherwise show a clear message."""
    missing = [path for path in paths if not path.exists()]
    if missing:
        st.error("Required output files are missing. Please run: python run_pipeline.py")
        with st.expander("Missing files"):
            for path in missing:
                st.code(str(path))
        return False
    return True


def metric_row(items: list[tuple[str, str]]) -> None:
    """Render a compact row of KPI metrics."""
    columns = st.columns(len(items))
    for column, (label, value) in zip(columns, items):
        column.metric(label, value)


st.title("Automated Cloud Cost Anomaly Detection")
st.caption("Synthetic CUR-like billing data, detection methods, alerts, contributors, and evaluation.")

st.markdown(
    """
This dashboard summarizes a Level 1 academic prototype for cloud cost anomaly
detection. It uses synthetic CUR-like billing data to demonstrate practical
daily cost monitoring, method agreement, and service/region contributor analysis.
"""
)

st.info(
    "This is a Level 1 academic prototype. It performs anomaly detection, "
    "alerting, and contributor analysis. It does not claim causal root-cause attribution."
)

st.subheader("Pipeline Summary")
st.write(
    "Synthetic CUR-like data -> preprocessing -> Z-score/STL/Isolation Forest -> "
    "alerting -> contributor analysis -> evaluation"
)

if not require_files([DAILY_FEATURES_PATH, ALERTS_PATH]):
    st.stop()

daily_features = load_csv(str(DAILY_FEATURES_PATH))
alerts = load_csv(str(ALERTS_PATH))

if daily_features.empty:
    st.error("Required output files are empty. Please run: python run_pipeline.py")
    st.stop()

warning_count = int((alerts["alert_level"] == "warning").sum()) if not alerts.empty else 0
critical_count = int((alerts["alert_level"] == "critical").sum()) if not alerts.empty else 0

metric_row(
    [
        ("Days", f"{daily_features['usage_date'].nunique():,}"),
        ("Total alerts", f"{len(alerts):,}"),
        ("Warning alerts", f"{warning_count:,}"),
        ("Critical alerts", f"{critical_count:,}"),
        ("True anomaly days", f"{int(daily_features['is_anomaly'].sum()):,}"),
    ]
)

st.subheader("How To Use")
st.write("Use the sidebar to open Overview, Anomaly Detail, and Evaluation pages.")

with st.expander("Dashboard data sources"):
    st.write(
        """
- `data/processed/daily_features.csv`
- `data/outputs/method_results.csv`
- `data/outputs/alerts.csv`
- `data/outputs/contributors.csv`
- `reports/evaluation_summary.csv`
"""
    )
