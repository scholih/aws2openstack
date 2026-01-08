"""Tests for CLI interface."""

from unittest.mock import patch, MagicMock
from pathlib import Path

from click.testing import CliRunner

from aws2openstack.cli import cli


@patch("aws2openstack.cli.MarkdownReporter")
@patch("aws2openstack.cli.JSONReporter")
@patch("aws2openstack.cli.GlueCatalogAssessor")
def test_cli_assess_glue_catalog_success(mock_assessor_class, mock_json_reporter_class, mock_md_reporter_class, tmp_path):
    """Test CLI assess glue-catalog command."""
    # Mock the assessor
    mock_assessor = MagicMock()
    mock_assessor_class.return_value = mock_assessor

    # Mock the report with proper summary attributes
    mock_report = MagicMock()
    mock_report.summary.total_databases = 2
    mock_report.summary.total_tables = 5
    mock_assessor.run_assessment.return_value = mock_report

    # Mock the reporters
    mock_json_reporter = MagicMock()
    mock_json_reporter_class.return_value = mock_json_reporter
    mock_md_reporter = MagicMock()
    mock_md_reporter_class.return_value = mock_md_reporter

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["assess", "glue-catalog", "--region", "us-east-1", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Assessment complete" in result.output
    mock_assessor_class.assert_called_once_with(region="us-east-1", profile=None)
    mock_assessor.run_assessment.assert_called_once()


@patch("aws2openstack.cli.MarkdownReporter")
@patch("aws2openstack.cli.JSONReporter")
@patch("aws2openstack.cli.GlueCatalogAssessor")
def test_cli_with_profile(mock_assessor_class, mock_json_reporter_class, mock_md_reporter_class, tmp_path):
    """Test CLI with AWS profile."""
    mock_assessor = MagicMock()
    mock_assessor_class.return_value = mock_assessor

    # Mock the report with proper summary attributes
    mock_report = MagicMock()
    mock_report.summary.total_databases = 1
    mock_report.summary.total_tables = 3
    mock_assessor.run_assessment.return_value = mock_report

    # Mock the reporters
    mock_json_reporter = MagicMock()
    mock_json_reporter_class.return_value = mock_json_reporter
    mock_md_reporter = MagicMock()
    mock_md_reporter_class.return_value = mock_md_reporter

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "assess",
            "glue-catalog",
            "--region",
            "eu-west-1",
            "--profile",
            "my-profile",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    mock_assessor_class.assert_called_once_with(region="eu-west-1", profile="my-profile")


def test_cli_missing_required_args():
    """Test CLI fails with missing required arguments."""
    runner = CliRunner()
    result = runner.invoke(cli, ["assess", "glue-catalog"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "Error" in result.output
