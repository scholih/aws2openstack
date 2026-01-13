# AWS to OpenStack Migration Dashboard

Interactive Streamlit dashboard for visualizing AWS Glue Catalog migration assessments.

## Features

- **Summary Metrics**: Database count, table count, total size, Iceberg tables
- **Migration Readiness Chart**: Pie chart showing ready/needs_conversion/blocked status
- **Format Distribution**: Bar chart of table formats (Parquet, Iceberg, ORC, etc.)
- **Assessment Selector**: Choose from historical assessments
- **Auto-refresh**: Cached data with manual refresh option

## Prerequisites

1. PostgreSQL database with assessment data
2. `DATABASE_URL` environment variable set

## Installation

The dashboard dependencies are included in the main package:

```bash
pip install -e .
```

This installs:
- `streamlit>=1.28.0`
- `plotly>=5.17.0`
- `pandas>=2.1.0`

## Running the Dashboard

### Option 1: Using streamlit directly

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/aws2openstack"
streamlit run src/aws2openstack/dashboard/app.py
```

### Option 2: With environment file

Create `.env` file:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/aws2openstack
```

Then run:
```bash
source .env
streamlit run src/aws2openstack/dashboard/app.py
```

## Usage

1. **Select Assessment**: Use sidebar dropdown to choose an assessment
2. **View Metrics**: Summary cards show key statistics
3. **Analyze Readiness**: Pie chart shows migration readiness breakdown
4. **Check Formats**: Bar chart displays table format distribution
5. **Refresh**: Click refresh button in sidebar to reload data

## Data Requirements

The dashboard requires at least one assessment in the database. To create an assessment:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/aws2openstack"
aws2openstack assess glue-catalog \
  --region us-east-1 \
  --output-dir ./output \
  --save-to-db
```

## Configuration

- **Cache TTL**: Data cached for 5 minutes (300 seconds)
- **Layout**: Wide mode for better chart visibility
- **Colors**:
  - Ready: Green (#10b981)
  - Needs Conversion: Amber (#f59e0b)
  - Blocked: Red (#ef4444)

## Troubleshooting

### "DATABASE_URL not set" error

Make sure the environment variable is exported:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/aws2openstack"
```

### "No assessments found" warning

Run an assessment with `--save-to-db` flag first:
```bash
aws2openstack assess glue-catalog --region us-east-1 --output-dir ./output --save-to-db
```

### Connection errors

Check PostgreSQL is running and credentials are correct:
```bash
psql $DATABASE_URL -c "SELECT 1"
```
