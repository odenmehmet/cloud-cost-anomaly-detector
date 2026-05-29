"""Streamlit page: selected alert detail and contributor analysis."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.ui_utils import (
    COLORS,
    apply_global_style,
    badge,
    format_methods,
    format_pct,
    format_usd,
    load_csv,
    method_display_name,
    optional_csv,
    plotly_base_layout,
    render_sidebar,
    require_files,
    yes_no,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALERTS_PATH = PROJECT_ROOT / "data" / "outputs" / "alerts.csv"
METHOD_RESULTS_PATH = PROJECT_ROOT / "data" / "outputs" / "method_results.csv"
CONTRIBUTORS_PATH = PROJECT_ROOT / "data" / "outputs" / "contributors.csv"
DAILY_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "daily_features.csv"
STL_COMPONENTS_PATH = PROJECT_ROOT / "data" / "outputs" / "stl_components.csv"


st.set_page_config(page_title="Anomaly Detail | Cloud Cost Anomaly Detector", layout="wide")
apply_global_style()
render_sidebar([ALERTS_PATH, METHOD_RESULTS_PATH, CONTRIBUTORS_PATH, DAILY_FEATURES_PATH])


def build_context_chart(
    daily_features: pd.DataFrame,
    stl_components: pd.DataFrame,
    selected_date: pd.Timestamp,
) -> go.Figure:
    """Build a local context chart around the selected alert date."""
    start_date = selected_date - pd.Timedelta(days=14)
    end_date = selected_date + pd.Timedelta(days=14)
    context = daily_features[
        (daily_features["usage_date"] >= start_date)
        & (daily_features["usage_date"] <= end_date)
    ][["usage_date", "total_cost_usd", "anomaly_types"]].copy()

    if not stl_components.empty:
        expected = stl_components[["usage_date", "expected_cost"]].copy()
        context = context.merge(expected, on="usage_date", how="left")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=context["usage_date"],
            y=context["total_cost_usd"],
            mode="lines+markers",
            name="Actual daily cost",
            line=dict(color=COLORS["blue"], width=2.4),
            marker=dict(size=6),
            customdata=context["anomaly_types"],
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Actual cost: $%{y:,.2f}<br>"
                "Anomaly type: %{customdata}<extra></extra>"
            ),
        )
    )

    if "expected_cost" in context.columns and context["expected_cost"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=context["usage_date"],
                y=context["expected_cost"],
                mode="lines",
                name="STL expected cost",
                line=dict(color=COLORS["amber"], width=2, dash="dash"),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Expected cost: $%{y:,.2f}<extra></extra>",
            )
        )

    selected_row = context[context["usage_date"] == selected_date]
    if not selected_row.empty:
        fig.add_trace(
            go.Scatter(
                x=selected_row["usage_date"],
                y=selected_row["total_cost_usd"],
                mode="markers",
                name="Selected alert date",
                marker=dict(color=COLORS["red"], size=15, symbol="star"),
                hovertemplate="Selected alert: %{x|%Y-%m-%d}<br>Cost: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.add_vline(x=selected_date, line_color=COLORS["red"], line_dash="dot")

    fig.update_yaxes(title="Total cost (USD)", tickprefix="$", separatethousands=True)
    fig.update_xaxes(title="Usage date")
    return plotly_base_layout(fig, title="Local Cost Context Around Selected Alert", height=390)


def contributor_chart(contributors: pd.DataFrame):
    """Build a bar chart for selected alert contributors."""
    chart_data = contributors.sort_values("rank", ascending=False).copy()
    chart_data["service_region"] = chart_data["service"] + " / " + chart_data["region"]
    fig = px.bar(
        chart_data,
        x="delta_cost",
        y="service_region",
        orientation="h",
        color="contribution_share",
        color_continuous_scale=["#1E293B", COLORS["blue"]],
        labels={
            "delta_cost": "Cost increase vs previous 7-day average",
            "service_region": "Service / region",
            "contribution_share": "Contribution share",
        },
        custom_data=[
            "service",
            "region",
            "cost_usd",
            "previous_7d_avg_cost",
            "delta_cost",
            "contribution_share",
        ],
    )
    fig.update_traces(
        hovertemplate=(
            "Service: %{customdata[0]}<br>"
            "Region: %{customdata[1]}<br>"
            "Current cost: $%{customdata[2]:,.2f}<br>"
            "Previous 7-day avg: $%{customdata[3]:,.2f}<br>"
            "Delta: $%{customdata[4]:,.2f}<br>"
            "Share: %{customdata[5]:.1%}<extra></extra>"
        )
    )
    fig.update_xaxes(tickprefix="$", separatethousands=True)
    return plotly_base_layout(
        fig,
        title="Top Service/Region Contributors vs Previous 7-Day Average",
        height=390,
    )


def render_incident_card(alert: pd.Series) -> None:
    """Render selected alert metadata as a compact incident card."""
    alert_level = str(alert["alert_level"]).title()
    level_color = COLORS["red"] if str(alert["alert_level"]) == "critical" else COLORS["amber"]
    truth_badge = (
        badge("True anomaly", COLORS["green"])
        if int(alert["is_true_anomaly"]) == 1
        else badge("Not a true anomaly", COLORS["muted"])
    )
    planned_badge = (
        badge("Planned event", COLORS["blue"])
        if int(alert["planned_event"]) == 1
        else badge("Unplanned", COLORS["purple"])
    )
    st.markdown(
        f"""
        <div class="incident-card">
            <div class="incident-title">
                {alert["alert_id"]} · {alert["usage_date"].date().isoformat()}
            </div>
            <div class="badge-row">
                {badge(alert_level, level_color)}
                {truth_badge}
                {planned_badge}
                {badge(str(alert["anomaly_type"]), COLORS["purple"])}
            </div>
            <div class="incident-grid" style="margin-top: 1rem;">
                <div class="incident-field" style="grid-column: span 2;">
                    <div class="field-label">Methods Triggered</div>
                    <div class="field-value">{format_methods(alert["methods_triggered"])}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Method Count</div>
                    <div class="field-value">{int(alert["method_count"])}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Actual Cost</div>
                    <div class="field-value">{format_usd(alert["actual_cost"])}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Expected Cost</div>
                    <div class="field-value">{format_usd(alert["expected_cost"])}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Relative Delta</div>
                    <div class="field-value">{format_pct(alert["relative_delta"])}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Top Current-Cost Service</div>
                    <div class="field-value">{alert["top_service"]}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Top Current-Cost Region</div>
                    <div class="field-value">{alert["top_region"]}</div>
                </div>
                <div class="incident-field">
                    <div class="field-label">Planned Event</div>
                    <div class="field-value">{yes_no(alert["planned_event"])}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.title("Anomaly Detail")

