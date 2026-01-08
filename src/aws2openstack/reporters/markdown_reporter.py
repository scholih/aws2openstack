"""Markdown report generator."""

from pathlib import Path

from tabulate import tabulate  # type: ignore[import-untyped]

from aws2openstack.models.catalog import AssessmentReport, GlueTable


class MarkdownReporter:
    """Generate Markdown reports from assessment data."""

    def generate(self, report: AssessmentReport, output_path: Path) -> None:
        """Generate Markdown report file.

        Args:
            report: Assessment report to export
            output_path: Path where Markdown file should be written
        """
        sections = [
            self._generate_header(report),
            self._generate_executive_summary(report),
            self._generate_readiness_breakdown(report),
            self._generate_database_overview(report),
            self._generate_table_details(report),
            self._generate_recommendations(report),
        ]

        content = "\n\n".join(sections)

        with open(output_path, "w") as f:
            f.write(content)

    def _generate_header(self, report: AssessmentReport) -> str:
        """Generate report header."""
        metadata = report.assessment_metadata
        timestamp_str = metadata.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")

        return f"""# AWS Glue Catalog Assessment

**Generated:** {timestamp_str}
**Region:** {metadata.region}
**AWS Account:** {metadata.aws_account_id}"""

    def _generate_executive_summary(self, report: AssessmentReport) -> str:
        """Generate executive summary section."""
        summary = report.summary
        iceberg_pct = (
            round(summary.iceberg_tables / summary.total_tables * 100, 1)
            if summary.total_tables > 0
            else 0
        )

        return f"""## Executive Summary

- **Total Databases:** {summary.total_databases}
- **Total Tables:** {summary.total_tables}
- **Iceberg Tables:** {summary.iceberg_tables} ({iceberg_pct}%)
- **Migration Ready:** {summary.migration_ready} tables
- **Needs Conversion:** {summary.needs_conversion} tables
- **Total Estimated Storage:** {summary.total_estimated_size_gb:.1f} GB"""

    def _generate_readiness_breakdown(self, report: AssessmentReport) -> str:
        """Generate migration readiness breakdown table."""
        summary = report.summary
        total = summary.total_tables

        if total == 0:
            return "## Migration Readiness Breakdown\n\nNo tables found."

        rows = [
            [
                "READY",
                summary.migration_ready,
                f"{round(summary.migration_ready / total * 100, 1)}%",
            ],
            [
                "NEEDS_CONVERSION",
                summary.needs_conversion,
                f"{round(summary.needs_conversion / total * 100, 1)}%",
            ],
            [
                "UNKNOWN",
                summary.unknown,
                f"{round(summary.unknown / total * 100, 1)}%",
            ],
        ]

        table = tabulate(rows, headers=["Status", "Count", "Percentage"], tablefmt="github")

        return f"## Migration Readiness Breakdown\n\n{table}"

    def _generate_database_overview(self, report: AssessmentReport) -> str:
        """Generate database overview table."""
        if not report.databases:
            return "## Database Overview\n\nNo databases found."

        rows = []
        for db in report.databases:
            # Count Iceberg tables in this database
            iceberg_count = sum(
                1
                for t in report.tables
                if t.database_name == db.database_name and t.is_iceberg
            )

            # Sum storage for this database
            db_storage = sum(
                t.estimated_size_gb or 0
                for t in report.tables
                if t.database_name == db.database_name
            )

            rows.append(
                [
                    db.database_name,
                    db.table_count,
                    iceberg_count,
                    f"{db_storage:.1f}" if db_storage > 0 else "N/A",
                ]
            )

        table = tabulate(
            rows,
            headers=["Database", "Tables", "Iceberg Tables", "Storage (GB)"],
            tablefmt="github",
        )

        return f"## Database Overview\n\n{table}"

    def _generate_table_details(self, report: AssessmentReport) -> str:
        """Generate detailed table inventory."""
        if not report.tables:
            return "## Detailed Table Inventory\n\nNo tables found."

        # Group tables by database
        databases: dict[str, list[GlueTable]] = {}
        for table in report.tables:
            if table.database_name not in databases:
                databases[table.database_name] = []
            databases[table.database_name].append(table)

        sections = ["## Detailed Table Inventory"]

        for db_name, tables in sorted(databases.items()):
            sections.append(f"\n### Database: {db_name}")

            rows = []
            for table in tables:
                size_str = (
                    f"{table.estimated_size_gb:.1f}"
                    if table.estimated_size_gb is not None
                    else "N/A"
                )
                partitions = ", ".join(table.partition_keys) if table.partition_keys else "None"
                notes_str = "; ".join(table.notes) if table.notes else ""

                rows.append(
                    [
                        table.table_name,
                        table.table_format,
                        size_str,
                        partitions,
                        table.migration_readiness,
                        notes_str,
                    ]
                )

            table_md = tabulate(
                rows,
                headers=["Table", "Format", "Size (GB)", "Partitions", "Readiness", "Notes"],
                tablefmt="github",
            )

            sections.append(table_md)

        return "\n".join(sections)

    def _generate_recommendations(self, report: AssessmentReport) -> str:
        """Generate recommendations section."""
        summary = report.summary

        recommendations = ["## Recommendations", "", "### Migration Strategy", ""]

        if summary.migration_ready > 0:
            recommendations.append(
                f"- **{summary.migration_ready} Iceberg tables (READY):** "
                "Can be migrated immediately using bulk copy tools (rclone, s5cmd)"
            )
            recommendations.append("  - No format conversion needed")
            recommendations.append("  - Metadata can be registered directly in Apache Polaris")
            recommendations.append("")

        if summary.needs_conversion > 0:
            recommendations.append(
                f"- **{summary.needs_conversion} Non-Iceberg tables (NEEDS_CONVERSION):** "
                "Require format conversion"
            )
            recommendations.append("  - Recommend in-place conversion to Iceberg on AWS first")
            recommendations.append("  - Then migrate as Iceberg tables")
            recommendations.append(
                "  - Alternatively, use Spark jobs during migration to convert"
            )
            recommendations.append("")

        if summary.unknown > 0:
            recommendations.append(
                f"- **{summary.unknown} tables (UNKNOWN):** Need manual review"
            )
            recommendations.append("")

        recommendations.extend(
            [
                "### Next Steps",
                "",
                "1. Review tables marked as NEEDS_CONVERSION",
                "2. Prioritize tables by business criticality and size",
                "3. Plan conversion strategy for non-Iceberg tables",
                "4. Proceed to ETL job analysis phase",
            ]
        )

        return "\n".join(recommendations)
