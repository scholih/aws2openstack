"""Streamlit dashboard for AWS to OpenStack migration assessments."""

import os
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

from aws2openstack.persistence import AssessmentRepository, get_engine
from aws2openstack.persistence.models import Assessment


@st.cache_resource
def get_db_session() -> Session:
    """Create and cache database session.

    Returns:
        SQLAlchemy session

    Raises:
        ValueError: If DATABASE_URL not set
    """
    if not os.getenv("DATABASE_URL"):
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Example: postgresql://user:pass@localhost:5432/aws2openstack"
        )

    engine = get_engine()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@st.cache_data(ttl=300)
def get_assessments() -> list[dict]:
    """Fetch all assessments from database with caching.

    Returns:
        List of assessment dictionaries with id, timestamp, region, account_id
    """
    session = get_db_session()
    repository = AssessmentRepository(session)

    assessments = repository.list_assessments()

    return [
        {
            "id": str(a.id),
            "timestamp": a.timestamp,
            "region": a.region,
            "account_id": a.aws_account_id,
            "display": f"{a.region} - {a.aws_account_id} ({a.timestamp.strftime('%Y-%m-%d %H:%M')})",
        }
        for a in assessments
    ]


@st.cache_data(ttl=300)
def get_assessment_summary(assessment_id: str) -> dict:
    """Fetch assessment summary with caching.

    Args:
        assessment_id: Assessment UUID

    Returns:
        Summary dictionary with counts and breakdowns
    """
    session = get_db_session()
    repository = AssessmentRepository(session)

    from uuid import UUID
    summary = repository.get_database_summary(UUID(assessment_id))

    return summary


def render_metric_cards(summary: dict) -> None:
    """Render summary metrics as cards.

    Args:
        summary: Assessment summary data
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 Databases",
            value=summary["database_count"],
        )

    with col2:
        st.metric(
            label="📋 Tables",
            value=summary["table_count"],
        )

    with col3:
        st.metric(
            label="💾 Total Size",
            value=f"{summary['total_estimated_size_gb']:.1f} GB",
        )

    with col4:
        st.metric(
            label="🧊 Iceberg Tables",
            value=summary["iceberg_table_count"],
        )


def render_readiness_chart(summary: dict) -> None:
    """Render migration readiness pie chart.

    Args:
        summary: Assessment summary data
    """
    readiness = summary.get("readiness_breakdown", {})

    if not readiness:
        st.info("No readiness data available")
        return

    # Create DataFrame for Plotly
    df = pd.DataFrame([
        {"status": status, "count": count}
        for status, count in readiness.items()
    ])

    # Color mapping for readiness statuses
    color_map = {
        "ready": "#10b981",  # green
        "needs_conversion": "#f59e0b",  # amber
        "blocked": "#ef4444",  # red
    }

    fig = px.pie(
        df,
        values="count",
        names="status",
        title="Migration Readiness Status",
        color="status",
        color_discrete_map=color_map,
        hole=0.4,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>",
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_format_chart(summary: dict) -> None:
    """Render table format breakdown bar chart.

    Args:
        summary: Assessment summary data
    """
    formats = summary.get("format_breakdown", {})

    if not formats:
        st.info("No format data available")
        return

    # Create DataFrame for Plotly
    df = pd.DataFrame([
        {"format": fmt, "count": count}
        for fmt, count in formats.items()
    ]).sort_values("count", ascending=False)

    fig = px.bar(
        df,
        x="format",
        y="count",
        title="Table Format Distribution",
        labels={"format": "Table Format", "count": "Number of Tables"},
        color="format",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Tables: %{y}<extra></extra>",
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="Table Format",
        yaxis_title="Number of Tables",
    )

    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    """Main Streamlit dashboard application."""
    st.set_page_config(
        page_title="AWS to OpenStack Migration Dashboard",
        page_icon="🚀",
        layout="wide",
    )

    st.title("🚀 AWS to OpenStack Migration Dashboard")
    st.markdown("Assessment overview and migration readiness analysis")

    # Check DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        st.error(
            "❌ DATABASE_URL environment variable not set. "
            "Please set it to connect to the PostgreSQL database."
        )
        st.stop()

    # Fetch assessments
    try:
        assessments = get_assessments()
    except Exception as e:
        st.error(f"❌ Failed to fetch assessments: {e}")
        st.stop()

    if not assessments:
        st.warning("⚠️ No assessments found. Run an assessment first using the CLI.")
        st.code("aws2openstack assess glue-catalog --region us-east-1 --output-dir ./output --save-to-db")
        st.stop()

    # Assessment selector
    st.sidebar.header("Select Assessment")

    selected_display = st.sidebar.selectbox(
        "Assessment",
        options=[a["display"] for a in assessments],
        index=0,
    )

    # Find selected assessment
    selected = next(a for a in assessments if a["display"] == selected_display)

    # Display assessment info
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Assessment Details**")
    st.sidebar.markdown(f"**Region:** {selected['region']}")
    st.sidebar.markdown(f"**Account ID:** {selected['account_id']}")
    st.sidebar.markdown(f"**Timestamp:** {selected['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch and display summary
    try:
        summary = get_assessment_summary(selected["id"])
    except Exception as e:
        st.error(f"❌ Failed to fetch assessment summary: {e}")
        st.stop()

    # Render components
    st.header("📊 Summary Metrics")
    render_metric_cards(summary)

    st.markdown("---")

    # Charts in two columns
    col1, col2 = st.columns(2)

    with col1:
        st.header("🎯 Migration Readiness")
        render_readiness_chart(summary)

    with col2:
        st.header("📂 Table Formats")
        render_format_chart(summary)

    # Refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
