"""Streamlit page: overview of daily cost, labels, alerts, and methods."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.ui_utils import (
    COLORS,
    apply_global_style,
    format_number,
    format_methods,
    format_pct,
    format_usd,
    format_usd_compact,
    load_csv,
    method_display_name,
    metric_card,
    optional_csv,
    plotly_base_layout,
    render_sidebar,
    require_files,
    yes_no,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAILY_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "daily_features.csv"
ALERTS_PATH = PROJECT_ROOT / "data" / "outputs" / "alerts.csv"
METHOD_RESULTS_PATH = PROJECT_ROOT / "data" / "outputs" / "method_results.csv"


st.set_page_config(page_title="Overview | Cloud Cost Anomaly Detector", layout="wide")
apply_global_style()
render_sidebar([DAILY_FEATURES_PATH, ALERTS_PATH, METHOD_RESULTS_PATH])


def build_daily_cost_chart(daily: pd.DataFrame, alerts: pd.DataFrame) -> go.Figure:
    """Build the daily cost chart with true anomaly and alert markers."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["usage_date"],
            y=daily["total_cost_usd"],
            mode="lines",
            name="Daily total cost",
            line=dict(color=COLORS["blue"], width=2.4),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Cost: $%{y:,.2f}<extra></extra>",
        )
    )

    anomalies = daily[daily["is_anomaly"] == 1]
    if not anomalies.empty:
        fig.add_trace(
            go.Scatter(
                x=anomalies["usage_date"],
                y=anomalies["total_cost_usd"],
                mode="markers",
                name="True anomaly",
                marker=dict(color=COLORS["purple"], size=9, symbol="diamond"),
                customdata=anomalies[["anomaly_types", "top_service", "top_region"]],
                hovertemplate=(
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Cost: $%{y:,.2f}<br>"
                    "Anomaly type: %{customdata[0]}<br>"
                    "Top current-cost service: %{customdata[1]}<br>"
                    "Top current-cost region: %{customdata[2]}<extra></extra>"
                ),
            )
        )

    if not alerts.empty:
        alert_points = alerts.merge(
            daily[["usage_date", "total_cost_usd", "anomaly_types"]],
            on="usage_date",
            how="left",
        )
        alert_points["methods_display"] = alert_points["methods_triggered"].map(format_methods)
        for level, color, symbol, label in [
            ("warning", COLORS["amber"], "triangle-up", "Warning alert"),
            ("critical", COLORS["red"], "x", "Critical alert"),
        ]:
            level_points = alert_points[alert_points["alert_level"] == level]
            if not level_points.empty:
                fig.add_trace(
                    go.Scatter(
                        x=level_points["usage_date"],
                        y=level_points["total_cost_usd"],
                        mode="markers",
                        name=label,
                        marker=dict(color=color, size=12, symbol=symbol),
                        customdata=level_points[
                            ["alert_id", "methods_display", "alert_level", "anomaly_type"]
                        ],
                        hovertemplate=(
                            "Date: %{x|%Y-%m-%d}<br>"
                            "%{customdata[0]}<br>"
                            "Alert level: %{customdata[2]}<br>"
                            "Methods: %{customdata[1]}<br>"
                            "Anomaly label: %{customdata[3]}<br>"
                            "Cost: $%{y:,.2f}<extra></extra>"
                        ),
                    )
                )

    fig.update_yaxes(title="Total cost (USD)", tickprefix="$", separatethousands=True)
    fig.update_xaxes(title="Usage date")
    fig.update_layout(hovermode="x unified")
    return plotly_base_layout(
        fig,
        title="Daily Cloud Cost with True Anomalies and Alerts",
        height=470,
    )


st.title("Overview")

require_files([DAILY_FEATURES_PATH])
daily_features = load_csv(str(DAILY_FEATURES_PATH))
if daily_features.empty:
    st.error("Required output files are empty. Please run: python run_pipeline.py")
    st.stop()

daily_features["usage_date"] = pd.to_datetime(daily_features["usage_date"])
alerts = optional_csv(ALERTS_PATH, "alerts.csv")
method_results = optional_csv(METHOD_RESULTS_PATH, "method_results.csv")

if not alerts.empty:
    alerts["usage_date"] = pd.to_datetime(alerts["usage_date"])
if not method_results.empty:
    method_results["usage_date"] = pd.to_datetime(method_results["usage_date"])

min_date = daily_features["usage_date"].min().date()
max_date = daily_features["usage_date"].max().date()

