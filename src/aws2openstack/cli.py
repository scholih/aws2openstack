"""CLI interface for aws2openstack tools."""

import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import click

from aws2openstack.assessments.glue_catalog import GlueCatalogAssessor
from aws2openstack.reporters.json_reporter import JSONReporter
from aws2openstack.reporters.markdown_reporter import MarkdownReporter


@click.group()
@click.version_option()
def cli() -> None:
    """AWS to OpenStack migration tools."""
    pass


@cli.group()
def assess() -> None:
    """Run migration assessments."""
    pass


@assess.command("glue-catalog")
@click.option(
    "--region",
    required=True,
    help="AWS region to assess",
)
@click.option(
    "--profile",
    default=None,
    help="AWS profile name (uses default credential chain if not specified)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory to write report files",
)
@click.option(
    "--save-to-db",
    is_flag=True,
    help="Save assessment results to PostgreSQL (requires DATABASE_URL env var)",
)
def assess_glue_catalog(
    region: str, profile: str | None, output_dir: Path, save_to_db: bool
) -> None:
    """Assess AWS Glue Catalog for migration readiness."""
    click.echo(f"Starting Glue Catalog assessment for region: {region}")

    # Check DATABASE_URL if persistence requested
    if save_to_db and not os.getenv("DATABASE_URL"):
        click.echo(
            "❌ Error: DATABASE_URL environment variable not set. "
            "Required when using --save-to-db flag.",
            err=True,
        )
        raise click.Abort()

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run assessment
    assessor = GlueCatalogAssessor(region=region, profile=profile)

    click.echo("Collecting databases and tables...")
    report = assessor.run_assessment()

    click.echo(
        f"Found {report.summary.total_databases} databases "
        f"with {report.summary.total_tables} tables"
    )

    # Save to database if requested
    assessment_id = None
    if save_to_db:
        click.echo("Saving assessment to database...")
        assessment_id = _save_assessment_to_db(report, region, profile)
        click.echo(f"✅ Saved to database (ID: {assessment_id})")

    # Generate reports
    json_path = output_dir / "glue-catalog-assessment.json"
    md_path = output_dir / "glue-catalog-assessment.md"

    click.echo("Generating JSON report...")
    json_reporter = JSONReporter()
    json_reporter.generate(report, json_path)

    click.echo("Generating Markdown report...")
    md_reporter = MarkdownReporter()
    md_reporter.generate(report, md_path)

    click.echo("\n✅ Assessment complete!")
    click.echo(f"  - JSON report: {json_path}")
    click.echo(f"  - Markdown report: {md_path}")
    if assessment_id:
        click.echo(f"  - Database ID: {assessment_id}")


def _save_assessment_to_db(report, region: str, profile: str | None):
    """Save assessment report to PostgreSQL database.

    Args:
        report: AssessmentReport instance
        region: AWS region
        profile: AWS profile name (optional)

    Returns:
        UUID of saved assessment
    """
    from aws2openstack.persistence import get_engine, AssessmentRepository
    from aws2openstack.persistence.models import (
        Assessment,
        GlueDatabase,
        GlueTable,
    )
    from sqlalchemy.orm import sessionmaker

    # Create session
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    repository = AssessmentRepository(session)

    try:
        # Create assessment record
        assessment = Assessment(
            timestamp=report.timestamp,
            region=region,
            aws_account_id=report.account_id,
            tool_version="0.1.0",  # TODO: Get from package metadata
            services=["glue"],
            status="completed",
        )
        assessment = repository.save_assessment(assessment)

        # Save databases and tables
        for db_model in report.databases:
            # Create database record
            glue_db = GlueDatabase(
                assessment=assessment,
                database_name=db_model.name,
                description=db_model.description,
                location_uri=db_model.location_uri,
                table_count=len(db_model.tables),
            )
            glue_db = repository.save_glue_database(glue_db)

            # Save tables
            for table_model in db_model.tables:
                glue_table = GlueTable(
                    database=glue_db,
                    assessment=assessment,
                    table_name=table_model.name,
                    table_format=table_model.format,
                    storage_location=table_model.location,
                    estimated_size_gb=(
                        Decimal(str(table_model.estimated_size_gb))
                        if table_model.estimated_size_gb
                        else None
                    ),
                    partition_keys=table_model.partition_keys or [],
                    column_count=table_model.column_count,
                    last_updated=(
                        table_model.last_updated.replace(tzinfo=timezone.utc)
                        if table_model.last_updated
                        else None
                    ),
                    is_iceberg=table_model.is_iceberg,
                    migration_readiness=table_model.readiness,
                    notes=table_model.notes or [],
                )
                repository.save_glue_table(glue_table)

        session.commit()
        return assessment.id

    except Exception as e:
        session.rollback()
        raise click.ClickException(f"Failed to save to database: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    cli()
