# AWS Glue Catalog Assessment Tool - Design Document

**Date:** 2026-01-08
**Status:** Approved
**Scope:** Phase 1 - Assessment Tooling

## Overview

This document describes the design for the first deliverable of the aws2openstack project: an assessment tool that inventories AWS Glue Catalog resources to help migration consultants understand what needs to be migrated from AWS to sovereign OpenStack infrastructure.

## Context

Based on the technical assessment document, migrating from AWS Lakehouse to OpenStack requires understanding the current state before migration. The Glue Catalog is the foundation - it contains all table definitions, schemas, and metadata that define the data architecture.

## User Persona

**Primary User:** Migration consultants/specialists
- Run assessments for multiple clients
- Need detailed, client-facing reports
- Require both human-readable and machine-readable outputs
- Export data for further analysis and planning

## Scope

### In Scope - Phase 1
- Inventory AWS Glue Catalog (databases and tables)
- Analyze migration readiness based on table format
- Generate markdown reports for clients
- Export structured JSON data for automation
- Support standard AWS authentication methods

### Out of Scope - Future Phases
- Glue ETL job analysis
- Athena query pattern analysis
- Actual data migration
- Cost estimation
- Performance benchmarking

## Architecture

### Project Structure

```
aws2openstack/
├── src/
│   └── aws2openstack/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── assessments/
│       │   ├── __init__.py
│       │   ├── glue_catalog.py # Glue assessment logic
│       │   └── base.py         # Base assessment class
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── markdown.py     # Markdown report generator
│       │   └── json.py         # JSON data exporter
│       └── models/
│           ├── __init__.py
│           └── catalog.py      # Data models
├── docs/
│   └── plans/
├── tests/
│   └── test_glue_catalog.py
└── pyproject.toml
```

### Technology Stack

- **Python 3.12+** - Modern Python with type hints
- **boto3** - AWS SDK for Python (Glue API access)
- **click** - CLI framework
- **pydantic** - Data validation and modeling
- **tabulate** - Generate markdown tables
- Standard library for JSON serialization

### CLI Interface

```bash
# Basic usage
aws2openstack assess glue-catalog --region us-east-1 --output-dir ./results

# With specific AWS profile
aws2openstack assess glue-catalog --region us-east-1 --profile my-profile --output-dir ./results

# Multiple regions
aws2openstack assess glue-catalog --region us-east-1,eu-west-1 --output-dir ./results
```

**Arguments:**
- `--region` (required): AWS region(s) to assess (comma-separated for multiple)
- `--output-dir` (required): Directory to write report files
- `--profile` (optional): AWS profile name (uses default credential chain if not specified)

## Data Model

### GlueTable Model

```python
class GlueTable(BaseModel):
    database_name: str
    table_name: str
    table_format: str           # "ICEBERG", "PARQUET", "ORC", "AVRO", "CSV", etc.
    storage_location: str       # S3 URI (e.g., s3://bucket/path/)
    estimated_size_gb: float | None
    partition_keys: list[str]
    column_count: int
    last_updated: datetime | None
    is_iceberg: bool
    migration_readiness: str    # "READY", "NEEDS_CONVERSION", "UNKNOWN"
    notes: list[str]            # Any warnings or additional info
```

### GlueDatabase Model

```python
class GlueDatabase(BaseModel):
    database_name: str
    description: str | None
    location_uri: str | None
    table_count: int
```

### AssessmentReport Model

```python
class AssessmentReport(BaseModel):
    assessment_metadata: AssessmentMetadata
    summary: AssessmentSummary
    databases: list[GlueDatabase]
    tables: list[GlueTable]
```

## Data Collection Logic

### Discovery Flow

1. **Initialize AWS Client**
   - Use boto3 with standard credential chain (env vars, ~/.aws/credentials, IAM roles)
   - Support AWS_PROFILE environment variable or --profile flag
   - Validate credentials and region before starting

2. **List Databases**
   - Call `glue.get_databases()` paginated API
   - Extract database names and metadata
   - Handle pagination for large catalogs

3. **List Tables Per Database**
   - For each database, call `glue.get_tables(DatabaseName=db)`
   - Handle pagination
   - Collect full table metadata

4. **Analyze Each Table**
   - Parse table format from StorageDescriptor
   - Identify Iceberg tables (check Parameters for 'table_type' = 'ICEBERG')
   - Extract partition keys
   - Count columns
   - Parse storage location
   - Extract size estimates from table statistics if available
   - Determine migration readiness

### Migration Readiness Classification

**READY:**
- Table format is Iceberg
- Valid S3 storage location
- No obvious blockers

**NEEDS_CONVERSION:**
- Table format is Parquet, ORC, Avro, CSV, or other non-Iceberg format
- Would require conversion to Iceberg before migration

**UNKNOWN:**
- Missing critical metadata
- Unsupported or unrecognized format
- Permission errors reading table details

### Error Handling

- **Insufficient Permissions:** Log warning, skip resource, continue
- **Throttling:** Implement exponential backoff
- **Invalid Metadata:** Mark table as UNKNOWN, include in report with notes
- **Network Errors:** Retry with backoff, fail gracefully if persistent
- Generate error summary section in report

## Report Generation

### Markdown Report Structure

