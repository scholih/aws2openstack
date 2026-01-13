"""Tests for MCP server tools."""

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aws2openstack.persistence.base import Base
from aws2openstack.persistence.models import Assessment, GlueDatabase, GlueTable
from aws2openstack.persistence.repository import AssessmentRepository
from aws2openstack.mcp_server.tools import (
    get_latest_assessment_impl,
    query_tables_by_readiness_impl,
    get_database_summary_impl,
    search_tables_impl,
    get_tables_by_format_impl,
    compare_assessments_impl,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repository(session):
    """Create repository instance for testing."""
    return AssessmentRepository(session)


@pytest.fixture
def sample_assessment_with_tables(repository):
    """Create a complete assessment with databases and tables."""
    # Create assessment
    assessment = Assessment(
        timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
        region="us-east-1",
        aws_account_id="123456789012",
        tool_version="0.1.0",
        services=["glue"],
        status="completed",
    )
    assessment = repository.save_assessment(assessment)

    # Create databases
    db1 = GlueDatabase(
        assessment=assessment, database_name="analytics", table_count=3
    )
    db1 = repository.save_glue_database(db1)

    db2 = GlueDatabase(assessment=assessment, database_name="logs", table_count=1)
    db2 = repository.save_glue_database(db2)

    # Create tables
    table1 = GlueTable(
        database=db1,
        assessment=assessment,
        table_name="sales_data",
        table_format="parquet",
        storage_location="s3://bucket/sales/",
        estimated_size_gb=Decimal("100.0"),
        partition_keys=["year", "month"],
        column_count=15,
        is_iceberg=False,
        migration_readiness="ready",
    )
    repository.save_glue_table(table1)

    table2 = GlueTable(
        database=db1,
        assessment=assessment,
        table_name="customer_data",
        table_format="iceberg",
        storage_location="s3://bucket/customers/",
        estimated_size_gb=Decimal("50.0"),
        partition_keys=[],
        column_count=10,
        is_iceberg=True,
        migration_readiness="ready",
    )
    repository.save_glue_table(table2)

    table3 = GlueTable(
        database=db1,
        assessment=assessment,
        table_name="orders_legacy",
        table_format="orc",
        storage_location="s3://bucket/orders/",
        estimated_size_gb=Decimal("200.0"),
        partition_keys=["year"],
        column_count=20,
        is_iceberg=False,
        migration_readiness="needs_conversion",
    )
    repository.save_glue_table(table3)

    table4 = GlueTable(
        database=db2,
        assessment=assessment,
        table_name="access_logs",
        table_format="parquet",
        storage_location="s3://bucket/logs/",
        estimated_size_gb=Decimal("500.0"),
        partition_keys=["date"],
        column_count=8,
        is_iceberg=False,
        migration_readiness="ready",
    )
    repository.save_glue_table(table4)

    return assessment


class TestGetLatestAssessment:
    """Test get_latest_assessment tool."""

    def test_get_latest_assessment_success(
        self, repository, sample_assessment_with_tables
    ):
        """Test retrieving latest assessment."""
        result_json = get_latest_assessment_impl(
            repository, {"region": "us-east-1"}
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["assessment"]["region"] == "us-east-1"
        assert result["assessment"]["account_id"] == "123456789012"
        assert result["assessment"]["summary"]["database_count"] == 2
        assert result["assessment"]["summary"]["table_count"] == 4

    def test_get_latest_assessment_not_found(self, repository):
        """Test when no assessment exists."""
        result_json = get_latest_assessment_impl(
            repository, {"region": "eu-west-1"}
        )
        result = json.loads(result_json)

        assert result["success"] is False
        assert "No assessment found" in result["error"]

    def test_get_latest_assessment_with_account_filter(
        self, repository, sample_assessment_with_tables
    ):
        """Test filtering by account ID."""
        result_json = get_latest_assessment_impl(
            repository, {"region": "us-east-1", "account_id": "123456789012"}
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["assessment"]["account_id"] == "123456789012"


class TestQueryTablesByReadiness:
    """Test query_tables_by_readiness tool."""

    def test_query_ready_tables(self, repository, sample_assessment_with_tables):
        """Test querying tables by readiness status."""
        result_json = query_tables_by_readiness_impl(
            repository,
            {
                "assessment_id": str(sample_assessment_with_tables.id),
                "readiness": "ready",
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["count"] == 3
        assert result["readiness"] == "ready"
        assert all(t["readiness"] == "ready" for t in result["tables"])

    def test_query_needs_conversion_tables(
        self, repository, sample_assessment_with_tables
    ):
        """Test querying tables needing conversion."""
        result_json = query_tables_by_readiness_impl(
            repository,
            {
                "assessment_id": str(sample_assessment_with_tables.id),
                "readiness": "needs_conversion",
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tables"][0]["table_name"] == "orders_legacy"

    def test_query_invalid_assessment_id(self, repository):
        """Test with invalid assessment ID."""
        result_json = query_tables_by_readiness_impl(
            repository, {"assessment_id": "invalid-uuid", "readiness": "ready"}
        )
        result = json.loads(result_json)

        assert result["success"] is False


class TestGetDatabaseSummary:
    """Test get_database_summary tool."""

    def test_get_summary_success(self, repository, sample_assessment_with_tables):
        """Test getting database summary."""
        result_json = get_database_summary_impl(
            repository, {"assessment_id": str(sample_assessment_with_tables.id)}
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["summary"]["database_count"] == 2
        assert result["summary"]["table_count"] == 4
        assert result["summary"]["total_estimated_size_gb"] == 850.0
        assert result["summary"]["iceberg_table_count"] == 1

    def test_get_summary_not_found(self, repository):
        """Test with non-existent assessment."""
        from uuid import uuid4

        result_json = get_database_summary_impl(
            repository, {"assessment_id": str(uuid4())}
        )
        result = json.loads(result_json)

        assert result["success"] is False
        assert "not found" in result["error"]


class TestSearchTables:
    """Test search_tables tool."""

    def test_search_by_table_name(self, repository, sample_assessment_with_tables):
        """Test searching tables by name pattern."""
        result_json = search_tables_impl(
            repository,
            {
                "assessment_id": str(sample_assessment_with_tables.id),
                "pattern": "%data%",
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["count"] == 2  # sales_data, customer_data
        table_names = {t["table_name"] for t in result["tables"]}
        assert "sales_data" in table_names
        assert "customer_data" in table_names

    def test_search_no_matches(self, repository, sample_assessment_with_tables):
        """Test search with no matches."""
        result_json = search_tables_impl(
            repository,
            {
                "assessment_id": str(sample_assessment_with_tables.id),
                "pattern": "%nonexistent%",
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["count"] == 0


class TestGetTablesByFormat:
    """Test get_tables_by_format tool."""

    def test_get_parquet_tables(self, repository, sample_assessment_with_tables):
        """Test getting tables by format."""
        result_json = get_tables_by_format_impl(
            repository,
            {
                "assessment_id": str(sample_assessment_with_tables.id),
                "format": "parquet",
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["count"] == 2  # sales_data, access_logs
        assert result["format"] == "parquet"
        assert result["total_size_gb"] == 600.0

    def test_get_iceberg_tables(self, repository, sample_assessment_with_tables):
        """Test getting Iceberg tables."""
        result_json = get_tables_by_format_impl(
            repository,
            {
                "assessment_id": str(sample_assessment_with_tables.id),
                "format": "iceberg",
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tables"][0]["table_name"] == "customer_data"


class TestCompareAssessments:
    """Test compare_assessments tool."""

    def test_compare_assessments_success(
        self, repository, sample_assessment_with_tables
    ):
        """Test comparing two assessments."""
        # Create second assessment with changes
        assessment2 = Assessment(
            timestamp=datetime(2024, 1, 20, tzinfo=timezone.utc),
            region="us-east-1",
            aws_account_id="123456789012",
            tool_version="0.1.0",
            services=["glue"],
            status="completed",
        )
        assessment2 = repository.save_assessment(assessment2)

        # Create same databases but with one table added and one modified
        db1 = GlueDatabase(
            assessment=assessment2, database_name="analytics", table_count=4
        )
        db1 = repository.save_glue_database(db1)

        # Same table
        table1 = GlueTable(
            database=db1,
            assessment=assessment2,
            table_name="sales_data",
            table_format="parquet",
            storage_location="s3://bucket/sales/",
            estimated_size_gb=Decimal("100.0"),
            column_count=15,
            is_iceberg=False,
            migration_readiness="ready",
        )
        repository.save_glue_table(table1)

        # Modified table (format changed)
        table2 = GlueTable(
            database=db1,
            assessment=assessment2,
            table_name="customer_data",
            table_format="parquet",  # Changed from iceberg
            storage_location="s3://bucket/customers/",
            estimated_size_gb=Decimal("50.0"),
            column_count=10,
            is_iceberg=False,
            migration_readiness="ready",
        )
        repository.save_glue_table(table2)

        # New table
        table3 = GlueTable(
            database=db1,
            assessment=assessment2,
            table_name="new_table",
            table_format="iceberg",
            storage_location="s3://bucket/new/",
            estimated_size_gb=Decimal("75.0"),
            column_count=12,
            is_iceberg=True,
            migration_readiness="ready",
        )
        repository.save_glue_table(table3)

        # Compare
        result_json = compare_assessments_impl(
            repository,
            {
                "assessment_id_1": str(sample_assessment_with_tables.id),
                "assessment_id_2": str(assessment2.id),
            },
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "logs" in result["changes"]["databases_removed"]
        assert "new_table" in [
            t.split(".")[-1] for t in result["changes"]["tables_added"]
        ]
        assert len(result["changes"]["tables_modified"]) >= 1

    def test_compare_assessments_not_found(self, repository):
        """Test comparing with non-existent assessment."""
        from uuid import uuid4

        result_json = compare_assessments_impl(
            repository,
            {"assessment_id_1": str(uuid4()), "assessment_id_2": str(uuid4())},
        )
        result = json.loads(result_json)

        assert result["success"] is False
        assert "not found" in result["error"]
