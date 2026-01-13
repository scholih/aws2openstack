"""Tests for repository layer."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aws2openstack.persistence.base import Base
from aws2openstack.persistence.models import (
    Assessment,
    GlueDatabase,
    GlueTable,
    IAMRole,
    MappingTemplate,
    MigrationJob,
    TransformationResult,
    ValidationResult,
    VPCResource,
)
from aws2openstack.persistence.repository import AssessmentRepository


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
def sample_assessment():
    """Create a sample assessment for testing."""
    return Assessment(
        timestamp=datetime.now(timezone.utc),
        region="us-east-1",
        aws_account_id="123456789012",
        tool_version="0.1.0",
        services=["glue"],
        status="completed",
    )


class TestAssessmentCRUD:
    """Test Assessment CRUD operations."""

    def test_save_assessment(self, repository, sample_assessment):
        """Test saving an assessment."""
        saved = repository.save_assessment(sample_assessment)

        assert saved.id is not None
        assert saved.region == "us-east-1"
        assert saved.aws_account_id == "123456789012"
        assert saved.status == "completed"

    def test_get_assessment(self, repository, sample_assessment):
        """Test retrieving assessment by ID."""
        saved = repository.save_assessment(sample_assessment)
        retrieved = repository.get_assessment(saved.id)

        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.region == saved.region

    def test_get_assessment_not_found(self, repository):
        """Test retrieving non-existent assessment returns None."""
        from uuid import uuid4

        result = repository.get_assessment(uuid4())
        assert result is None

    def test_get_latest_assessment(self, repository):
        """Test getting latest assessment."""
        # Create multiple assessments
        assessment1 = Assessment(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            region="us-east-1",
            aws_account_id="111111111111",
            tool_version="0.1.0",
            services=["glue"],
        )
        assessment2 = Assessment(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            region="us-east-1",
            aws_account_id="111111111111",
            tool_version="0.1.0",
            services=["glue"],
        )

        repository.save_assessment(assessment1)
        repository.save_assessment(assessment2)

        latest = repository.get_latest_assessment()
        # SQLite doesn't preserve timezone, so compare date/time components
        assert latest.timestamp.replace(tzinfo=None) == datetime(2024, 1, 2)

    def test_get_latest_assessment_with_filters(self, repository):
        """Test getting latest assessment with region/account filters."""
        assessment1 = Assessment(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            region="us-east-1",
            aws_account_id="111111111111",
            tool_version="0.1.0",
            services=["glue"],
        )
        assessment2 = Assessment(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            region="us-west-2",
            aws_account_id="222222222222",
            tool_version="0.1.0",
            services=["glue"],
        )

        repository.save_assessment(assessment1)
        repository.save_assessment(assessment2)

        latest_west = repository.get_latest_assessment(region="us-west-2")
        assert latest_west.region == "us-west-2"

        latest_111 = repository.get_latest_assessment(account_id="111111111111")
        assert latest_111.aws_account_id == "111111111111"

    def test_list_assessments(self, repository):
        """Test listing assessments with pagination."""
        for i in range(5):
            assessment = Assessment(
                timestamp=datetime.now(timezone.utc),
                region="us-east-1",
                aws_account_id=f"{i:012d}",
                tool_version="0.1.0",
                services=["glue"],
            )
            repository.save_assessment(assessment)

        results = repository.list_assessments(limit=3, offset=0)
        assert len(results) == 3

        results = repository.list_assessments(limit=3, offset=3)
        assert len(results) == 2

    def test_delete_assessment(self, repository, sample_assessment):
        """Test deleting an assessment."""
        saved = repository.save_assessment(sample_assessment)
        assessment_id = saved.id

        # Delete and verify
        assert repository.delete_assessment(assessment_id) is True
        assert repository.get_assessment(assessment_id) is None

    def test_delete_assessment_not_found(self, repository):
        """Test deleting non-existent assessment returns False."""
        from uuid import uuid4

        result = repository.delete_assessment(uuid4())
        assert result is False


class TestGlueDatabaseOperations:
    """Test Glue database operations."""

    def test_save_glue_database(self, repository, sample_assessment):
        """Test saving a Glue database."""
        assessment = repository.save_assessment(sample_assessment)

        database = GlueDatabase(
            assessment=assessment,
            database_name="test_db",
            description="Test database",
            location_uri="s3://bucket/warehouse/",
            table_count=5,
        )

        saved = repository.save_glue_database(database)
        assert saved.id is not None
        assert saved.database_name == "test_db"

    def test_get_glue_databases(self, repository, sample_assessment):
        """Test retrieving all databases for an assessment."""
        assessment = repository.save_assessment(sample_assessment)

        db1 = GlueDatabase(
            assessment=assessment, database_name="db1", table_count=3
        )
        db2 = GlueDatabase(
            assessment=assessment, database_name="db2", table_count=5
        )

        repository.save_glue_database(db1)
        repository.save_glue_database(db2)

        databases = repository.get_glue_databases(assessment.id)
        assert len(databases) == 2
        assert {db.database_name for db in databases} == {"db1", "db2"}


class TestGlueTableOperations:
    """Test Glue table operations."""

    def test_save_glue_table(self, repository, sample_assessment):
        """Test saving a Glue table."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )

        table = GlueTable(
            database=database,
            assessment=assessment,
            table_name="sales_data",
            table_format="parquet",
            storage_location="s3://bucket/sales/",
            estimated_size_gb=Decimal("100.50"),
            partition_keys=["year", "month"],
            column_count=15,
            is_iceberg=False,
            migration_readiness="ready",
        )

        saved = repository.save_glue_table(table)
        assert saved.id is not None
        assert saved.table_name == "sales_data"

    def test_get_glue_tables(self, repository, sample_assessment):
        """Test retrieving tables for a database."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=2)
        )

        table1 = GlueTable(
            database=database,
            assessment=assessment,
            table_name="table1",
            table_format="parquet",
            storage_location="s3://bucket/table1/",
            column_count=10,
            is_iceberg=False,
            migration_readiness="ready",
        )
        table2 = GlueTable(
            database=database,
            assessment=assessment,
            table_name="table2",
            table_format="iceberg",
            storage_location="s3://bucket/table2/",
            column_count=20,
            is_iceberg=True,
            migration_readiness="ready",
        )

        repository.save_glue_table(table1)
        repository.save_glue_table(table2)

        tables = repository.get_glue_tables(database.id)
        assert len(tables) == 2

    def test_query_tables_by_readiness(self, repository, sample_assessment):
        """Test querying tables by migration readiness."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=3)
        )

        for i, readiness in enumerate(["ready", "ready", "needs_conversion"]):
            table = GlueTable(
                database=database,
                assessment=assessment,
                table_name=f"table{i}",
                table_format="parquet",
                storage_location=f"s3://bucket/table{i}/",
                column_count=10,
                is_iceberg=False,
                migration_readiness=readiness,
            )
            repository.save_glue_table(table)

        ready_tables = repository.query_tables_by_readiness(assessment.id, "ready")
        assert len(ready_tables) == 2

        needs_conversion = repository.query_tables_by_readiness(
            assessment.id, "needs_conversion"
        )
        assert len(needs_conversion) == 1

    def test_query_tables_by_format(self, repository, sample_assessment):
        """Test querying tables by format."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=3)
        )

        for i, fmt in enumerate(["parquet", "iceberg", "parquet"]):
            table = GlueTable(
                database=database,
                assessment=assessment,
                table_name=f"table{i}",
                table_format=fmt,
                storage_location=f"s3://bucket/table{i}/",
                column_count=10,
                is_iceberg=(fmt == "iceberg"),
                migration_readiness="ready",
            )
            repository.save_glue_table(table)

        parquet_tables = repository.query_tables_by_format(assessment.id, "parquet")
        assert len(parquet_tables) == 2

        iceberg_tables = repository.query_tables_by_format(assessment.id, "iceberg")
        assert len(iceberg_tables) == 1


class TestMigrationJobOperations:
    """Test migration job operations."""

    def test_save_migration_job(self, repository, sample_assessment):
        """Test saving a migration job."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )

        job = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="full_copy",
            status="running",
            sync_mode="one_time",
        )

        saved = repository.save_migration_job(job)
        assert saved.id is not None
        assert saved.status == "running"

    def test_get_migration_jobs(self, repository, sample_assessment):
        """Test retrieving migration jobs for an assessment."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )

        job1 = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="full_copy",
            status="completed",
        )
        job2 = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="incremental",
            status="running",
        )

        repository.save_migration_job(job1)
        repository.save_migration_job(job2)

        all_jobs = repository.get_migration_jobs(assessment.id)
        assert len(all_jobs) == 2

        completed_jobs = repository.get_migration_jobs(assessment.id, status="completed")
        assert len(completed_jobs) == 1
        assert completed_jobs[0].status == "completed"

    def test_update_migration_job_status(self, repository, sample_assessment):
        """Test updating migration job status."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )

        job = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="full_copy",
            status="running",
        )
        saved = repository.save_migration_job(job)

        # Update status
        completed_at = datetime.now(timezone.utc)
        result = repository.update_migration_job_status(
            saved.id, "completed", completed_at=completed_at
        )
        assert result is True

        # Verify update
        updated = repository.get_migration_job(saved.id)
        assert updated.status == "completed"
        assert updated.completed_at is not None


