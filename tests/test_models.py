"""Tests for catalog data models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aws2openstack.models.catalog import GlueTable


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
