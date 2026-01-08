"""Data models for AWS Glue Catalog."""

from datetime import datetime

from pydantic import BaseModel, Field


class GlueTable(BaseModel):
    """Represents an AWS Glue table with migration readiness info."""

    database_name: str = Field(..., description="Name of the Glue database")
    table_name: str = Field(..., description="Name of the table")
    table_format: str = Field(..., description="Table format (ICEBERG, PARQUET, ORC, etc.)")
    storage_location: str = Field(..., description="S3 storage location URI")
    estimated_size_gb: float | None = Field(
        None, description="Estimated size in GB (from Glue statistics)"
    )
    partition_keys: list[str] = Field(default_factory=list, description="Partition column names")
    column_count: int = Field(..., description="Number of columns in the table")
    last_updated: datetime | None = Field(None, description="Last update timestamp")
    is_iceberg: bool = Field(..., description="Whether the table is Iceberg format")
    migration_readiness: str = Field(
        ..., description="Migration readiness: READY, NEEDS_CONVERSION, UNKNOWN"
    )
    notes: list[str] = Field(default_factory=list, description="Additional notes or warnings")

    model_config = {"frozen": False}


class GlueDatabase(BaseModel):
    """Represents an AWS Glue database."""

    database_name: str = Field(..., description="Name of the database")
    description: str | None = Field(None, description="Database description")
    location_uri: str | None = Field(None, description="Default location URI")
    table_count: int = Field(..., description="Number of tables in this database")


class AssessmentMetadata(BaseModel):
    """Metadata about the assessment run."""

    timestamp: datetime = Field(..., description="When the assessment was run")
    region: str = Field(..., description="AWS region assessed")
    aws_account_id: str = Field(..., description="AWS account ID")
    tool_version: str = Field(..., description="Version of aws2openstack tool")


class AssessmentSummary(BaseModel):
    """Summary statistics for the assessment."""

    total_databases: int = Field(..., description="Total number of databases")
    total_tables: int = Field(..., description="Total number of tables")
    iceberg_tables: int = Field(..., description="Number of Iceberg tables")
    migration_ready: int = Field(..., description="Tables ready to migrate")
    needs_conversion: int = Field(..., description="Tables needing conversion")
    unknown: int = Field(..., description="Tables with unknown readiness")
    total_estimated_size_gb: float = Field(..., description="Total estimated storage in GB")


class AssessmentReport(BaseModel):
    """Complete assessment report with all data."""

    assessment_metadata: AssessmentMetadata
    summary: AssessmentSummary
    databases: list[GlueDatabase]
    tables: list[GlueTable]
