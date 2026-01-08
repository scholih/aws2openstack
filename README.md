# aws2openstack

Migration assessment and automation tools for AWS to OpenStack sovereign cloud migrations.

## Overview

This project provides tools to help consultants and engineers assess and migrate AWS Lakehouse infrastructure (S3, Glue, Athena, Spark) to sovereign OpenStack environments using open-source alternatives.

## Features

### Phase 1: Assessment Tooling (Current)

- **Glue Catalog Assessment**: Inventory AWS Glue databases and tables
- **Migration Readiness Analysis**: Classify tables as ready, needs conversion, or unknown
- **Report Generation**: Generate both Markdown (client-facing) and JSON (automation) reports
- **Multiple Format Support**: Detect Iceberg, Parquet, ORC, and other table formats

## Installation

```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Usage

### Assess AWS Glue Catalog

```bash
# Basic usage
aws2openstack assess glue-catalog \
  --region us-east-1 \
  --output-dir ./assessment-results

# With specific AWS profile
aws2openstack assess glue-catalog \
  --region us-east-1 \
  --profile my-aws-profile \
  --output-dir ./assessment-results
```

**Output:**
- `glue-catalog-assessment.json` - Structured data for automation
- `glue-catalog-assessment.md` - Human-readable report for clients

### Authentication

The tool uses the standard AWS credential chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS profile from `--profile` flag or `AWS_PROFILE` env var
3. `~/.aws/credentials` default profile
4. IAM role (if running on EC2/ECS)

### Required AWS Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabases",
        "glue:GetTables",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Development

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aws2openstack --cov-report=term-missing

# Run specific test file
pytest tests/test_glue_catalog.py -v
```

### Type Checking

```bash
mypy src/
```

### Linting

```bash
ruff check src/ tests/
```

## Project Structure

```
aws2openstack/
├── src/aws2openstack/
│   ├── cli.py                    # CLI entry point
│   ├── models/
│   │   └── catalog.py            # Data models
│   ├── assessments/
│   │   └── glue_catalog.py       # Glue assessment logic
│   └── reporters/
│       ├── json_reporter.py      # JSON export
│       └── markdown_reporter.py  # Markdown reports
├── tests/                        # Test suite
├── docs/plans/                   # Design documents
└── pyproject.toml               # Project configuration
```

## Roadmap

- ✅ **Phase 1**: Glue Catalog assessment
- 🔄 **Phase 2**: Glue ETL job analysis
- 📋 **Phase 3**: Athena query pattern analysis
- 📋 **Phase 4**: Migration automation
- 📋 **Phase 5**: Validation framework

## License

TBD

## Contributing

TBD