```markdown
# AWS Glue Catalog Assessment

**Generated:** 2026-01-08 14:30:00 CET
**Region:** us-east-1
**AWS Account:** 123456789012

## Executive Summary

- **Total Databases:** 12
- **Total Tables:** 847
- **Iceberg Tables:** 623 (73%)
- **Migration Ready:** 623 tables
- **Needs Conversion:** 224 tables
- **Total Estimated Storage:** 15.2 TB

## Migration Readiness Breakdown

| Status | Count | Percentage |
|--------|-------|------------|
| READY | 623 | 73% |
| NEEDS_CONVERSION | 224 | 26% |
| UNKNOWN | 0 | 1% |

## Database Overview

| Database | Tables | Iceberg Tables | Storage (TB) |
|----------|--------|----------------|--------------|
| analytics_prod | 245 | 245 | 8.3 |
| logs | 412 | 378 | 4.2 |
| ... | ... | ... | ... |

## Detailed Table Inventory

### Database: analytics_prod

| Table | Format | Size (GB) | Partitions | Readiness | Notes |
|-------|--------|-----------|------------|-----------|-------|
| events | ICEBERG | 1234.5 | date, region | READY | |
| ... | ... | ... | ... | ... | ... |

## Recommendations

### Migration Strategy

- **623 Iceberg tables (READY):** Can be migrated immediately using bulk copy tools (rclone, s5cmd)
  - No format conversion needed
  - Metadata can be registered directly in Apache Polaris
  - Estimated copy time: X hours at Y GB/s

- **224 Non-Iceberg tables (NEEDS_CONVERSION):** Require format conversion
  - Recommend in-place conversion to Iceberg on AWS first
  - Then migrate as Iceberg tables
  - Alternatively, use Spark jobs during migration to convert

### Next Steps

1. Review tables marked as NEEDS_CONVERSION
2. Prioritize tables by business criticality and size
3. Plan conversion strategy for non-Iceberg tables
4. Proceed to ETL job analysis phase
```

### JSON Output Structure

```json
{
  "assessment_metadata": {
    "timestamp": "2026-01-08T14:30:00Z",
    "region": "us-east-1",
    "aws_account_id": "123456789012",
    "tool_version": "0.1.0"
  },
  "summary": {
    "total_databases": 12,
    "total_tables": 847,
    "iceberg_tables": 623,
    "migration_ready": 623,
    "needs_conversion": 224,
    "unknown": 0,
    "total_estimated_size_gb": 15200.0
  },
  "databases": [
    {
      "database_name": "analytics_prod",
      "description": "Production analytics tables",
      "location_uri": "s3://my-bucket/analytics/",
      "table_count": 245
    }
  ],
  "tables": [
    {
      "database_name": "analytics_prod",
      "table_name": "events",
      "table_format": "ICEBERG",
      "storage_location": "s3://my-bucket/analytics/events/",
      "estimated_size_gb": 1234.5,
      "partition_keys": ["date", "region"],
      "column_count": 42,
      "last_updated": "2026-01-07T10:30:00Z",
      "is_iceberg": true,
      "migration_readiness": "READY",
      "notes": []
    }
  ]
}
```

### Output Files

Both files written to `--output-dir`:
- `glue-catalog-assessment.md` - Human-readable report
- `glue-catalog-assessment.json` - Complete structured data

## Authentication

Use standard AWS credential chain in this order:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS profile from `--profile` flag or `AWS_PROFILE` env var
3. `~/.aws/credentials` default profile
4. IAM role (if running on EC2/ECS/Lambda)

No credentials stored or handled by the tool directly - all managed by boto3.

## Testing Strategy

### Unit Tests
- Mock boto3 responses for Glue API calls
- Test migration readiness classification logic
- Test report generation with sample data
- Test error handling for various failure scenarios

### Integration Tests
- Require AWS credentials (skip if not available)
- Test against real Glue Catalog in test account
- Validate report output format
- Test with various table formats

### Test Data
- Create fixtures with representative Glue metadata
- Cover edge cases: missing fields, unknown formats, large catalogs

## Future Enhancements (Out of Scope)

- **Phase 2:** Glue ETL job analysis
- **Phase 3:** Athena query pattern analysis
- **Phase 4:** Cost estimation
- **Phase 5:** Automated migration execution

## Dependencies

```toml
[project]
dependencies = [
    "boto3>=1.34.0",
    "click>=8.1.0",
    "pydantic>=2.5.0",
    "tabulate>=0.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.7.0",
    "ruff>=0.1.0",
    "boto3-stubs[glue]>=1.34.0",
]
```

## Success Criteria

- ✅ Tool successfully inventories all Glue databases and tables
- ✅ Accurately identifies Iceberg vs non-Iceberg tables
- ✅ Generates clear, actionable markdown reports
- ✅ Exports complete JSON data for automation
- ✅ Handles errors gracefully without crashing
- ✅ Works with standard AWS authentication
- ✅ Runs in under 5 minutes for catalogs with <1000 tables
- ✅ Type-safe with full type hints
- ✅ Test coverage >80%

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Glue API throttling on large catalogs | High | Implement exponential backoff, pagination |
| Missing size statistics | Medium | Clearly mark as "unknown", don't block assessment |
| Permission errors | Medium | Graceful degradation, partial results still useful |
| Complex table formats not recognized | Low | Mark as UNKNOWN with notes for manual review |

## Open Questions

None - design approved and ready for implementation.
