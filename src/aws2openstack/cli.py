"""CLI interface for aws2openstack tools."""

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
def assess_glue_catalog(region: str, profile: str | None, output_dir: Path) -> None:
    """Assess AWS Glue Catalog for migration readiness."""
    click.echo(f"Starting Glue Catalog assessment for region: {region}")

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


if __name__ == "__main__":
    cli()
