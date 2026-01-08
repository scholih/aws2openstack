"""AWS Glue Catalog assessment."""

from datetime import datetime, timezone

import boto3

from aws2openstack import __version__
from aws2openstack.models.catalog import (
    AssessmentMetadata,
    AssessmentReport,
    AssessmentSummary,
    GlueDatabase,
    GlueTable,
)


class GlueCatalogAssessor:
    """Assess AWS Glue Catalog for migration readiness."""

    def __init__(self, region: str, profile: str | None = None) -> None:
        """Initialize the assessor with AWS credentials.

        Args:
            region: AWS region to assess
            profile: Optional AWS profile name (uses default credential chain if None)
        """
        self.region = region

        if profile:
            session = boto3.Session(profile_name=profile)
            self.glue_client = session.client("glue", region_name=region)
            sts_client = session.client("sts", region_name=region)
        else:
            self.glue_client = boto3.client("glue", region_name=region)
            sts_client = boto3.client("sts", region_name=region)

        # Get AWS account ID
        caller_identity = sts_client.get_caller_identity()
        self.aws_account_id = caller_identity["Account"]

    def list_databases(self) -> list[GlueDatabase]:
        """List all databases in the Glue Catalog.

        Returns:
            List of GlueDatabase objects
        """
        databases: list[GlueDatabase] = []
        next_token = None

        while True:
            if next_token:
                response = self.glue_client.get_databases(NextToken=next_token)
            else:
                response = self.glue_client.get_databases()

            for db_dict in response.get("DatabaseList", []):
                database = GlueDatabase(
                    database_name=db_dict["Name"],
                    description=db_dict.get("Description"),
                    location_uri=db_dict.get("LocationUri"),
                    table_count=0,  # Will be updated when we count tables
                )
                databases.append(database)

            next_token = response.get("NextToken")
            if not next_token:
                break

        return databases

    def list_tables(self, database_name: str) -> list[GlueTable]:
        """List all tables in a database.

        Args:
            database_name: Name of the database

        Returns:
            List of GlueTable objects
        """
        tables: list[GlueTable] = []
        next_token = None

        while True:
            if next_token:
                response = self.glue_client.get_tables(
                    DatabaseName=database_name,
                    NextToken=next_token,
                )
            else:
                response = self.glue_client.get_tables(DatabaseName=database_name)

            for table_dict in response.get("TableList", []):
                table = self._parse_table(database_name, table_dict)
                tables.append(table)

            next_token = response.get("NextToken")
            if not next_token:
                break

        return tables

    def _parse_table(self, database_name: str, table_dict: dict) -> GlueTable:
        """Parse Glue table metadata into GlueTable model.

        Args:
            database_name: Name of the database
            table_dict: Raw table metadata from Glue API

        Returns:
            GlueTable object
        """
        table_name = table_dict["Name"]
        storage_desc = table_dict.get("StorageDescriptor", {})
        parameters = table_dict.get("Parameters", {})

        # Extract basic info
        storage_location = storage_desc.get("Location", "")
        columns = storage_desc.get("Columns", [])
        column_count = len(columns)
        partition_keys = [pk["Name"] for pk in table_dict.get("PartitionKeys", [])]

        # Determine table format
        table_type = parameters.get("table_type", "").upper()
        if table_type == "ICEBERG":
            table_format = "ICEBERG"
            is_iceberg = True
        else:
            # Try to infer from SerDe or InputFormat
            input_format = storage_desc.get("InputFormat", "")
            if "parquet" in input_format.lower():
                table_format = "PARQUET"
            elif "orc" in input_format.lower():
                table_format = "ORC"
            else:
                table_format = "UNKNOWN"
            is_iceberg = False

        # Get size estimate (if available)
        estimated_size_gb = None
        # Note: Size statistics may be in Parameters as 'numBytes' or similar
        # For now, we'll leave as None and enhance later if needed

        # Get last updated time
        last_updated = table_dict.get("UpdateTime")
        if last_updated and not isinstance(last_updated, datetime):
            # If it's not already a datetime, try to parse it
            last_updated = None

        # Determine migration readiness
        migration_readiness, notes = self._assess_migration_readiness(
            is_iceberg, table_format, storage_location
        )

        return GlueTable(
            database_name=database_name,
            table_name=table_name,
            table_format=table_format,
            storage_location=storage_location,
            estimated_size_gb=estimated_size_gb,
            partition_keys=partition_keys,
            column_count=column_count,
            last_updated=last_updated,
            is_iceberg=is_iceberg,
            migration_readiness=migration_readiness,
            notes=notes,
        )

    def _assess_migration_readiness(
        self, is_iceberg: bool, table_format: str, storage_location: str
    ) -> tuple[str, list[str]]:
        """Assess migration readiness for a table.

        Args:
            is_iceberg: Whether the table is Iceberg format
            table_format: Table format string
            storage_location: S3 storage location

        Returns:
            Tuple of (readiness status, list of notes)
        """
        notes: list[str] = []

        if is_iceberg:
            if storage_location.startswith("s3://"):
                return "READY", notes
            else:
                notes.append("Non-S3 storage location")
                return "UNKNOWN", notes

        if table_format in ("PARQUET", "ORC", "AVRO"):
            notes.append(f"{table_format} format requires conversion to Iceberg")
            return "NEEDS_CONVERSION", notes

        if table_format == "UNKNOWN":
            notes.append("Unknown table format")
            return "UNKNOWN", notes

        notes.append(f"Unsupported format: {table_format}")
        return "UNKNOWN", notes

    def run_assessment(self) -> AssessmentReport:
        """Run complete Glue Catalog assessment.

        Returns:
            Complete AssessmentReport with all data
        """
        # Collect databases
        databases = self.list_databases()

        # Collect tables for each database
        all_tables: list[GlueTable] = []
        for database in databases:
            tables = self.list_tables(database.database_name)
            all_tables.extend(tables)
            # Update database table count
            database.table_count = len(tables)

        # Calculate summary statistics
        iceberg_count = sum(1 for t in all_tables if t.is_iceberg)
        ready_count = sum(1 for t in all_tables if t.migration_readiness == "READY")
        needs_conversion_count = sum(
            1 for t in all_tables if t.migration_readiness == "NEEDS_CONVERSION"
        )
        unknown_count = sum(1 for t in all_tables if t.migration_readiness == "UNKNOWN")

        total_size_gb = sum(
            t.estimated_size_gb for t in all_tables if t.estimated_size_gb is not None
        )

        # Create metadata
        metadata = AssessmentMetadata(
            timestamp=datetime.now(timezone.utc),
            region=self.region,
            aws_account_id=self.aws_account_id,
            tool_version=__version__,
        )

        # Create summary
        summary = AssessmentSummary(
            total_databases=len(databases),
            total_tables=len(all_tables),
            iceberg_tables=iceberg_count,
            migration_ready=ready_count,
            needs_conversion=needs_conversion_count,
            unknown=unknown_count,
            total_estimated_size_gb=total_size_gb,
        )

        # Create report
        return AssessmentReport(
            assessment_metadata=metadata,
            summary=summary,
            databases=databases,
            tables=all_tables,
        )