class TestValidationResultOperations:
    """Test validation result operations."""

    def test_save_validation_result(self, repository, sample_assessment):
        """Test saving a validation result."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )
        job = repository.save_migration_job(
            MigrationJob(
                assessment=assessment,
                resource_type="glue_table",
                resource_id=database.id,
                job_type="full_copy",
                status="completed",
            )
        )

        validation = ValidationResult(
            migration_job=job,
            validation_type="row_count",
            status="passed",
            source_value="1000000",
            target_value="1000000",
            difference="0",
        )

        saved = repository.save_validation_result(validation)
        assert saved.id is not None
        assert saved.validation_type == "row_count"

    def test_get_validation_results(self, repository, sample_assessment):
        """Test retrieving validation results for a job."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )
        job = repository.save_migration_job(
            MigrationJob(
                assessment=assessment,
                resource_type="glue_table",
                resource_id=database.id,
                job_type="full_copy",
                status="completed",
            )
        )

        val1 = ValidationResult(
            migration_job=job,
            validation_type="row_count",
            status="passed",
        )
        val2 = ValidationResult(
            migration_job=job,
            validation_type="checksum",
            status="failed",
        )

        repository.save_validation_result(val1)
        repository.save_validation_result(val2)

        all_results = repository.get_validation_results(job.id)
        assert len(all_results) == 2

        failed_results = repository.get_validation_results(job.id, status="failed")
        assert len(failed_results) == 1
        assert failed_results[0].validation_type == "checksum"