require_files([ALERTS_PATH, DAILY_FEATURES_PATH])
alerts = load_csv(str(ALERTS_PATH))
daily_features = load_csv(str(DAILY_FEATURES_PATH))
if alerts.empty:
    st.info("No alerts exist. Run python run_pipeline.py after detector and alert phases.")
    st.stop()

alerts["usage_date"] = pd.to_datetime(alerts["usage_date"])
daily_features["usage_date"] = pd.to_datetime(daily_features["usage_date"])
method_results = optional_csv(METHOD_RESULTS_PATH, "method_results.csv")
contributors = optional_csv(CONTRIBUTORS_PATH, "contributors.csv")
stl_components = optional_csv(STL_COMPONENTS_PATH, "stl_components.csv")

if not method_results.empty:
    method_results["usage_date"] = pd.to_datetime(method_results["usage_date"])
if not contributors.empty:
    contributors["usage_date"] = pd.to_datetime(contributors["usage_date"])
if not stl_components.empty:
    stl_components["usage_date"] = pd.to_datetime(stl_components["usage_date"])

alerts = alerts.sort_values("usage_date").reset_index(drop=True)
alert_options = [
    f"{row.alert_id} | {row.usage_date.date()} | {row.alert_level}"
    for row in alerts.itertuples(index=False)
]
default_index = next(
    (idx for idx, label in enumerate(alert_options) if label.startswith("ALERT-0001")),
    0,
)
selected_label = st.selectbox("Select alert", alert_options, index=default_index)
selected_alert_id = selected_label.split(" | ")[0]
selected_alert = alerts[alerts["alert_id"] == selected_alert_id].iloc[0]
selected_date = selected_alert["usage_date"]

