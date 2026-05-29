"""Streamlit page: evaluation results for methods and final alerts."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.ui_utils import (
    COLORS,
    apply_global_style,
    format_methods,
    format_pct,
    load_csv,
    metric_card,
    plotly_base_layout,
    render_sidebar,
    require_files,
    subject_display_name,
    yes_no,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SUMMARY_PATH = PROJECT_ROOT / "reports" / "evaluation_summary.csv"
EVALUATION_BY_TYPE_PATH = PROJECT_ROOT / "reports" / "evaluation_by_type.csv"
DETECTION_DELAY_PATH = PROJECT_ROOT / "reports" / "detection_delay.csv"
FALSE_POSITIVE_DAYS_PATH = PROJECT_ROOT / "reports" / "false_positive_days.csv"


st.set_page_config(page_title="Evaluation | Cloud Cost Anomaly Detector", layout="wide")
apply_global_style()
render_sidebar(
    [
        EVALUATION_SUMMARY_PATH,
        EVALUATION_BY_TYPE_PATH,
        DETECTION_DELAY_PATH,
        FALSE_POSITIVE_DAYS_PATH,
    ]
)


def format_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    """Format summary metrics for readable display."""
    display = df.copy()
    display["subject"] = display["subject"].map(subject_display_name)
    for column in ["precision", "recall", "f1"]:
        display[column] = display[column].map(format_pct)
    display["false_positives_per_30_days"] = display[
        "false_positives_per_30_days"
    ].astype(float).map("{:.2f}".format)
    display = display.rename(
        columns={
            "subject": "Subject",
            "matching_mode": "Matching mode",
            "total_days": "Total days",
            "true_anomaly_days": "True anomaly days",
            "predicted_positive_days": "Predicted positive days",
            "true_positives": "TP",
            "false_positives": "FP",
            "true_negatives": "TN",
            "false_negatives": "FN",
            "precision": "Precision",
            "recall": "Recall",
            "f1": "F1",
            "false_positives_per_30_days": "FP / 30 days",
        }
    )
    return display


def metrics_chart(summary: pd.DataFrame):
    """Build precision/recall/F1 comparison chart."""
    chart_data = summary.copy()
    chart_data["subject"] = chart_data["subject"].map(subject_display_name)
    chart_data = chart_data.melt(
        id_vars=["subject"],
        value_vars=["precision", "recall", "f1"],
        var_name="metric",
        value_name="value",
    )
    chart_data["metric"] = chart_data["metric"].map(
        {"precision": "Precision", "recall": "Recall", "f1": "F1"}
    )
    fig = px.bar(
        chart_data,
        x="subject",
        y="value",
        color="metric",
        barmode="group",
        color_discrete_map={
            "Precision": COLORS["blue"],
            "Recall": COLORS["green"],
            "F1": COLORS["purple"],
        },
        labels={"subject": "Subject", "value": "Score", "metric": "Metric"},
        text=chart_data["value"].map(lambda value: f"{value:.0%}"),
    )
    fig.update_yaxes(range=[0, 1], tickformat=".0%")
    return plotly_base_layout(fig, title="Precision, Recall, and F1 by Subject", height=380)


def false_positive_chart(summary: pd.DataFrame):
    """Build false positives per 30 days comparison chart."""
    chart_data = summary.copy()
    chart_data["subject"] = chart_data["subject"].map(subject_display_name)
    fig = px.bar(
        chart_data,
        x="subject",
        y="false_positives_per_30_days",
        color="subject",
        color_discrete_sequence=[COLORS["amber"], COLORS["blue"], COLORS["purple"], COLORS["red"]],
        labels={
            "subject": "Subject",
            "false_positives_per_30_days": "False positives per 30 days",
        },
        text=chart_data["false_positives_per_30_days"].map(lambda value: f"{value:.2f}"),
    )
    fig.update_layout(showlegend=False)
    return plotly_base_layout(fig, title="False Positives per 30 Days", height=330)


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
    "**How to read this page:** Precision means how many predicted anomalies were "
    "correct. Recall means how many true anomaly days were detected. F1 balances "
    "precision and recall. FP/30 days estimates alert noise level."
)

available_modes = ["exact_day", "tolerance_1_day"]
selected_mode = st.selectbox("Matching mode", available_modes)
mode_summary = summary[summary["matching_mode"] == selected_mode].copy()

top_cols = st.columns(4)
agreement = mode_summary[mode_summary["subject"] == "agreement_alert"]
if not agreement.empty:
    row = agreement.iloc[0]
    with top_cols[0]:
        metric_card("Agreement Precision", format_pct(row["precision"]), COLORS["blue"])
    with top_cols[1]:
        metric_card("Agreement Recall", format_pct(row["recall"]), COLORS["green"])
    with top_cols[2]:
        metric_card("Agreement F1", format_pct(row["f1"]), COLORS["purple"])
    with top_cols[3]:
        metric_card("Agreement FP / 30 days", f"{float(row['false_positives_per_30_days']):.2f}", COLORS["amber"])

st.subheader("Evaluation Summary")
st.dataframe(format_metric_table(mode_summary), use_container_width=True, hide_index=True)

left, right = st.columns([2, 1])
with left:
    st.plotly_chart(metrics_chart(mode_summary), use_container_width=True)
with right:
    st.plotly_chart(false_positive_chart(mode_summary), use_container_width=True)

st.subheader("Key Findings")
finding_cols = st.columns(4)
with finding_cols[0]:
    metric_card("Spike Detection", "Strong", COLORS["green"], "One-day spikes are easier to detect.")
with finding_cols[1]:
    metric_card("Gradual Drift", "Harder", COLORS["amber"], "Slow changes challenge simple methods.")
with finding_cols[2]:
    metric_card("Agreement Alert", "Selective", COLORS["blue"], "Lower alert volume can reduce recall.")
with finding_cols[3]:
    metric_card("Planned Events", "Review", COLORS["purple"], "False positives need human context.")

with st.expander("Evaluation by anomaly type", expanded=False):
    display_by_type = by_type.copy()
    display_by_type["subject"] = display_by_type["subject"].map(subject_display_name)
    for column in ["recall_exact", "recall_tolerance_1_day"]:
        display_by_type[column] = display_by_type[column].map(format_pct)
    display_by_type = display_by_type.rename(
        columns={
            "subject": "Subject",
            "anomaly_type": "Anomaly type",
            "true_days": "True days",
            "detected_days_exact": "Detected days exact",
            "detected_days_tolerance_1_day": "Detected days tolerance 1 day",
            "recall_exact": "Recall exact",
            "recall_tolerance_1_day": "Recall tolerance 1 day",
        }
    )
    st.dataframe(display_by_type, use_container_width=True, hide_index=True)

with st.expander("Detection delay", expanded=False):
    display_delay = detection_delay.copy()
    display_delay["subject"] = display_delay["subject"].map(subject_display_name)
    display_delay["detected"] = display_delay["detected"].map(yes_no)
    display_delay = display_delay.rename(
        columns={
            "subject": "Subject",
            "anomaly_id": "Anomaly ID",
            "anomaly_type": "Anomaly type",
            "detected": "Detected",
            "first_detection_date": "First detection date",
            "detection_delay_days": "Detection delay days",
        }
    )
    st.dataframe(display_delay, use_container_width=True, hide_index=True)

with st.expander("False positive days", expanded=False):
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
        display_fp = false_positive_days[false_positive_columns].copy()
        display_fp["subject"] = display_fp["subject"].map(subject_display_name)
        display_fp["planned_event"] = display_fp["planned_event"].map(yes_no)
        display_fp["methods_triggered"] = display_fp["methods_triggered"].map(
            lambda value: "" if pd.isna(value) else format_methods(value)
        )
        display_fp = display_fp.rename(
            columns={
                "subject": "Subject",
                "usage_date": "Date",
                "planned_event": "Planned event",
                "alert_level": "Alert level",
                "methods_triggered": "Methods triggered",
                "reason": "Reason",
            }
        )
        st.dataframe(display_fp, use_container_width=True, hide_index=True)