class TestMappingTemplateOperations:
    """Test mapping template operations."""

    def test_save_mapping_template(self, repository):
        """Test saving a mapping template."""
        template = MappingTemplate(
            name="Glue to Trino",
            source_service="glue",
            source_type="catalog",
            rules={"format": "iceberg", "target": "trino"},
            is_active=True,
        )

        saved = repository.save_mapping_template(template)
        assert saved.id is not None
        assert saved.name == "Glue to Trino"

    def test_get_active_templates(self, repository):
        """Test retrieving active templates."""
        template1 = MappingTemplate(
            name="Template 1",
            source_service="glue",
            source_type="catalog",
            rules={},
            is_active=True,
        )
        template2 = MappingTemplate(
            name="Template 2",
            source_service="glue",
            source_type="catalog",
            rules={},
            is_active=False,
        )

        repository.save_mapping_template(template1)
        repository.save_mapping_template(template2)

        active = repository.get_active_templates()
        assert len(active) == 1
        assert active[0].name == "Template 1"

        active_glue = repository.get_active_templates(source_service="glue")
        assert len(active_glue) == 1


class TestInfrastructureOperations:
    """Test infrastructure context operations."""

    def test_save_and_get_iam_roles(self, repository, sample_assessment):
        """Test IAM role operations."""
        assessment = repository.save_assessment(sample_assessment)

        role = IAMRole(
            assessment=assessment,
            role_name="GlueServiceRole",
            role_arn="arn:aws:iam::123456789012:role/GlueServiceRole",
            policy_document={"Version": "2012-10-17"},
            used_by_services=["glue", "s3"],
        )

        saved = repository.save_iam_role(role)
        assert saved.id is not None

        roles = repository.get_iam_roles(assessment.id)
        assert len(roles) == 1
        assert roles[0].role_name == "GlueServiceRole"

    def test_save_and_get_vpc_resources(self, repository, sample_assessment):
        """Test VPC resource operations."""
        assessment = repository.save_assessment(sample_assessment)

        vpc = VPCResource(
            assessment=assessment,
            vpc_id="vpc-12345678",
            subnet_ids=["subnet-aaa", "subnet-bbb"],
            security_group_ids=["sg-xxx"],
            resource_type="glue_endpoint",
        )

        saved = repository.save_vpc_resource(vpc)
        assert saved.id is not None

        vpcs = repository.get_vpc_resources(assessment.id)
        assert len(vpcs) == 1
        assert vpcs[0].vpc_id == "vpc-12345678"


