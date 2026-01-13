"""Tests for SQLAlchemy persistence models."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

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


class TestAssessmentModel:
    """Test Assessment model creation and fields."""

    def test_create_assessment(self):
        """Test creating an Assessment instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-east-1",
            aws_account_id="123456789012",
            tool_version="0.1.0",
            services=["glue"],
        )

        assert assessment.region == "us-east-1"
        assert assessment.aws_account_id == "123456789012"
        assert assessment.tool_version == "0.1.0"
        assert assessment.services == ["glue"]
        assert assessment.status is None  # Default set by database

    def test_assessment_repr(self):
        """Test Assessment string representation."""
        now = datetime.now(timezone.utc)
        assessment = Assessment(
            timestamp=now,
            region="eu-west-1",
            aws_account_id="999888777666",
            tool_version="0.2.0",
            services=["glue", "s3"],
        )

        repr_str = repr(assessment)
        assert "Assessment" in repr_str
        assert "999888777666" in repr_str
        assert "eu-west-1" in repr_str


class TestMappingTemplateModel:
    """Test MappingTemplate model creation and fields."""

    def test_create_mapping_template(self):
        """Test creating a MappingTemplate instance."""
        template = MappingTemplate(
            name="Glue to Trino",
            source_service="glue",
            source_type="catalog",
            rules={"format": "iceberg", "target": "trino"},
        )

        assert template.name == "Glue to Trino"
        assert template.source_service == "glue"
        assert template.source_type == "catalog"
        assert template.rules == {"format": "iceberg", "target": "trino"}


class TestGlueDatabaseModel:
    """Test GlueDatabase model creation and fields."""

    def test_create_glue_database(self):
        """Test creating a GlueDatabase instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-west-2",
            aws_account_id="111222333444",
            tool_version="0.1.0",
            services=["glue"],
        )

        database = GlueDatabase(
            assessment=assessment,
            database_name="analytics_db",
            description="Analytics database",
            location_uri="s3://my-bucket/warehouse/",
            table_count=42,
        )

        assert database.database_name == "analytics_db"
        assert database.description == "Analytics database"
        assert database.table_count == 42
        assert database.assessment == assessment


class TestGlueTableModel:
    """Test GlueTable model creation and fields."""

    def test_create_glue_table(self):
        """Test creating a GlueTable instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-west-2",
            aws_account_id="555666777888",
            tool_version="0.1.0",
            services=["glue"],
        )

        database = GlueDatabase(
            assessment=assessment,
            database_name="my_db",
            table_count=1,
        )

        table = GlueTable(
            database=database,
            assessment=assessment,
            table_name="sales_data",
            table_format="parquet",
            storage_location="s3://bucket/path/",
            estimated_size_gb=Decimal("123.45"),
            partition_keys=["year", "month"],
            column_count=15,
            is_iceberg=False,
            migration_readiness="ready",
            notes=["Large table", "High priority"],
        )

        assert table.table_name == "sales_data"
        assert table.table_format == "parquet"
        assert table.estimated_size_gb == Decimal("123.45")
        assert table.partition_keys == ["year", "month"]
        assert table.is_iceberg is False
        assert table.migration_readiness == "ready"
        assert table.notes == ["Large table", "High priority"]


class TestMigrationJobModel:
    """Test MigrationJob model creation and fields."""

    def test_create_migration_job(self):
        """Test creating a MigrationJob instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="ap-south-1",
            aws_account_id="123123123123",
            tool_version="0.1.0",
            services=["glue"],
        )

        database = GlueDatabase(
            assessment=assessment,
            database_name="test_db",
            table_count=1,
        )

        job = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="full_copy",
            status="running",
            sync_mode="one_time",
        )

        assert job.resource_type == "glue_table"
        assert job.job_type == "full_copy"
        assert job.status == "running"
        assert job.sync_mode == "one_time"


class TestValidationResultModel:
    """Test ValidationResult model creation and fields."""

    def test_create_validation_result(self):
        """Test creating a ValidationResult instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="eu-central-1",
            aws_account_id="999111222333",
            tool_version="0.1.0",
            services=["glue"],
        )

        database = GlueDatabase(
            assessment=assessment,
            database_name="val_db",
            table_count=1,
        )

        job = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="validation",
            status="completed",
        )

        validation = ValidationResult(
            migration_job=job,
            validation_type="row_count",
            status="passed",
            source_value="1000000",
            target_value="1000000",
            difference="0",
        )

        assert validation.validation_type == "row_count"
        assert validation.status == "passed"
        assert validation.source_value == "1000000"
        assert validation.target_value == "1000000"