if int(selected_alert["planned_event"]) == 1:
    st.warning(
        "This date is marked as a planned event. It is not a true anomaly and is "
        "useful for false-positive analysis."
    )
elif int(selected_alert["is_true_anomaly"]) == 1:
    st.success(f"True anomaly label: {selected_alert['anomaly_type']}")

if int(selected_alert["method_count"]) == 3 and int(selected_alert["is_true_anomaly"]) == 1:
    st.info(
        "Demo story: all three methods flagged this critical true anomaly. "
        "The injected label identifies it as a one-day spike."
    )
elif int(selected_alert["planned_event"]) == 1:
    st.info(
        "Demo story: this alert is retained even though it is a planned event, "
        "so it can be discussed as a false positive during evaluation."
    )

st.markdown(
    """
    <div class="callout">
        Contributor analysis ranks cost increases by service/region. It does not prove causality.
    </div>
    """,
    unsafe_allow_html=True,
)

render_incident_card(selected_alert)

st.write("**Alert reason**")
st.write(selected_alert["alert_reason"])

st.plotly_chart(
    build_context_chart(daily_features, stl_components, selected_date),
    use_container_width=True,
)

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
            display_methods = method_rows[
                [
                    "method",
                    "is_flagged",
                    "score",
                    "threshold",
                    "severity_hint",
                    "relative_deviation",
                    "explanation",
                ]
            ].copy()
            display_methods["method"] = display_methods["method"].map(method_display_name)
            display_methods["is_flagged"] = display_methods["is_flagged"].map(
                lambda value: "Flagged" if int(value) == 1 else "Not flagged"
            )
            display_methods["score"] = display_methods["score"].astype(float).map("{:.3f}".format)
            display_methods["threshold"] = display_methods["threshold"].astype(float).map("{:.3f}".format)
            display_methods["relative_deviation"] = display_methods["relative_deviation"].map(format_pct)
            display_methods = display_methods.rename(
                columns={
                    "method": "Method",
                    "is_flagged": "Flag status",
                    "score": "Score",
                    "threshold": "Threshold",
                    "severity_hint": "Severity hint",
                    "relative_deviation": "Relative deviation",
                    "explanation": "Explanation",
                }
            )
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
            st.plotly_chart(contributor_chart(alert_contributors), use_container_width=True)

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
        display_contributors = alert_contributors[
            [
                "rank",
                "service",
                "region",
                "cost_usd",
                "previous_7d_avg_cost",
                "delta_cost",
                "contribution_share",
                "contributor_reason",
            ]
        ].copy()
        for column in ["cost_usd", "previous_7d_avg_cost", "delta_cost"]:
            display_contributors[column] = display_contributors[column].map(format_usd)
        display_contributors["contribution_share"] = display_contributors[
            "contribution_share"
        ].map(format_pct)
        display_contributors = display_contributors.rename(
            columns={
                "rank": "Rank",
                "service": "Service",
                "region": "Region",
                "cost_usd": "Current cost",
                "previous_7d_avg_cost": "Previous 7-day avg",
                "delta_cost": "Delta cost",
                "contribution_share": "Contribution share",
                "contributor_reason": "Contributor reason",
            }
        )
        st.dataframe(display_contributors, use_container_width=True, hide_index=True)
