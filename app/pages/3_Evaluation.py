"""
Streamlit page: evaluation results for methods and final alerts.
"""

from pathlib import Path
import warnings

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SUMMARY_PATH = PROJECT_ROOT / "reports" / "evaluation_summary.csv"
EVALUATION_BY_TYPE_PATH = PROJECT_ROOT / "reports" / "evaluation_by_type.csv"
DETECTION_DELAY_PATH = PROJECT_ROOT / "reports" / "detection_delay.csv"
FALSE_POSITIVE_DAYS_PATH = PROJECT_ROOT / "reports" / "false_positive_days.csv"


st.set_page_config(page_title="Evaluation", layout="wide")


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file with cached Streamlit data loading."""
    return pd.read_csv(path)


def require_files(paths: list[Path]) -> None:
    """Stop the page with a friendly message if any required report is missing."""
    missing = [path for path in paths if not path.exists()]
    if missing:
        st.error("Required output files are missing. Please run: python run_pipeline.py")
        with st.expander("Missing files"):
            for path in missing:
                st.code(str(path))
        st.stop()


def format_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    """Format summary metrics for readable display."""
    display = df.copy()
    for column in ["precision", "recall", "f1"]:
        display[column] = (display[column].astype(float) * 100).map("{:.1f}%".format)
    display["false_positives_per_30_days"] = display[
        "false_positives_per_30_days"
    ].map("{:.2f}".format)
    return display


def metrics_chart(summary: pd.DataFrame):
    """Build precision/recall/F1 comparison chart."""
    chart_data = summary.melt(
        id_vars=["subject"],
        value_vars=["precision", "recall", "f1"],
        var_name="metric",
        value_name="value",
    )
    fig = px.bar(
        chart_data,
        x="subject",
        y="value",
        color="metric",
        barmode="group",
        labels={"subject": "Subject", "value": "Score", "metric": "Metric"},
        text=chart_data["value"].map(lambda value: f"{value:.2f}"),
    )
    fig.update_yaxes(range=[0, 1], tickformat=".0%")
    fig.update_layout(height=380, margin=dict(l=16, r=16, t=24, b=16))
    return fig


def false_positive_chart(summary: pd.DataFrame):
    """Build false positives per 30 days comparison chart."""
    fig = px.bar(
        summary,
        x="subject",
        y="false_positives_per_30_days",
        color="subject",
        labels={
            "subject": "Subject",
            "false_positives_per_30_days": "False positives per 30 days",
        },
        text="false_positives_per_30_days",
    )
    fig.update_layout(height=320, showlegend=False, margin=dict(l=16, r=16, t=24, b=16))
    return fig


st.title("Evaluation")

required_paths = [
    EVALUATION_SUMMARY_PATH,
    EVALUATION_BY_TYPE_PATH,
    DETECTION_DELAY_PATH,
    FALSE_POSITIVE_DAYS_PATH,
]
require_files(required_paths)

summary = load_csv(str(EVALUATION_SUMMARY_PATH))
by_type = load_csv(str(EVALUATION_BY_TYPE_PATH))
detection_delay = load_csv(str(DETECTION_DELAY_PATH))
false_positive_days = load_csv(str(FALSE_POSITIVE_DAYS_PATH))

if summary.empty:
    st.error("Required output files are empty. Please run: python run_pipeline.py")
    st.stop()

st.info(
    "Evaluation compares produced detector and alert outputs against synthetic "
    "ground-truth anomaly labels. Poor metrics are shown directly for discussion."
)

available_modes = ["exact_day", "tolerance_1_day"]
selected_mode = st.selectbox("Matching mode", available_modes)
mode_summary = summary[summary["matching_mode"] == selected_mode].copy()

st.subheader("Evaluation Summary")
st.dataframe(format_metric_table(mode_summary), use_container_width=True, hide_index=True)

left, right = st.columns([2, 1])
with left:
    st.plotly_chart(metrics_chart(mode_summary), use_container_width=True)
with right:
    st.plotly_chart(false_positive_chart(mode_summary), use_container_width=True)

st.subheader("Evaluation By Anomaly Type")
display_by_type = by_type.copy()
for column in ["recall_exact", "recall_tolerance_1_day"]:
    display_by_type[column] = (
        display_by_type[column].astype(float) * 100
    ).map("{:.1f}%".format)
st.dataframe(display_by_type, use_container_width=True, hide_index=True)

st.subheader("Detection Delay")
delay_columns = [
    "subject",
    "anomaly_id",
    "anomaly_type",
    "detected",
    "first_detection_date",
    "detection_delay_days",
]
st.dataframe(detection_delay[delay_columns], use_container_width=True, hide_index=True)

st.subheader("False Positive Days")
false_positive_columns = [
    "subject",
    "usage_date",
    "planned_event",
    "alert_level",
    "methods_triggered",
    "reason",
]
if false_positive_days.empty:
    st.write("No false positive days are listed.")
else:
    st.dataframe(
        false_positive_days[false_positive_columns],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Interpretation")
st.write(
    """
- One-day spikes are easier to detect.
- Gradual drift is harder for these simple methods.
- Agreement alert can reduce alert volume but may lower recall.
- Planned event false positives show why human interpretation matters.
"""
)
