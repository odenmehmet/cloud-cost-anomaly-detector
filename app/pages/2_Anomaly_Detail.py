"""
Streamlit page: selected alert detail and contributor analysis.
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
ALERTS_PATH = PROJECT_ROOT / "data" / "outputs" / "alerts.csv"
METHOD_RESULTS_PATH = PROJECT_ROOT / "data" / "outputs" / "method_results.csv"
CONTRIBUTORS_PATH = PROJECT_ROOT / "data" / "outputs" / "contributors.csv"


st.set_page_config(page_title="Anomaly Detail", layout="wide")


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


def format_money(value: float) -> str:
    """Format a numeric value as USD."""
    return f"${float(value):,.2f}"


def format_percent(value: float) -> str:
    """Format a fractional value as a percentage."""
    return f"{float(value) * 100:.1f}%"


def contributor_chart(contributors: pd.DataFrame):
    """Build a bar chart for selected alert contributors."""
    chart_data = contributors.copy()
    chart_data["service_region"] = chart_data["service"] + " / " + chart_data["region"]
    fig = px.bar(
        chart_data.sort_values("rank", ascending=False),
        x="delta_cost",
        y="service_region",
        orientation="h",
        color="contribution_share",
        color_continuous_scale="Blues",
        labels={
            "delta_cost": "Delta cost vs previous 7-day average",
            "service_region": "Service / region",
            "contribution_share": "Contribution share",
        },
        hover_data=["cost_usd", "previous_7d_avg_cost", "contribution_share"],
    )
    fig.update_layout(height=360, margin=dict(l=16, r=16, t=24, b=16))
    return fig


st.title("Anomaly Detail")

require_file(ALERTS_PATH)
alerts = load_csv(str(ALERTS_PATH))
if alerts.empty:
    st.info("No alerts exist. Run python run_pipeline.py after detector and alert phases.")
    st.stop()

alerts["usage_date"] = pd.to_datetime(alerts["usage_date"])
method_results = optional_csv(METHOD_RESULTS_PATH, "method_results.csv")
contributors = optional_csv(CONTRIBUTORS_PATH, "contributors.csv")

if not method_results.empty:
    method_results["usage_date"] = pd.to_datetime(method_results["usage_date"])
if not contributors.empty:
    contributors["usage_date"] = pd.to_datetime(contributors["usage_date"])

alerts = alerts.sort_values("usage_date").reset_index(drop=True)
alert_options = {
    f"{row.alert_id} | {row.usage_date.date()} | {row.alert_level}": row.alert_id
    for row in alerts.itertuples(index=False)
}
selected_label = st.selectbox("Select alert", list(alert_options.keys()))
selected_alert_id = alert_options[selected_label]
selected_alert = alerts[alerts["alert_id"] == selected_alert_id].iloc[0]
selected_date = selected_alert["usage_date"]

if int(selected_alert["planned_event"]) == 1:
    st.warning(
        "This date is marked as a planned event. It is not a true anomaly and is "
        "useful for false-positive analysis."
    )
elif int(selected_alert["is_true_anomaly"]) == 1:
    st.success(f"True anomaly label: {selected_alert['anomaly_type']}")

st.info(
    "Contributor analysis identifies the largest service/region cost contributors. "
    "It is not causal root-cause attribution."
)

st.subheader("Selected Alert")
meta_cols = st.columns(4)
meta_cols[0].metric("Alert ID", selected_alert["alert_id"])
meta_cols[1].metric("Date", selected_date.date().isoformat())
meta_cols[2].metric("Level", str(selected_alert["alert_level"]).title())
meta_cols[3].metric("Methods", int(selected_alert["method_count"]))

cost_cols = st.columns(4)
cost_cols[0].metric("Actual cost", format_money(selected_alert["actual_cost"]))
cost_cols[1].metric("Expected cost", format_money(selected_alert["expected_cost"]))
cost_cols[2].metric("Relative delta", format_percent(selected_alert["relative_delta"]))
cost_cols[3].metric("Planned event", "Yes" if int(selected_alert["planned_event"]) else "No")

context = pd.DataFrame(
    [
        {
            "true_anomaly": "Yes" if int(selected_alert["is_true_anomaly"]) else "No",
            "anomaly_type": str(selected_alert["anomaly_type"]),
            "top_service": str(selected_alert["top_service"]),
            "top_region": str(selected_alert["top_region"]),
        }
    ]
)
st.dataframe(context, use_container_width=True, hide_index=True)

st.write("**Alert reason**")
st.write(selected_alert["alert_reason"])

left, right = st.columns([1, 1])

with left:
    st.subheader("Method Rows")
    if method_results.empty:
        st.warning("Method rows are unavailable for this alert date.")
    else:
        method_rows = method_results[method_results["usage_date"] == selected_date].copy()
        if method_rows.empty:
            st.warning("No method rows found for this alert date.")
        else:
            method_columns = [
                "method",
                "is_flagged",
                "score",
                "threshold",
                "severity_hint",
                "relative_deviation",
                "explanation",
            ]
            display_methods = method_rows[method_columns].copy()
            display_methods["score"] = display_methods["score"].map("{:.4f}".format)
            display_methods["threshold"] = display_methods["threshold"].map("{:.4f}".format)
            display_methods["relative_deviation"] = (
                display_methods["relative_deviation"].astype(float) * 100
            ).map("{:.1f}%".format)
            st.dataframe(display_methods, use_container_width=True, hide_index=True)

with right:
    st.subheader("Top Contributors")
    if contributors.empty:
        st.warning("Contributor rows are unavailable for this alert.")
    else:
        alert_contributors = contributors[
            contributors["alert_id"] == selected_alert["alert_id"]
        ].sort_values("rank")
        if alert_contributors.empty:
            st.warning("Selected alert has no contributor rows.")
        else:
            chart = contributor_chart(alert_contributors)
            st.plotly_chart(chart, use_container_width=True)

st.subheader("Contributor Table")
if contributors.empty:
    st.warning("Contributor rows are unavailable for this alert.")
else:
    alert_contributors = contributors[
        contributors["alert_id"] == selected_alert["alert_id"]
    ].sort_values("rank")
    if alert_contributors.empty:
        st.warning("Selected alert has no contributor rows.")
    else:
        contributor_columns = [
            "rank",
            "service",
            "region",
            "cost_usd",
            "previous_7d_avg_cost",
            "delta_cost",
            "contribution_share",
            "contributor_reason",
        ]
        display_contributors = alert_contributors[contributor_columns].copy()
        for column in ["cost_usd", "previous_7d_avg_cost", "delta_cost"]:
            display_contributors[column] = display_contributors[column].map("${:,.2f}".format)
        display_contributors["contribution_share"] = (
            display_contributors["contribution_share"].astype(float) * 100
        ).map("{:.1f}%".format)
        st.dataframe(display_contributors, use_container_width=True, hide_index=True)
