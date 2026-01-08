"""JSON report generator."""

import json
from pathlib import Path

from aws2openstack.models.catalog import AssessmentReport


class JSONReporter:
    """Generate JSON reports from assessment data."""

    def generate(self, report: AssessmentReport, output_path: Path) -> None:
        """Generate JSON report file.

        Args:
            report: Assessment report to export
            output_path: Path where JSON file should be written
        """
        # Convert Pydantic model to dict, handling datetime serialization
        data = report.model_dump(mode="json")

        # Write JSON with pretty formatting
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
