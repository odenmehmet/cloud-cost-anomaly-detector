"""Main Streamlit application entry point for the project dashboard."""

from pathlib import Path

import streamlit as st

from app.ui_utils import (
    COLORS,
    apply_global_style,
    badge,
    format_number,
    load_csv,
    metric_card,
    render_sidebar,
    require_files,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "daily_features.csv"
ALERTS_PATH = PROJECT_ROOT / "data" / "outputs" / "alerts.csv"


st.set_page_config(
    page_title="Cloud Cost Anomaly Detector",
    layout="wide",
)
apply_global_style()
render_sidebar([DAILY_FEATURES_PATH, ALERTS_PATH])


st.markdown(
    f"""
    <section class="hero">
        <h1>Cloud Cost Anomaly Detector</h1>
        <p>
            A professor-demo-ready Streamlit dashboard for synthetic CUR-like cost
            anomaly detection, alerting, contributor analysis, and evaluation.
        </p>
        <div class="badge-row">
            {badge("Level 1 / Standard", COLORS["green"])}
            {badge("Synthetic CUR-like data", COLORS["blue"])}
            {badge("3 detectors", COLORS["purple"])}
            {badge("Streamlit demo", COLORS["amber"])}
            {badge("Non-causal contributor analysis", COLORS["red"])}
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="callout">
        Synthetic CUR-like data -> preprocessing -> Rolling Z-score, STL, and
        Isolation Forest -> agreement alerts -> service/region contributors ->
        evaluation reports.
    </div>
    """,
    unsafe_allow_html=True,
)

require_files([DAILY_FEATURES_PATH, ALERTS_PATH])

daily_features = load_csv(str(DAILY_FEATURES_PATH))
alerts = load_csv(str(ALERTS_PATH))

if daily_features.empty:
    st.error("Required output files are empty. Please run: python run_pipeline.py")
    st.stop()

warning_count = int((alerts["alert_level"] == "warning").sum()) if not alerts.empty else 0
critical_count = int((alerts["alert_level"] == "critical").sum()) if not alerts.empty else 0

kpi_cols = st.columns(5)
with kpi_cols[0]:
    metric_card("Days", format_number(daily_features["usage_date"].nunique()), COLORS["blue"])
with kpi_cols[1]:
    metric_card("Total alerts", format_number(len(alerts)), COLORS["purple"])
with kpi_cols[2]:
    metric_card("Warning alerts", format_number(warning_count), COLORS["amber"])
with kpi_cols[3]:
    metric_card("Critical alerts", format_number(critical_count), COLORS["red"])
with kpi_cols[4]:
    metric_card(
        "True anomaly days",
        format_number(int(daily_features["is_anomaly"].sum())),
        COLORS["green"],
    )

left, right = st.columns([1.15, 0.85])

with left:
    st.subheader("Demo Flow")
    st.markdown(
        """
        1. **Overview**: inspect the daily total cost trend and alert markers.
        2. **Anomaly Detail**: explain `ALERT-0001` and its method agreement.
        3. **Evaluation**: compare detector performance and false positives.
        """
    )

with right:
    st.subheader("Scope Guard")
    st.info(
        "No AWS live ingestion, no production deployment, no notification delivery, "
        "and no causal root-cause attribution."
    )

st.divider()
st.write("Use the sidebar to open **Overview**, **Anomaly Detail**, and **Evaluation** pages.")
