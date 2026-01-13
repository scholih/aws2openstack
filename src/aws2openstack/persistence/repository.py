"""Repository layer for data access operations.

Implements the repository pattern for clean separation between business logic
and data access. All database operations go through repositories.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

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


class AssessmentRepository:
    """Repository for assessment-related data access operations."""

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    # ========================================================================
    # Assessment CRUD Operations
    # ========================================================================

    def save_assessment(self, assessment: Assessment) -> Assessment:
        """Save or update an assessment.

        Args:
            assessment: Assessment instance to save

        Returns:
            Saved assessment with generated ID
        """
        self.session.add(assessment)
        self.session.commit()
        self.session.refresh(assessment)
        return assessment

    def get_assessment(self, assessment_id: UUID) -> Optional[Assessment]:
        """Get assessment by ID.

        Args:
            assessment_id: UUID of assessment

        Returns:
            Assessment if found, None otherwise
        """
        return self.session.query(Assessment).filter_by(id=assessment_id).first()

    def get_latest_assessment(
        self, region: Optional[str] = None, account_id: Optional[str] = None
    ) -> Optional[Assessment]:
        """Get the most recent assessment.

        Args:
            region: Optional AWS region filter
            account_id: Optional AWS account ID filter

        Returns:
            Most recent assessment matching filters, or None
        """
        query = self.session.query(Assessment)

        if region:
            query = query.filter_by(region=region)
        if account_id:
            query = query.filter_by(aws_account_id=account_id)

        return query.order_by(desc(Assessment.timestamp)).first()

    def list_assessments(
        self,
        limit: int = 100,
        offset: int = 0,
        region: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> List[Assessment]:
        """List assessments with pagination and filters.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            region: Optional region filter
            account_id: Optional account ID filter

        Returns:
            List of assessments matching filters
        """
        query = self.session.query(Assessment)

        if region:
            query = query.filter_by(region=region)
        if account_id:
            query = query.filter_by(aws_account_id=account_id)

        return (
            query.order_by(desc(Assessment.timestamp))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def delete_assessment(self, assessment_id: UUID) -> bool:
        """Delete assessment and all related data (cascade).

        Args:
            assessment_id: UUID of assessment to delete

        Returns:
            True if deleted, False if not found
        """
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return False

        self.session.delete(assessment)
        self.session.commit()
        return True

    # ========================================================================
    # Glue Database Operations
    # ========================================================================

    def save_glue_database(self, database: GlueDatabase) -> GlueDatabase:
        """Save or update a Glue database.

        Args:
            database: GlueDatabase instance to save

        Returns:
            Saved database with generated ID
        """
        self.session.add(database)
        self.session.commit()
        self.session.refresh(database)
        return database

    def get_glue_database(self, database_id: UUID) -> Optional[GlueDatabase]:
        """Get Glue database by ID.

        Args:
            database_id: UUID of database

        Returns:
            GlueDatabase if found, None otherwise
        """
        return self.session.query(GlueDatabase).filter_by(id=database_id).first()

    def get_glue_databases(
        self, assessment_id: UUID, include_tables: bool = False
    ) -> List[GlueDatabase]:
        """Get all Glue databases for an assessment.

        Args:
            assessment_id: UUID of assessment
            include_tables: Whether to eagerly load tables

        Returns:
            List of Glue databases
        """
        query = self.session.query(GlueDatabase).filter_by(
            assessment_id=assessment_id
        )

        if include_tables:
            query = query.options(joinedload(GlueDatabase.tables))

        return query.all()

    # ========================================================================
    # Glue Table Operations
    # ========================================================================

    def save_glue_table(self, table: GlueTable) -> GlueTable:
        """Save or update a Glue table.

        Args:
            table: GlueTable instance to save

        Returns:
            Saved table with generated ID
        """
        self.session.add(table)
        self.session.commit()
        self.session.refresh(table)
        return table

    def get_glue_table(self, table_id: UUID) -> Optional[GlueTable]:
        """Get Glue table by ID.

        Args:
            table_id: UUID of table

        Returns:
            GlueTable if found, None otherwise
        """
        return self.session.query(GlueTable).filter_by(id=table_id).first()

    def get_glue_tables(self, database_id: UUID) -> List[GlueTable]:
        """Get all Glue tables for a database.

        Args:
            database_id: UUID of database

        Returns:
            List of Glue tables
        """
        return self.session.query(GlueTable).filter_by(database_id=database_id).all()

    def query_tables_by_readiness(
        self, assessment_id: UUID, readiness: str
    ) -> List[GlueTable]:
        """Query tables by migration readiness status.

        Args:
            assessment_id: UUID of assessment
            readiness: Migration readiness status (e.g., 'ready', 'needs_conversion')

        Returns:
            List of tables matching readiness status
        """
        return (
            self.session.query(GlueTable)
            .filter_by(assessment_id=assessment_id, migration_readiness=readiness)
            .all()
        )

    def query_tables_by_format(
        self, assessment_id: UUID, table_format: str
    ) -> List[GlueTable]:
        """Query tables by table format.

        Args:
            assessment_id: UUID of assessment
            table_format: Table format (e.g., 'parquet', 'iceberg', 'orc')

        Returns:
            List of tables with specified format
        """
        return (
            self.session.query(GlueTable)
            .filter_by(assessment_id=assessment_id, table_format=table_format)
            .all()
        )

    # ========================================================================
    # Migration Job Operations
    # ========================================================================

    def save_migration_job(self, job: MigrationJob) -> MigrationJob:
        """Save or update a migration job.

        Args:
            job: MigrationJob instance to save

        Returns:
            Saved job with generated ID
        """
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_migration_job(self, job_id: UUID) -> Optional[MigrationJob]:
        """Get migration job by ID.

        Args:
            job_id: UUID of job

        Returns:
            MigrationJob if found, None otherwise
        """
        return self.session.query(MigrationJob).filter_by(id=job_id).first()

    def get_migration_jobs(
        self,
        assessment_id: UUID,
        status: Optional[str] = None,
        include_validation: bool = False,
    ) -> List[MigrationJob]:
        """Get migration jobs for an assessment.

        Args:
            assessment_id: UUID of assessment
            status: Optional status filter
            include_validation: Whether to eagerly load validation results

        Returns:
            List of migration jobs
        """
        query = self.session.query(MigrationJob).filter_by(assessment_id=assessment_id)

        if status:
            query = query.filter_by(status=status)

        if include_validation:
            query = query.options(joinedload(MigrationJob.validation_results))

        return query.all()

    def update_migration_job_status(
        self,
        job_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """Update migration job status.

        Args:
            job_id: UUID of job
            status: New status
            error_message: Optional error message
            completed_at: Optional completion timestamp

        Returns:
            True if updated, False if job not found
        """
        job = self.get_migration_job(job_id)
        if not job:
            return False

        job.status = status
        if error_message:
            job.error_message = error_message
        if completed_at:
            job.completed_at = completed_at

        self.session.commit()
        return True

    # ========================================================================
    # Validation Result Operations
    # ========================================================================

    def save_validation_result(
        self, validation: ValidationResult
    ) -> ValidationResult:
        """Save a validation result.

        Args:
            validation: ValidationResult instance to save

        Returns:
            Saved validation result with generated ID
        """
        self.session.add(validation)
        self.session.commit()
        self.session.refresh(validation)
        return validation

    def get_validation_results(
        self, migration_job_id: UUID, status: Optional[str] = None
    ) -> List[ValidationResult]:
        """Get validation results for a migration job.

        Args:
            migration_job_id: UUID of migration job
            status: Optional status filter

        Returns:
            List of validation results
        """
        query = self.session.query(ValidationResult).filter_by(
            migration_job_id=migration_job_id
        )

        if status:
            query = query.filter_by(status=status)

        return query.all()

    # ========================================================================
    # Mapping Template Operations
    # ========================================================================

    def save_mapping_template(self, template: MappingTemplate) -> MappingTemplate:
        """Save or update a mapping template.

        Args:
            template: MappingTemplate instance to save

        Returns:
            Saved template with generated ID
        """
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return template

    def get_active_templates(
        self, source_service: Optional[str] = None, source_type: Optional[str] = None
    ) -> List[MappingTemplate]:
        """Get active mapping templates.

        Args:
            source_service: Optional service filter
            source_type: Optional type filter

        Returns:
            List of active templates matching filters
        """
        query = self.session.query(MappingTemplate).filter_by(is_active=True)

        if source_service:
            query = query.filter_by(source_service=source_service)
        if source_type:
            query = query.filter_by(source_type=source_type)

        return query.order_by(desc(MappingTemplate.version)).all()

    # ========================================================================
    # Infrastructure Context Operations
    # ========================================================================

    def save_iam_role(self, role: IAMRole) -> IAMRole:
        """Save an IAM role.

        Args:
            role: IAMRole instance to save

        Returns:
            Saved role with generated ID
        """
        self.session.add(role)
        self.session.commit()
        self.session.refresh(role)
        return role

    def get_iam_roles(self, assessment_id: UUID) -> List[IAMRole]:
        """Get IAM roles for an assessment.

        Args:
            assessment_id: UUID of assessment

        Returns:
            List of IAM roles
        """
        return self.session.query(IAMRole).filter_by(assessment_id=assessment_id).all()

    def save_vpc_resource(self, vpc: VPCResource) -> VPCResource:
        """Save a VPC resource.

        Args:
            vpc: VPCResource instance to save

        Returns:
            Saved VPC resource with generated ID
        """
        self.session.add(vpc)
        self.session.commit()
        self.session.refresh(vpc)
        return vpc

    def get_vpc_resources(self, assessment_id: UUID) -> List[VPCResource]:
        """Get VPC resources for an assessment.

        Args:
            assessment_id: UUID of assessment

        Returns:
            List of VPC resources
        """
        return (
            self.session.query(VPCResource).filter_by(assessment_id=assessment_id).all()
        )

    # ========================================================================
    # Summary and Aggregation Operations
    # ========================================================================

    def get_database_summary(self, assessment_id: UUID) -> Dict[str, Any]:
        """Get summary statistics for databases in an assessment.

        Args:
            assessment_id: UUID of assessment

        Returns:
            Dictionary with summary statistics
        """
        # Count databases
        db_count = (
            self.session.query(func.count(GlueDatabase.id))
            .filter_by(assessment_id=assessment_id)
            .scalar()
        )

        # Count tables
        table_count = (
            self.session.query(func.count(GlueTable.id))
            .filter_by(assessment_id=assessment_id)
            .scalar()
        )

        # Count by readiness
        readiness_counts = dict(
            self.session.query(
                GlueTable.migration_readiness, func.count(GlueTable.id)
            )
            .filter_by(assessment_id=assessment_id)
            .group_by(GlueTable.migration_readiness)
            .all()
        )

        # Count by format
        format_counts = dict(
            self.session.query(GlueTable.table_format, func.count(GlueTable.id))
            .filter_by(assessment_id=assessment_id)
            .group_by(GlueTable.table_format)
            .all()
        )

        # Count Iceberg tables
        iceberg_count = (
            self.session.query(func.count(GlueTable.id))
            .filter_by(assessment_id=assessment_id, is_iceberg=True)
            .scalar()
        )

        # Total estimated size
        total_size_gb = (
            self.session.query(func.sum(GlueTable.estimated_size_gb))
            .filter_by(assessment_id=assessment_id)
            .scalar()
            or 0
        )

        return {
            "database_count": db_count,
            "table_count": table_count,
            "iceberg_table_count": iceberg_count,
            "total_estimated_size_gb": float(total_size_gb),
            "readiness_breakdown": readiness_counts,
            "format_breakdown": format_counts,
        }

    def get_migration_summary(self, assessment_id: UUID) -> Dict[str, Any]:
        """Get summary statistics for migration jobs in an assessment.

        Args:
            assessment_id: UUID of assessment

        Returns:
            Dictionary with migration summary statistics
        """
        # Count jobs by status
        status_counts = dict(
            self.session.query(MigrationJob.status, func.count(MigrationJob.id))
            .filter_by(assessment_id=assessment_id)
            .group_by(MigrationJob.status)
            .all()
        )

        # Total bytes copied
        total_bytes = (
            self.session.query(func.sum(MigrationJob.bytes_copied))
            .filter_by(assessment_id=assessment_id)
            .scalar()
            or 0
        )

        # Total rows copied
        total_rows = (
            self.session.query(func.sum(MigrationJob.rows_copied))
            .filter_by(assessment_id=assessment_id)
            .scalar()
            or 0
        )

        # Count validation failures
        failed_validations = (
            self.session.query(func.count(ValidationResult.id))
            .join(MigrationJob)
            .filter(
                MigrationJob.assessment_id == assessment_id,
                ValidationResult.status == "failed",
            )
            .scalar()
        )

        return {
            "status_breakdown": status_counts,
            "total_bytes_copied": total_bytes,
            "total_rows_copied": total_rows,
            "failed_validations": failed_validations,
        }

    # ========================================================================
    # Transformation Result Operations
    # ========================================================================

    def save_transformation_result(
        self, result: TransformationResult
    ) -> TransformationResult:
        """Save a transformation result.

        Args:
            result: TransformationResult instance to save

        Returns:
            Saved result with generated ID
        """
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def get_transformation_results(
        self, assessment_id: UUID, status: Optional[str] = None
    ) -> List[TransformationResult]:
        """Get transformation results for an assessment.

        Args:
            assessment_id: UUID of assessment
            status: Optional status filter

        Returns:
            List of transformation results
        """
        query = self.session.query(TransformationResult).filter_by(
            assessment_id=assessment_id
        )

        if status:
            query = query.filter_by(status=status)

        return query.all()
