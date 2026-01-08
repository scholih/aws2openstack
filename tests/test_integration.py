"""Integration tests for end-to-end workflows."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from aws2openstack.assessments.glue_catalog import GlueCatalogAssessor
from aws2openstack.reporters.json_reporter import JSONReporter
from aws2openstack.reporters.markdown_reporter import MarkdownReporter


@patch("boto3.client")
def test_end_to_end_assessment(mock_boto_client, tmp_path):
    """Test complete assessment workflow."""
    # Mock AWS clients
    mock_glue = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

    # Mock Glue responses
    mock_glue.get_databases.return_value = {
        "DatabaseList": [
            {"Name": "analytics", "Description": "Analytics data"},
            {"Name": "logs"},
        ]
    }

    def get_tables_side_effect(DatabaseName, **kwargs):
        if DatabaseName == "analytics":
            return {
                "TableList": [
                    {
                        "Name": "events",
                        "StorageDescriptor": {
                            "Location": "s3://bucket/events/",
                            "Columns": [{"Name": f"col{i}"} for i in range(10)],
                        },
                        "PartitionKeys": [{"Name": "date", "Type": "date"}],
                        "Parameters": {"table_type": "ICEBERG"},
                        "UpdateTime": datetime(2026, 1, 7, 10, 0, 0, tzinfo=timezone.utc),
                    }
                ]
            }
        elif DatabaseName == "logs":
            return {
                "TableList": [
                    {
                        "Name": "access_logs",
                        "StorageDescriptor": {
                            "Location": "s3://bucket/logs/",
                            "Columns": [{"Name": "timestamp"}, {"Name": "ip"}],
                            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                        },
                        "PartitionKeys": [],
                        "Parameters": {},
                    }
                ]
            }
        return {"TableList": []}

    mock_glue.get_tables.side_effect = get_tables_side_effect

    def client_factory(service, region_name=None):
        if service == "glue":
            return mock_glue
        elif service == "sts":
            return mock_sts
        raise ValueError(f"Unexpected service: {service}")

    mock_boto_client.side_effect = client_factory

    # Run assessment
    assessor = GlueCatalogAssessor(region="us-east-1")
    report = assessor.run_assessment()

    # Verify report contents
    assert report.summary.total_databases == 2
    assert report.summary.total_tables == 2
    assert report.summary.iceberg_tables == 1
    assert report.summary.migration_ready == 1
    assert report.summary.needs_conversion == 1

    # Generate reports
    json_path = tmp_path / "test.json"
    md_path = tmp_path / "test.md"

    json_reporter = JSONReporter()
    json_reporter.generate(report, json_path)

    md_reporter = MarkdownReporter()
    md_reporter.generate(report, md_path)

    # Verify files exist and are valid
    assert json_path.exists()
    assert md_path.exists()

    # Verify JSON is parseable
    with open(json_path) as f:
        data = json.load(f)
    assert data["summary"]["total_tables"] == 2

    # Verify Markdown has expected content
    md_content = md_path.read_text()
    assert "AWS Glue Catalog Assessment" in md_content
    assert "analytics" in md_content
    assert "events" in md_content
    assert "access_logs" in md_content