class TestIAMRoleModel:
    """Test IAMRole model creation and fields."""

    def test_create_iam_role(self):
        """Test creating an IAMRole instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-east-2",
            aws_account_id="444555666777",
            tool_version="0.1.0",
            services=["iam"],
        )

        role = IAMRole(
            assessment=assessment,
            role_name="GlueServiceRole",
            role_arn="arn:aws:iam::444555666777:role/GlueServiceRole",
            policy_document={"Version": "2012-10-17", "Statement": []},
            used_by_services=["glue", "s3"],
        )

        assert role.role_name == "GlueServiceRole"
        assert "GlueServiceRole" in role.role_arn
        assert role.used_by_services == ["glue", "s3"]


class TestVPCResourceModel:
    """Test VPCResource model creation and fields."""

    def test_create_vpc_resource(self):
        """Test creating a VPCResource instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="ca-central-1",
            aws_account_id="888999000111",
            tool_version="0.1.0",
            services=["vpc"],
        )

        vpc = VPCResource(
            assessment=assessment,
            vpc_id="vpc-12345678",
            subnet_ids=["subnet-aaa", "subnet-bbb"],
            security_group_ids=["sg-xxx", "sg-yyy"],
            resource_type="glue_endpoint",
            meta={"az": "ca-central-1a"},
        )

        assert vpc.vpc_id == "vpc-12345678"
        assert vpc.subnet_ids == ["subnet-aaa", "subnet-bbb"]
        assert vpc.security_group_ids == ["sg-xxx", "sg-yyy"]
        assert vpc.meta == {"az": "ca-central-1a"}


class TestTransformationResultModel:
    """Test TransformationResult model creation and fields."""

    def test_create_transformation_result(self):
        """Test creating a TransformationResult instance."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-west-1",
            aws_account_id="222333444555",
            tool_version="0.1.0",
            services=["glue"],
        )

        template = MappingTemplate(
            name="Basic Transform",
            source_service="glue",
            source_type="table",
            rules={"action": "copy"},
        )

        result = TransformationResult(
            assessment=assessment,
            template=template,
            terraform_output_path="/path/to/terraform/",
            target_catalog_type="iceberg_rest",
            status="completed",
            meta={"tables_processed": 10},
        )

        assert result.terraform_output_path == "/path/to/terraform/"
        assert result.target_catalog_type == "iceberg_rest"
        assert result.status == "completed"
        assert result.meta == {"tables_processed": 10}


class TestModelRelationships:
    """Test relationships between models."""

    def test_assessment_glue_database_relationship(self):
        """Test Assessment -> GlueDatabase relationship."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-east-1",
            aws_account_id="123456789012",
            tool_version="0.1.0",
            services=["glue"],
        )

        db1 = GlueDatabase(
            assessment=assessment,
            database_name="db1",
            table_count=5,
        )

        db2 = GlueDatabase(
            assessment=assessment,
            database_name="db2",
            table_count=10,
        )

        # Relationship automatically populated via back_populates
        assert len(assessment.glue_databases) == 2
        assert db1.assessment == assessment
        assert db2.assessment == assessment

    def test_glue_database_tables_relationship(self):
        """Test GlueDatabase -> GlueTable relationship."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="us-west-2",
            aws_account_id="987654321098",
            tool_version="0.1.0",
            services=["glue"],
        )

        database = GlueDatabase(
            assessment=assessment,
            database_name="test_db",
            table_count=2,
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

        # Relationship automatically populated via back_populates
        assert len(database.tables) == 2
        assert table1.database == database
        assert table2.database == database

    def test_migration_job_validation_results_relationship(self):
        """Test MigrationJob -> ValidationResult relationship."""
        assessment = Assessment(
            timestamp=datetime.now(timezone.utc),
            region="eu-west-1",
            aws_account_id="111222333444",
            tool_version="0.1.0",
            services=["glue"],
        )

        database = GlueDatabase(
            assessment=assessment,
            database_name="rel_db",
            table_count=1,
        )

        job = MigrationJob(
            assessment=assessment,
            resource_type="glue_table",
            resource_id=database.id,
            job_type="full_copy",
            status="completed",
        )

        val1 = ValidationResult(
            migration_job=job,
            validation_type="row_count",
            status="passed",
        )

        val2 = ValidationResult(
            migration_job=job,
            validation_type="checksum",
            status="passed",
        )

        # Relationship automatically populated via back_populates
        assert len(job.validation_results) == 2
        assert val1.migration_job == job
        assert val2.migration_job == job
