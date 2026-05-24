"""
Streamlit page: overview of daily cost, labels, alerts, and methods.
"""

from pathlib import Path
import warnings

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAILY_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "daily_features.csv"
ALERTS_PATH = PROJECT_ROOT / "data" / "outputs" / "alerts.csv"
METHOD_RESULTS_PATH = PROJECT_ROOT / "data" / "outputs" / "method_results.csv"


st.set_page_config(page_title="Overview", layout="wide")


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file with cached Streamlit data loading."""
    return pd.read_csv(path)


def require_file(path: Path) -> None:
    """Stop the page with a friendly message if a required file is missing."""
    if not path.exists():
        st.error("Required output files are missing. Please run: python run_pipeline.py")
        st.stop()


def optional_csv(path: Path, label: str) -> pd.DataFrame:
    """Load an optional CSV file or show a warning and return an empty frame."""
    if not path.exists():
        st.warning(f"{label} is missing. Run python run_pipeline.py to regenerate it.")
        return pd.DataFrame()
    return load_csv(str(path))


def format_percent(series: pd.Series) -> pd.Series:
    """Format fractional values as percentages for display."""
    return (series.astype(float) * 100).map("{:.1f}%".format)


def build_daily_cost_chart(
    daily: pd.DataFrame,
    alerts: pd.DataFrame,
) -> go.Figure:
    """Build the daily cost chart with true anomaly and alert markers."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["usage_date"],
            y=daily["total_cost_usd"],
            mode="lines",
            name="Daily total cost",
            line=dict(color="#2563EB", width=2),
            hovertemplate="%{x}<br>Total cost: $%{y:,.2f}<extra></extra>",
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
                marker=dict(color="#7C3AED", size=9, symbol="diamond"),
                hovertemplate="%{x}<br>True anomaly: %{customdata}<br>Cost: $%{y:,.2f}<extra></extra>",
                customdata=anomalies["anomaly_types"],
            )
        )

    if not alerts.empty:
        alert_points = alerts.merge(
            daily[["usage_date", "total_cost_usd"]],
            on="usage_date",
            how="left",
        )
        for level, color, symbol in [
            ("warning", "#F59E0B", "triangle-up"),
            ("critical", "#DC2626", "x"),
        ]:
            level_points = alert_points[alert_points["alert_level"] == level]
            if not level_points.empty:
                fig.add_trace(
                    go.Scatter(
                        x=level_points["usage_date"],
                        y=level_points["total_cost_usd"],
                        mode="markers",
                        name=f"{level.title()} alert",
                        marker=dict(color=color, size=11, symbol=symbol),
                        customdata=level_points[["alert_id", "methods_triggered"]],
                        hovertemplate=(
                            "%{x}<br>%{customdata[0]}<br>"
                            "Methods: %{customdata[1]}<br>Cost: $%{y:,.2f}<extra></extra>"
                        ),
                    )
                )

    fig.update_layout(
        height=440,
        margin=dict(l=16, r=16, t=32, b=16),
        xaxis_title="Usage date",
        yaxis_title="Total cost (USD)",
        legend_title="",
        hovermode="x unified",
    )
    return fig


st.title("Overview")

require_file(DAILY_FEATURES_PATH)
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
selected_range = st.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(selected_range, tuple) and len(selected_range) == 2:
    start_date, end_date = selected_range
else:
    start_date = min_date
    end_date = max_date

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

metric_cols = st.columns(5)
metric_cols[0].metric("Total cost", f"${filtered_daily['total_cost_usd'].sum():,.0f}")
metric_cols[1].metric("True anomaly days", f"{int(filtered_daily['is_anomaly'].sum()):,}")
metric_cols[2].metric("Total alerts", f"{len(filtered_alerts):,}")
metric_cols[3].metric(
    "Warning alerts",
    f"{int((filtered_alerts['alert_level'] == 'warning').sum()) if not filtered_alerts.empty else 0:,}",
)
metric_cols[4].metric(
    "Critical alerts",
    f"{int((filtered_alerts['alert_level'] == 'critical').sum()) if not filtered_alerts.empty else 0:,}",
)

st.plotly_chart(
    build_daily_cost_chart(filtered_daily, filtered_alerts),
    use_container_width=True,
)

st.info(
    "Planned events are not true anomalies. If flagged, they are counted as false "
    "positives during evaluation."
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
        display_alerts["actual_cost"] = display_alerts["actual_cost"].map("${:,.2f}".format)
        display_alerts["expected_cost"] = display_alerts["expected_cost"].map("${:,.2f}".format)
        display_alerts["relative_delta"] = format_percent(display_alerts["relative_delta"])
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
            .rename(columns={"is_flagged": "flagged days"})
            .sort_values("method")
        )
        st.dataframe(method_counts, use_container_width=True, hide_index=True)
