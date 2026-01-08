"""Tests for report generators."""

import json
from pathlib import Path
from datetime import datetime, timezone

import pytest

from aws2openstack.models.catalog import (
    AssessmentMetadata,
    AssessmentSummary,
    AssessmentReport,
    GlueDatabase,
    GlueTable,
)
from aws2openstack.reporters.json_reporter import JSONReporter


@pytest.fixture
def sample_report():
    """Create a sample assessment report."""
    metadata = AssessmentMetadata(
        timestamp=datetime(2026, 1, 8, 14, 30, 0, tzinfo=timezone.utc),
        region="us-east-1",
        aws_account_id="123456789012",
        tool_version="0.1.0",
    )

    summary = AssessmentSummary(
        total_databases=1,
        total_tables=2,
        iceberg_tables=1,
        migration_ready=1,
        needs_conversion=1,
        unknown=0,
        total_estimated_size_gb=150.5,
    )

    database = GlueDatabase(
        database_name="test_db",
        description="Test database",
        location_uri="s3://bucket/db/",
        table_count=2,
    )

    table1 = GlueTable(
        database_name="test_db",
        table_name="iceberg_table",
        table_format="ICEBERG",
        storage_location="s3://bucket/iceberg/",
        estimated_size_gb=100.5,
        partition_keys=["date"],
        column_count=10,
        last_updated=datetime(2026, 1, 7, 10, 0, 0, tzinfo=timezone.utc),
        is_iceberg=True,
        migration_readiness="READY",
        notes=[],
    )

    table2 = GlueTable(
        database_name="test_db",
        table_name="parquet_table",
        table_format="PARQUET",
        storage_location="s3://bucket/parquet/",
        estimated_size_gb=50.0,
        partition_keys=["year", "month"],
        column_count=5,
        last_updated=None,
        is_iceberg=False,
        migration_readiness="NEEDS_CONVERSION",
        notes=["PARQUET format requires conversion to Iceberg"],
    )

    return AssessmentReport(
        assessment_metadata=metadata,
        summary=summary,
        databases=[database],
        tables=[table1, table2],
    )


def test_json_reporter_generate(sample_report, tmp_path):
    """Test JSON report generation."""
    output_path = tmp_path / "test-report.json"

    reporter = JSONReporter()
    reporter.generate(sample_report, output_path)

    assert output_path.exists()

    # Verify JSON structure
    with open(output_path) as f:
        data = json.load(f)

    assert data["assessment_metadata"]["region"] == "us-east-1"
    assert data["summary"]["total_tables"] == 2
    assert len(data["databases"]) == 1
    assert len(data["tables"]) == 2


def test_json_reporter_valid_json(sample_report, tmp_path):
    """Test generated JSON is valid and parseable."""
    output_path = tmp_path / "test-report.json"

    reporter = JSONReporter()
    reporter.generate(sample_report, output_path)

    # Should not raise exception
    with open(output_path) as f:
        data = json.load(f)

    assert isinstance(data, dict)


from aws2openstack.reporters.markdown_reporter import MarkdownReporter


def test_markdown_reporter_generate(sample_report, tmp_path):
    """Test Markdown report generation."""
    output_path = tmp_path / "test-report.md"

    reporter = MarkdownReporter()
    reporter.generate(sample_report, output_path)

    assert output_path.exists()

    # Verify content
    content = output_path.read_text()
    assert "# AWS Glue Catalog Assessment" in content
    assert "us-east-1" in content
    assert "123456789012" in content
    assert "test_db" in content
    assert "iceberg_table" in content
    assert "parquet_table" in content


def test_markdown_reporter_includes_summary(sample_report, tmp_path):
    """Test Markdown report includes executive summary."""
    output_path = tmp_path / "test-report.md"

    reporter = MarkdownReporter()
    reporter.generate(sample_report, output_path)

    content = output_path.read_text()
    assert "## Executive Summary" in content
    assert "Total Tables:** 2" in content
    assert "Iceberg Tables:** 1" in content
    assert "Migration Ready:** 1" in content


def test_markdown_reporter_includes_recommendations(sample_report, tmp_path):
    """Test Markdown report includes recommendations."""
    output_path = tmp_path / "test-report.md"

    reporter = MarkdownReporter()
    reporter.generate(sample_report, output_path)

    content = output_path.read_text()
    assert "## Recommendations" in content