date_cols = st.columns([1, 1, 2])
with date_cols[0]:
    start_date = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
with date_cols[1]:
    end_date = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.warning("Start date was after end date, so the full range is shown.")
    start_date, end_date = min_date, max_date

filtered_daily = daily_features[
    (daily_features["usage_date"].dt.date >= start_date)
    & (daily_features["usage_date"].dt.date <= end_date)
].copy()

filtered_alerts = alerts.copy()
if not filtered_alerts.empty:
    filtered_alerts = filtered_alerts[
        (filtered_alerts["usage_date"].dt.date >= start_date)
        & (filtered_alerts["usage_date"].dt.date <= end_date)
    ].copy()

kpi_cols = st.columns(5)
with kpi_cols[0]:
    metric_card("Total cost", format_usd_compact(filtered_daily["total_cost_usd"].sum()), COLORS["blue"])
with kpi_cols[1]:
    metric_card("True anomaly days", format_number(int(filtered_daily["is_anomaly"].sum())), COLORS["green"])
with kpi_cols[2]:
    metric_card("Total alerts", format_number(len(filtered_alerts)), COLORS["purple"])
with kpi_cols[3]:
    warning_count = int((filtered_alerts["alert_level"] == "warning").sum()) if not filtered_alerts.empty else 0
    metric_card("Warning alerts", format_number(warning_count), COLORS["amber"])
with kpi_cols[4]:
    critical_count = int((filtered_alerts["alert_level"] == "critical").sum()) if not filtered_alerts.empty else 0
    metric_card("Critical alerts", format_number(critical_count), COLORS["red"])

st.plotly_chart(build_daily_cost_chart(filtered_daily, filtered_alerts), use_container_width=True)

st.info(
    "Planned events are not true anomalies. If flagged, they are counted as false "
    "positives during evaluation. Top current-cost service is not necessarily the top "
    "contributor by delta; contributor ranking is shown in Anomaly Detail."
)

left, right = st.columns([2, 1])

with left:
    st.subheader("Alert Summary")
    if filtered_alerts.empty:
        st.write("No alerts are available for the selected date range.")
    else:
        alert_columns = [
            "alert_id",
            "usage_date",
            "alert_level",
            "methods_triggered",
            "actual_cost",
            "expected_cost",
            "relative_delta",
            "is_true_anomaly",
            "anomaly_type",
            "planned_event",
            "top_service",
            "top_region",
        ]
        display_alerts = filtered_alerts[alert_columns].copy()
        display_alerts["usage_date"] = display_alerts["usage_date"].dt.date.astype(str)
        display_alerts["actual_cost"] = display_alerts["actual_cost"].map(format_usd)
        display_alerts["expected_cost"] = display_alerts["expected_cost"].map(format_usd)
        display_alerts["relative_delta"] = display_alerts["relative_delta"].map(format_pct)
        display_alerts["methods_triggered"] = display_alerts["methods_triggered"].map(format_methods)
        display_alerts["is_true_anomaly"] = display_alerts["is_true_anomaly"].map(yes_no)
        display_alerts["planned_event"] = display_alerts["planned_event"].map(yes_no)
        display_alerts = display_alerts.rename(
            columns={
                "alert_id": "Alert ID",
                "usage_date": "Date",
                "alert_level": "Alert level",
                "methods_triggered": "Methods triggered",
                "actual_cost": "Actual cost",
                "expected_cost": "Expected cost",
                "relative_delta": "Relative delta",
                "is_true_anomaly": "True anomaly",
                "anomaly_type": "Anomaly type",
                "planned_event": "Planned event",
                "top_service": "Top current-cost service",
                "top_region": "Top current-cost region",
            }
        )
        st.dataframe(display_alerts, use_container_width=True, hide_index=True)

with right:
    st.subheader("Method Flag Counts")
    if method_results.empty:
        st.write("Method result data is not available.")
    else:
        filtered_methods = method_results[
            (method_results["usage_date"].dt.date >= start_date)
            & (method_results["usage_date"].dt.date <= end_date)
        ]
        method_counts = (
            filtered_methods.groupby("method", as_index=False)["is_flagged"]
            .sum()
            .rename(columns={"is_flagged": "Flagged days"})
            .sort_values("method")
        )
        method_counts["Method"] = method_counts["method"].map(method_display_name)
        method_counts = method_counts[["Method", "Flagged days"]]
        st.dataframe(method_counts, use_container_width=True, hide_index=True)
