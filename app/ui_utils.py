"""Shared Streamlit UI helpers for the demo dashboard."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable

warnings.filterwarnings(
    "ignore",
    message="Pandas requires version .*",
    category=UserWarning,
)

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COLORS = {
    "blue": "#38BDF8",
    "blue_dark": "#1D4ED8",
    "purple": "#A78BFA",
    "amber": "#F59E0B",
    "red": "#EF4444",
    "green": "#22C55E",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "surface": "#111827",
    "surface_2": "#0F172A",
    "border": "#243244",
}

METHOD_DISPLAY_NAMES = {
    "zscore": "Rolling Z-score",
    "stl": "STL Decomposition",
    "isolation_forest": "Isolation Forest",
}

SUBJECT_DISPLAY_NAMES = {
    "zscore": "Rolling Z-score",
    "stl": "STL Decomposition",
    "isolation_forest": "Isolation Forest",
    "agreement_alert": "Agreement Alert",
}


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file with cached Streamlit data loading."""
    return pd.read_csv(path)


def require_files(paths: Iterable[Path]) -> None:
    """Stop the current page with a friendly message if files are missing."""
    missing = [path for path in paths if not path.exists()]
    if missing:
        st.error("Required output files are missing. Please run: python run_pipeline.py")
        with st.expander("Missing files"):
            for path in missing:
                st.code(str(path))
        st.stop()


def optional_csv(path: Path, label: str) -> pd.DataFrame:
    """Load an optional CSV file or show a warning and return an empty frame."""
    if not path.exists():
        st.warning(f"{label} is missing. Run python run_pipeline.py to regenerate it.")
        return pd.DataFrame()
    return load_csv(str(path))


def apply_global_style() -> None:
    """Apply lightweight dashboard styling."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.1rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
        .hero {
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(17, 24, 39, 0.92));
            border-radius: 14px;
            padding: 1.35rem 1.45rem;
            margin-bottom: 1rem;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
        }
        .hero h1 {
            margin: 0 0 0.35rem 0;
            font-size: 2.15rem;
            line-height: 1.1;
            letter-spacing: 0;
        }
        .hero p {
            margin: 0;
            color: #CBD5E1;
            font-size: 1rem;
        }
        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.95rem;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.26rem 0.62rem;
            font-size: 0.78rem;
            font-weight: 650;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(15, 23, 42, 0.84);
            color: #E5E7EB;
            white-space: nowrap;
        }
        .metric-card {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-left: 4px solid var(--accent);
            background: rgba(15, 23, 42, 0.72);
            border-radius: 10px;
            padding: 0.9rem 1rem;
            min-height: 105px;
        }
        .metric-label {
            color: #94A3B8;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.4rem;
        }
        .metric-value {
            color: #F8FAFC;
            font-size: 1.55rem;
            font-weight: 750;
            line-height: 1.15;
        }
        .metric-note {
            color: #94A3B8;
            font-size: 0.78rem;
            margin-top: 0.35rem;
        }
        .incident-card {
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: rgba(15, 23, 42, 0.78);
            border-radius: 12px;
            padding: 1.05rem 1.15rem;
            margin: 0.35rem 0 1rem;
        }
        .incident-title {
            font-size: 1.25rem;
            font-weight: 750;
            margin-bottom: 0.5rem;
        }
        .incident-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
        }
        .incident-field {
            border-top: 1px solid rgba(148, 163, 184, 0.15);
            padding-top: 0.6rem;
        }
        .field-label {
            color: #94A3B8;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 700;
        }
        .field-value {
            color: #F8FAFC;
            font-size: 1rem;
            font-weight: 650;
            margin-top: 0.18rem;
        }
        .callout {
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.68);
            border-radius: 10px;
            padding: 0.85rem 1rem;
            color: #CBD5E1;
            margin-bottom: 0.75rem;
        }
        @media (max-width: 900px) {
            .incident-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(required_paths: Iterable[Path] | None = None) -> None:
    """Render a compact shared sidebar title and data status."""
    st.sidebar.markdown("## Cloud Cost Anomaly Detector")
    st.sidebar.caption("Level 1 Demo")
    st.sidebar.page_link("streamlit_app.py", label="Home")
    st.sidebar.page_link("pages/1_Overview.py", label="Overview")
    st.sidebar.page_link("pages/2_Anomaly_Detail.py", label="Anomaly Detail")
    st.sidebar.page_link("pages/3_Evaluation.py", label="Evaluation")
    st.sidebar.divider()
    if required_paths is not None:
        missing = [path for path in required_paths if not path.exists()]
        if missing:
            st.sidebar.warning("Pipeline outputs missing")
        else:
            st.sidebar.success("Pipeline outputs loaded")


def metric_card(label: str, value: str, accent: str = COLORS["blue"], note: str = "") -> None:
    """Render a styled KPI card."""
    note_html = f'<div class="metric-note">{note}</div>' if note else ""
    st.markdown(
        f"""
        <div class="metric-card" style="--accent: {accent};">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = COLORS["blue"]) -> str:
    """Return a small HTML badge."""
    return (
        f'<span class="badge" style="border-color: {color}66; '
        f'color: {color};">{text}</span>'
    )


def format_usd(value: float | int) -> str:
    """Format a number as USD."""
    return f"${float(value):,.2f}"


def format_usd_compact(value: float | int) -> str:
    """Format a number as compact USD for KPI cards."""
    return f"${float(value):,.0f}"


def format_pct(value: float | int) -> str:
    """Format a fractional number as a percentage."""
    return f"{float(value) * 100:.1f}%"


def format_number(value: float | int) -> str:
    """Format an integer-like value with thousands separators."""
    return f"{int(value):,}"


def yes_no(value: object) -> str:
    """Render 0/1-style values as Yes/No."""
    try:
        return "Yes" if int(value) == 1 else "No"
    except (TypeError, ValueError):
        return "No"


def method_display_name(value: str) -> str:
    """Return a human-readable detector method name."""
    return METHOD_DISPLAY_NAMES.get(str(value), str(value))


def format_methods(value: str) -> str:
    """Format comma-separated detector names for display."""
    methods = [method.strip() for method in str(value).split(",") if method.strip()]
    return ", ".join(method_display_name(method) for method in methods)


def subject_display_name(value: str) -> str:
    """Return a human-readable evaluation subject name."""
    return SUBJECT_DISPLAY_NAMES.get(str(value), str(value))


def plotly_base_layout(fig, title: str | None = None, height: int | None = None):
    """Apply the shared Plotly dark dashboard layout."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.35)",
        font=dict(color="#E5E7EB"),
        title=title,
        title_x=0,
        legend_title="",
        margin=dict(l=20, r=20, t=56 if title else 26, b=28),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig
