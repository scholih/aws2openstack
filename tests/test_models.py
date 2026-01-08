"""Tests for catalog data models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aws2openstack.models.catalog import (
    GlueTable,
    GlueDatabase,
    AssessmentMetadata,
    AssessmentSummary,
    AssessmentReport,
)


def test_glue_table_iceberg_ready():
    """Test Iceberg table is marked as READY."""
    table = GlueTable(
        database_name="analytics",
        table_name="events",
        table_format="ICEBERG",
        storage_location="s3://bucket/path/",
        estimated_size_gb=100.5,
        partition_keys=["date", "region"],
        column_count=42,
        last_updated=datetime(2026, 1, 8, 10, 0, 0, tzinfo=timezone.utc),
        is_iceberg=True,
        migration_readiness="READY",
        notes=[],
    )

    assert table.database_name == "analytics"
    assert table.is_iceberg is True
    assert table.migration_readiness == "READY"


def test_glue_table_parquet_needs_conversion():
    """Test Parquet table is marked as NEEDS_CONVERSION."""
    table = GlueTable(
        database_name="logs",
        table_name="access_logs",
        table_format="PARQUET",
        storage_location="s3://bucket/logs/",
        estimated_size_gb=None,
        partition_keys=["year", "month"],
        column_count=15,
        last_updated=None,
        is_iceberg=False,
        migration_readiness="NEEDS_CONVERSION",
        notes=["Non-Iceberg format requires conversion"],
    )

    assert table.table_format == "PARQUET"
    assert table.is_iceberg is False
    assert table.migration_readiness == "NEEDS_CONVERSION"


def test_glue_table_validation_fails_missing_fields():
    """Test validation fails when required fields are missing."""
    with pytest.raises(ValidationError):
        GlueTable(
            database_name="test",
            # Missing required fields
        )


def test_glue_database():
    """Test GlueDatabase model."""
    db = GlueDatabase(
        database_name="analytics_prod",
        description="Production analytics tables",
        location_uri="s3://my-bucket/analytics/",
        table_count=245,
    )

    assert db.database_name == "analytics_prod"
    assert db.table_count == 245


def test_assessment_metadata():
    """Test AssessmentMetadata model."""
    metadata = AssessmentMetadata(
        timestamp=datetime(2026, 1, 8, 14, 30, 0, tzinfo=timezone.utc),
        region="us-east-1",
        aws_account_id="123456789012",
        tool_version="0.1.0",
    )

    assert metadata.region == "us-east-1"
    assert metadata.tool_version == "0.1.0"


def test_assessment_summary():
    """Test AssessmentSummary model."""
    summary = AssessmentSummary(
        total_databases=12,
        total_tables=847,
        iceberg_tables=623,
        migration_ready=623,
        needs_conversion=224,
        unknown=0,
        total_estimated_size_gb=15200.0,
    )

    assert summary.total_tables == 847
    assert summary.iceberg_tables == 623


def test_assessment_report():
    """Test AssessmentReport model integrates all components."""
    metadata = AssessmentMetadata(
        timestamp=datetime(2026, 1, 8, 14, 30, 0, tzinfo=timezone.utc),
        region="us-east-1",
        aws_account_id="123456789012",
        tool_version="0.1.0",
    )

    summary = AssessmentSummary(
        total_databases=1,
        total_tables=1,
        iceberg_tables=1,
        migration_ready=1,
        needs_conversion=0,
        unknown=0,
        total_estimated_size_gb=100.5,
    )

    database = GlueDatabase(
        database_name="test_db",
        description=None,
        location_uri=None,
        table_count=1,
    )

    table = GlueTable(
        database_name="test_db",
        table_name="test_table",
        table_format="ICEBERG",
        storage_location="s3://bucket/path/",
        estimated_size_gb=100.5,
        partition_keys=[],
        column_count=10,
        last_updated=None,
        is_iceberg=True,
        migration_readiness="READY",
        notes=[],
    )

    report = AssessmentReport(
        assessment_metadata=metadata,
        summary=summary,
        databases=[database],
        tables=[table],
    )

    assert len(report.databases) == 1
    assert len(report.tables) == 1
    assert report.summary.total_tables == 1
