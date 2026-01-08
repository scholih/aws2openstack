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
