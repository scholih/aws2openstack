"""SQLAlchemy ORM models for PostgreSQL database."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from aws2openstack.persistence.base import Base


class Assessment(Base):
    """Assessment run metadata and summary.

    Tracks a single execution of the assessment tool against an AWS account.
    Links to all discovered resources (databases, tables, IAM roles, VPCs).
    """

    __tablename__ = "assessments"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    region = Column(String(50), nullable=False)
    aws_account_id = Column(String(12), nullable=False)
    tool_version = Column(String(20), nullable=False)
    services = Column(ARRAY(Text), nullable=False)
    status = Column(String(20), server_default="completed")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships with cascade deletes
    glue_databases = relationship(
        "GlueDatabase",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    glue_tables = relationship(
        "GlueTable",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    transformation_results = relationship(
        "TransformationResult",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    migration_jobs = relationship(
        "MigrationJob",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    iam_roles = relationship(
        "IAMRole",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    vpc_resources = relationship(
        "VPCResource",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Assessment(id={self.id}, account={self.aws_account_id}, "
            f"region={self.region}, timestamp={self.timestamp})>"
        )


class MappingTemplate(Base):
    """Rule-based transformation template.

    Defines transformation rules for converting AWS resources to OpenStack equivalents.
    Rules stored as JSON for flexibility.
    """

    __tablename__ = "mapping_templates"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name = Column(String(100), nullable=False)
    source_service = Column(String(50), nullable=False)
    source_type = Column(String(50), nullable=False)
    rules = Column(JSON, nullable=False)
    version = Column(Integer, server_default="1")
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    transformation_results = relationship(
        "TransformationResult", back_populates="template"
    )

    def __repr__(self) -> str:
        return (
            f"<MappingTemplate(id={self.id}, name={self.name}, "
            f"service={self.source_service}, type={self.source_type})>"
        )


class TransformationResult(Base):
    """Terraform generation result.

    Tracks the output of transformation from AWS resources to Terraform code.
    """

    __tablename__ = "transformation_results"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id = Column(PG_UUID(as_uuid=True), ForeignKey("mapping_templates.id"))
    terraform_output_path = Column(Text, nullable=False)
    target_catalog_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    meta = Column("metadata", JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    assessment = relationship("Assessment", back_populates="transformation_results")
    template = relationship("MappingTemplate", back_populates="transformation_results")

    def __repr__(self) -> str:
        return (
            f"<TransformationResult(id={self.id}, assessment_id={self.assessment_id}, "
            f"catalog_type={self.target_catalog_type}, status={self.status})>"
        )


class MigrationJob(Base):
    """Data migration job tracking.

    Tracks individual data migration jobs including:
    - Big bang migration: single job with completion tracking
    - Shadow running: ongoing sync with last_sync_timestamp and validation
    """

    __tablename__ = "migration_jobs"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(PG_UUID(as_uuid=True), nullable=False)
    job_type = Column(String(50), nullable=False)
    aws_job_id = Column(String(255))
    status = Column(String(20), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    bytes_copied = Column(BigInteger)
    rows_copied = Column(BigInteger)
    error_message = Column(Text)
    meta = Column("metadata", JSON)

    # Shadow running support
    sync_mode = Column(String(20))
    last_sync_timestamp = Column(TIMESTAMP(timezone=True))

    # Validation support
    validation_status = Column(String(20))
    last_validated_at = Column(TIMESTAMP(timezone=True))
    validation_details = Column(JSON)

    # Relationships
    assessment = relationship("Assessment", back_populates="migration_jobs")
    validation_results = relationship(
        "ValidationResult",
        back_populates="migration_job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<MigrationJob(id={self.id}, resource_type={self.resource_type}, "
            f"status={self.status}, sync_mode={self.sync_mode})>"
        )


class ValidationResult(Base):
    """Data quality validation result.

    Tracks validation outcomes for data quality checks during migration.
    Supports 5 validation types:
    - row_count: Verify row counts match
    - checksum: Data integrity verification
    - schema: Schema structure validation
    - statistical: Statistical distribution checks
    - sample: Sample data comparison
    """

    __tablename__ = "validation_results"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    migration_job_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("migration_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    validation_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    source_value = Column(Text)
    target_value = Column(Text)
    difference = Column(Text)
    validated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    migration_job = relationship("MigrationJob", back_populates="validation_results")

    def __repr__(self) -> str:
        return (
            f"<ValidationResult(id={self.id}, type={self.validation_type}, "
            f"status={self.status})>"
        )


class GlueDatabase(Base):
    """AWS Glue database metadata.

    Represents a Glue Data Catalog database discovered during assessment.
    """

    __tablename__ = "glue_databases"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    database_name = Column(String(255), nullable=False)
    description = Column(Text)
    location_uri = Column(Text)
    table_count = Column(Integer, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="glue_databases")
    tables = relationship(
        "GlueTable",
        back_populates="database",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<GlueDatabase(id={self.id}, name={self.database_name}, "
            f"table_count={self.table_count})>"
        )


class GlueTable(Base):
    """AWS Glue table metadata.

    Represents a Glue Data Catalog table with migration readiness assessment.
    Includes format detection (Parquet, ORC, Iceberg) and migration complexity.
    """

    __tablename__ = "glue_tables"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    database_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("glue_databases.id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    table_name = Column(String(255), nullable=False)
    table_format = Column(String(50), nullable=False)
    storage_location = Column(Text, nullable=False)
    estimated_size_gb = Column(Numeric(12, 2))
    partition_keys = Column(ARRAY(Text))
    column_count = Column(Integer, nullable=False)
    last_updated = Column(TIMESTAMP(timezone=True))
    is_iceberg = Column(Boolean, nullable=False)
    migration_readiness = Column(String(20), nullable=False)
    notes = Column(ARRAY(Text))

    # Relationships
    database = relationship("GlueDatabase", back_populates="tables")
    assessment = relationship("Assessment", back_populates="glue_tables")

    def __repr__(self) -> str:
        return (
            f"<GlueTable(id={self.id}, name={self.table_name}, "
            f"format={self.table_format}, readiness={self.migration_readiness})>"
        )


class IAMRole(Base):
    """AWS IAM role metadata.

    Infrastructure context for migration - tracks IAM roles used by services.
    """

    __tablename__ = "iam_roles"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_name = Column(String(255), nullable=False)
    role_arn = Column(Text, nullable=False)
    policy_document = Column(JSON)
    used_by_services = Column(ARRAY(Text))

    # Relationships
    assessment = relationship("Assessment", back_populates="iam_roles")

    def __repr__(self) -> str:
        return f"<IAMRole(id={self.id}, name={self.role_name})>"


class VPCResource(Base):
    """AWS VPC resource metadata.

    Infrastructure context for migration - tracks VPC configuration.
    """

    __tablename__ = "vpc_resources"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    assessment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    vpc_id = Column(String(50), nullable=False)
    subnet_ids = Column(ARRAY(Text))
    security_group_ids = Column(ARRAY(Text))
    resource_type = Column(String(50))
    meta = Column("metadata", JSON)

    # Relationships
    assessment = relationship("Assessment", back_populates="vpc_resources")

    def __repr__(self) -> str:
        return f"<VPCResource(id={self.id}, vpc_id={self.vpc_id})>"