class TestSummaryOperations:
    """Test summary and aggregation operations."""

    def test_get_database_summary(self, repository, sample_assessment):
        """Test database summary statistics."""
        assessment = repository.save_assessment(sample_assessment)

        # Create databases and tables
        db1 = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="db1", table_count=2)
        )
        db2 = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="db2", table_count=1)
        )

        # Create tables with various attributes
        table1 = GlueTable(
            database=db1,
            assessment=assessment,
            table_name="table1",
            table_format="parquet",
            storage_location="s3://bucket/table1/",
            estimated_size_gb=Decimal("100.0"),
            column_count=10,
            is_iceberg=False,
            migration_readiness="ready",
        )
        table2 = GlueTable(
            database=db1,
            assessment=assessment,
            table_name="table2",
            table_format="iceberg",
            storage_location="s3://bucket/table2/",
            estimated_size_gb=Decimal("200.0"),
            column_count=20,
            is_iceberg=True,
            migration_readiness="ready",
        )
        table3 = GlueTable(
            database=db2,
            assessment=assessment,
            table_name="table3",
            table_format="parquet",
            storage_location="s3://bucket/table3/",
            estimated_size_gb=Decimal("50.0"),
            column_count=5,
            is_iceberg=False,
            migration_readiness="needs_conversion",
        )

        repository.save_glue_table(table1)
        repository.save_glue_table(table2)
        repository.save_glue_table(table3)

        # Get summary
        summary = repository.get_database_summary(assessment.id)

        assert summary["database_count"] == 2
        assert summary["table_count"] == 3
        assert summary["iceberg_table_count"] == 1
        assert summary["total_estimated_size_gb"] == 350.0
        assert summary["readiness_breakdown"]["ready"] == 2
        assert summary["readiness_breakdown"]["needs_conversion"] == 1
        assert summary["format_breakdown"]["parquet"] == 2
        assert summary["format_breakdown"]["iceberg"] == 1

    def test_get_migration_summary(self, repository, sample_assessment):
        """Test migration summary statistics."""
        assessment = repository.save_assessment(sample_assessment)
        database = repository.save_glue_database(
            GlueDatabase(assessment=assessment, database_name="test_db", table_count=1)
        )

        # Create migration jobs
        job1 = repository.save_migration_job(
            MigrationJob(
                assessment=assessment,
                resource_type="glue_table",
                resource_id=database.id,
                job_type="full_copy",
                status="completed",
                bytes_copied=1000000,
                rows_copied=10000,
            )
        )
        job2 = repository.save_migration_job(
            MigrationJob(
                assessment=assessment,
                resource_type="glue_table",
                resource_id=database.id,
                job_type="incremental",
                status="running",
                bytes_copied=500000,
                rows_copied=5000,
            )
        )

        # Create validation results
        repository.save_validation_result(
            ValidationResult(
                migration_job=job1,
                validation_type="row_count",
                status="passed",
            )
        )
        repository.save_validation_result(
            ValidationResult(
                migration_job=job1,
                validation_type="checksum",
                status="failed",
            )
        )

        # Get summary
        summary = repository.get_migration_summary(assessment.id)

        assert summary["status_breakdown"]["completed"] == 1
        assert summary["status_breakdown"]["running"] == 1
        assert summary["total_bytes_copied"] == 1500000
        assert summary["total_rows_copied"] == 15000
        assert summary["failed_validations"] == 1


class TestTransformationResultOperations:
    """Test transformation result operations."""

    def test_save_transformation_result(self, repository, sample_assessment):
        """Test saving a transformation result."""
        assessment = repository.save_assessment(sample_assessment)
        template = repository.save_mapping_template(
            MappingTemplate(
                name="Test Template",
                source_service="glue",
                source_type="table",
                rules={},
            )
        )

        result = TransformationResult(
            assessment=assessment,
            template=template,
            terraform_output_path="/path/to/terraform/",
            target_catalog_type="iceberg_rest",
            status="completed",
        )

        saved = repository.save_transformation_result(result)
        assert saved.id is not None
        assert saved.status == "completed"

    def test_get_transformation_results(self, repository, sample_assessment):
        """Test retrieving transformation results."""
        assessment = repository.save_assessment(sample_assessment)
        template = repository.save_mapping_template(
            MappingTemplate(
                name="Test Template",
                source_service="glue",
                source_type="table",
                rules={},
            )
        )

        result1 = TransformationResult(
            assessment=assessment,
            template=template,
            terraform_output_path="/path1/",
            target_catalog_type="iceberg_rest",
            status="completed",
        )
        result2 = TransformationResult(
            assessment=assessment,
            template=template,
            terraform_output_path="/path2/",
            target_catalog_type="hive_metastore",
            status="failed",
        )

        repository.save_transformation_result(result1)
        repository.save_transformation_result(result2)

        all_results = repository.get_transformation_results(assessment.id)
        assert len(all_results) == 2

        completed_results = repository.get_transformation_results(
            assessment.id, status="completed"
        )
        assert len(completed_results) == 1
        assert completed_results[0].target_catalog_type == "iceberg_rest"
