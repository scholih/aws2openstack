# PostgreSQL Persistence, MCP Server, and Streamlit Dashboard - Design Document

**Date:** 2026-01-09
**Status:** Proposed
**Scope:** Phase 2 - Persistence Layer, Interactive Exploration, and Monitoring

## Overview

This document describes the design for Phase 2 of the aws2openstack project: adding PostgreSQL persistence for assessment data, an MCP server for interactive Claude-based exploration, and a Streamlit dashboard for visualization and migration monitoring.

## Context

Phase 1 delivered a CLI assessment tool that inventories AWS Glue Catalog and generates JSON/Markdown reports. Phase 2 extends this by:
1. Storing assessment results in PostgreSQL for historical tracking and querying
2. Enabling natural language exploration of assessment data via Claude MCP server
3. Providing real-time monitoring dashboards for assessments and migrations

## User Personas

**Primary Users:**
1. **Migration consultants** - Use Streamlit dashboard to analyze assessments, present to clients
2. **Data engineers** - Query assessment data via Claude MCP for migration planning
3. **Operations teams** - Monitor active migrations via CloudWatch-integrated dashboards

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                     PostgreSQL                          │
│  ┌──────────────┬──────────────┬────────────────┐     │
│  │ assessments  │  databases   │    tables      │     │
│  │              │              │                │     │
│  │ migration_   │  migration_  │   migration_   │     │
│  │ jobs         │  progress    │   metrics      │     │
│  └──────────────┴──────────────┴────────────────┘     │
└─────────────────────────────────────────────────────────┘
         ▲                    ▲                ▲
         │                    │                │
    ┌────┴────┐         ┌─────┴─────┐    ┌────┴────┐
    │   CLI   │         │    MCP    │    │Streamlit│
    │Assessment│        │  Server   │    │Dashboard│
    └─────────┘         └───────────┘    └────┬────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ CloudWatch  │
                                        │ (AWS DMS,   │
                                        │ DataSync,   │
                                        │ Glue Jobs)  │
                                        └─────────────┘
```

### Data Flow

1. **Assessment CLI**: Runs `aws2openstack assess glue-catalog`, writes results to PostgreSQL (+ files)
2. **MCP Server**: Claude queries "Show tables needing conversion" → SQL → results from PostgreSQL
3. **Streamlit Dashboard** (two views):
   - **Assessment View**: Queries PostgreSQL for migration readiness visualization
   - **Migration View**: Fetches CloudWatch metrics (DMS, DataSync, Glue) + PostgreSQL state → live dashboards
4. **Migration orchestration** (future Phase 3): Tracks migration jobs in PostgreSQL, links to CloudWatch

### Technology Stack

**Persistence:**
- PostgreSQL 15+ (for arrays, UUID support)
- SQLAlchemy 2.x (ORM and connection management)
- Alembic (database migrations)

**MCP Server:**
- Model Context Protocol SDK
- Python 3.12+
- SQLAlchemy for queries

**Dashboard:**
- Streamlit (UI framework)
- Plotly (interactive charts)
- boto3 CloudWatch client
- streamlit-autorefresh (live updates)

**CLI Extension:**
- Extend existing aws2openstack CLI
- Optional PostgreSQL persistence (controlled by DATABASE_URL env var)

---

## Component 1: PostgreSQL Schema

### Database Schema

Mirrors Pydantic models from Phase 1 for consistency:

```sql
-- Assessment runs (one per CLI execution)
CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    region VARCHAR(50) NOT NULL,
    aws_account_id VARCHAR(12) NOT NULL,
    tool_version VARCHAR(20) NOT NULL,

    -- Summary statistics (denormalized for fast queries)
    total_databases INTEGER NOT NULL,
    total_tables INTEGER NOT NULL,
    iceberg_tables INTEGER NOT NULL,
    migration_ready INTEGER NOT NULL,
    needs_conversion INTEGER NOT NULL,
    unknown INTEGER NOT NULL,
    total_estimated_size_gb NUMERIC(12,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Databases (many per assessment)
CREATE TABLE databases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    description TEXT,
    location_uri TEXT,
    table_count INTEGER NOT NULL
);

-- Tables (many per database)
CREATE TABLE tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID REFERENCES databases(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE, -- Denormalized for queries
    table_name VARCHAR(255) NOT NULL,
    table_format VARCHAR(50) NOT NULL,
    storage_location TEXT NOT NULL,
    estimated_size_gb NUMERIC(12,2),
    partition_keys TEXT[], -- PostgreSQL array
    column_count INTEGER NOT NULL,
    last_updated TIMESTAMPTZ,
    is_iceberg BOOLEAN NOT NULL,
    migration_readiness VARCHAR(20) NOT NULL, -- READY, NEEDS_CONVERSION, UNKNOWN
    notes TEXT[] -- PostgreSQL array
);

-- Migration jobs (future - for tracking actual migrations)
CREATE TABLE migration_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID REFERENCES tables(id),
    job_type VARCHAR(50) NOT NULL, -- DMS, COPY, GLUE_JOB
    aws_job_id VARCHAR(255), -- DMS task ARN, Glue job run ID, etc.
    status VARCHAR(20) NOT NULL, -- PENDING, RUNNING, COMPLETED, FAILED
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    rows_copied BIGINT,
    bytes_copied BIGINT,
    error_message TEXT
);

-- Indexes for common query patterns
CREATE INDEX idx_assessments_timestamp ON assessments(timestamp DESC);
CREATE INDEX idx_assessments_account_region ON assessments(aws_account_id, region);
CREATE INDEX idx_databases_assessment ON databases(assessment_id);
CREATE INDEX idx_tables_database ON tables(database_id);
CREATE INDEX idx_tables_assessment ON tables(assessment_id);
CREATE INDEX idx_tables_readiness ON tables(migration_readiness);
CREATE INDEX idx_tables_format ON tables(table_format);
CREATE INDEX idx_tables_name ON tables(table_name);
CREATE INDEX idx_migration_jobs_table ON migration_jobs(table_id);
CREATE INDEX idx_migration_jobs_status ON migration_jobs(status);
```

### Key Design Decisions

1. **UUIDs for primary keys**: Better for distributed systems, no collisions
2. **Foreign key constraints with CASCADE**: Clean up old assessments automatically
3. **PostgreSQL arrays**: Native support for `partition_keys` and `notes` (matches Pydantic `list[str]`)
4. **Denormalized fields**: `assessment_id` in tables for direct queries without joins
5. **TIMESTAMPTZ**: Timezone-aware timestamps (store UTC, display in user's timezone)
6. **Indexes**: Optimized for dashboard queries (by readiness, format, timestamp)

### Migration Strategy

Use Alembic for schema versioning:
```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

---

## Component 2: CLI Persistence Integration

### New Module Structure

```
src/aws2openstack/
├── persistence/
│   ├── __init__.py
│   ├── db.py              # Database connection
│   ├── models.py          # SQLAlchemy models
│   └── repository.py      # Data access layer
```

### Implementation

**Database Connection:**

```python
# src/aws2openstack/persistence/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

def get_connection_string() -> str:
    """Get PostgreSQL connection from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/aws2openstack"
    )

def get_engine():
    """Create SQLAlchemy engine."""
    return create_engine(
        get_connection_string(),
        pool_pre_ping=True,  # Verify connections
        echo=False  # Set True for SQL logging
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False)
```

**Repository Pattern:**

```python
# src/aws2openstack/persistence/repository.py
from uuid import UUID
from sqlalchemy.orm import Session
from aws2openstack.models.catalog import AssessmentReport

class AssessmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_assessment(self, report: AssessmentReport) -> UUID:
        """Save complete assessment report to PostgreSQL.

        Args:
            report: Assessment report from Phase 1

        Returns:
            UUID of created assessment record
        """
        # Insert assessment with summary
        assessment = Assessment(
            timestamp=report.assessment_metadata.timestamp,
            region=report.assessment_metadata.region,
            aws_account_id=report.assessment_metadata.aws_account_id,
            tool_version=report.assessment_metadata.tool_version,
            total_databases=report.summary.total_databases,
            total_tables=report.summary.total_tables,
            iceberg_tables=report.summary.iceberg_tables,
            migration_ready=report.summary.migration_ready,
            needs_conversion=report.summary.needs_conversion,
            unknown=report.summary.unknown,
            total_estimated_size_gb=report.summary.total_estimated_size_gb
        )
        self.session.add(assessment)
        self.session.flush()  # Get assessment.id

        # Insert databases and tables
        for db in report.databases:
            database = Database(
                assessment_id=assessment.id,
                database_name=db.database_name,
                description=db.description,
                location_uri=db.location_uri,
                table_count=db.table_count
            )
            self.session.add(database)
            self.session.flush()  # Get database.id

            # Find tables for this database
            db_tables = [t for t in report.tables if t.database_name == db.database_name]
            for table in db_tables:
                table_record = Table(
                    database_id=database.id,
                    assessment_id=assessment.id,  # Denormalized
                    table_name=table.table_name,
                    table_format=table.table_format,
                    storage_location=table.storage_location,
                    estimated_size_gb=table.estimated_size_gb,
                    partition_keys=table.partition_keys,
                    column_count=table.column_count,
                    last_updated=table.last_updated,
                    is_iceberg=table.is_iceberg,
                    migration_readiness=table.migration_readiness,
                    notes=table.notes
                )
                self.session.add(table_record)

        self.session.commit()
        return assessment.id

    def get_latest_assessment(self, region: str, account_id: str) -> Assessment | None:
        """Get most recent assessment for region/account."""
        return self.session.query(Assessment)\
            .filter_by(region=region, aws_account_id=account_id)\
            .order_by(Assessment.timestamp.desc())\
            .first()
```

### CLI Integration

**Modified CLI Command:**

```python
# src/aws2openstack/cli.py
@assess.command("glue-catalog")
@click.option("--region", required=True)
@click.option("--profile", default=None)
@click.option("--output-dir", type=click.Path(path_type=Path), required=True)
@click.option("--save-to-db", is_flag=True, help="Save results to PostgreSQL")
def assess_glue_catalog(region: str, profile: str | None, output_dir: Path, save_to_db: bool):
    """Assess AWS Glue Catalog for migration readiness."""
    click.echo(f"Starting Glue Catalog assessment for region: {region}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run assessment (existing Phase 1 code)
    assessor = GlueCatalogAssessor(region=region, profile=profile)
    click.echo("Collecting databases and tables...")
    report = assessor.run_assessment()

    click.echo(f"Found {report.summary.total_databases} databases "
               f"with {report.summary.total_tables} tables")

    # NEW: Save to PostgreSQL (optional, controlled by flag or DATABASE_URL)
    if save_to_db or os.getenv("DATABASE_URL"):
        try:
            from aws2openstack.persistence.db import get_engine
            from aws2openstack.persistence.repository import AssessmentRepository

            engine = get_engine()
            session = SessionLocal(bind=engine)
            repo = AssessmentRepository(session)

            assessment_id = repo.save_assessment(report)
            click.echo(f"💾 Saved to database: {assessment_id}")
        except Exception as e:
            click.echo(f"⚠️  Failed to save to database: {e}", err=True)

    # EXISTING: Generate file reports
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
```

### Configuration

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:pass@localhost:5432/aws2openstack`)
- If not set, CLI works as before (Phase 1 behavior - files only)
- If set, CLI persists to database + generates files

**Backward Compatibility:**
- Existing CLI commands work without database
- Database persistence is optional enhancement
- No breaking changes to Phase 1 functionality

---

## Component 3: MCP Server for Claude

### Purpose

Enable natural language queries in Claude about assessment data stored in PostgreSQL. Migration consultants can ask questions like:
- "Show me all tables that need conversion in the analytics database"
- "What's the largest Parquet table?"
- "Which databases have the most Iceberg tables?"

### MCP Server Architecture

```
src/aws2openstack/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py          # MCP server implementation
│   ├── tools.py           # Tool definitions for Claude
│   └── queries.py         # SQL query builders
```

### Tool Definitions

The MCP server exposes 6 tools for Claude:

```python
# src/aws2openstack/mcp_server/tools.py
tools = [
    {
        "name": "get_latest_assessment",
        "description": "Get the most recent assessment summary for a region/account",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "AWS region (e.g., us-east-1)"},
                "account_id": {"type": "string", "description": "AWS account ID"}
            },
            "required": ["region", "account_id"]
        }
    },
    {
        "name": "query_tables_by_readiness",
        "description": "Find tables filtered by migration readiness status",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["READY", "NEEDS_CONVERSION", "UNKNOWN"],
                    "description": "Migration readiness status"
                },
                "database": {
                    "type": "string",
                    "description": "Optional: filter by database name"
                },
                "assessment_id": {
                    "type": "string",
                    "description": "Optional: specific assessment UUID (defaults to latest)"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "get_database_summary",
        "description": "Get summary statistics for a specific database",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_name": {"type": "string", "description": "Database name"},
                "assessment_id": {"type": "string", "description": "Optional: assessment UUID"}
            },
            "required": ["database_name"]
        }
    },
    {
        "name": "search_tables",
        "description": "Search tables by name pattern or format",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Table name pattern (SQL LIKE, e.g., 'events%')"
                },
                "format": {
                    "type": "string",
                    "enum": ["ICEBERG", "PARQUET", "ORC", "AVRO", "UNKNOWN"],
                    "description": "Optional: filter by table format"
                },
                "min_size_gb": {
                    "type": "number",
                    "description": "Optional: minimum table size in GB"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "get_tables_by_format",
        "description": "Group tables by format with counts and sizes",
        "input_schema": {
            "type": "object",
            "properties": {
                "assessment_id": {"type": "string", "description": "Optional: assessment UUID"}
            }
        }
    },
    {
        "name": "compare_assessments",
        "description": "Compare two assessments to see what changed",
        "input_schema": {
            "type": "object",
            "properties": {
                "assessment_id_1": {"type": "string", "description": "First assessment UUID"},
                "assessment_id_2": {"type": "string", "description": "Second assessment UUID"}
            },
            "required": ["assessment_id_1", "assessment_id_2"]
        }
    }
]
```

### Example Interaction Flow

**User to Claude:**
> "Show me all Parquet tables larger than 100GB in the analytics database"

**Claude calls MCP tool:**
```json
{
  "tool": "search_tables",
  "arguments": {
    "pattern": "%",
    "format": "PARQUET",
    "min_size_gb": 100
  }
}
```

**MCP Server executes SQL:**
```sql
SELECT t.table_name, t.estimated_size_gb, t.storage_location, t.partition_keys
FROM tables t
JOIN databases d ON t.database_id = d.id
WHERE d.database_name = 'analytics'
  AND t.table_format = 'PARQUET'
  AND t.estimated_size_gb > 100
ORDER BY t.estimated_size_gb DESC;
```

**Returns to Claude:**
```json
[
  {"table_name": "events", "estimated_size_gb": 1250.5, "storage_location": "s3://...", "partition_keys": ["date"]},
  {"table_name": "logs", "estimated_size_gb": 450.2, "storage_location": "s3://...", "partition_keys": []}
]
```

**Claude formats response:**
> "I found 2 Parquet tables over 100GB in the analytics database:
>
> 1. **events** - 1,250.5 GB, partitioned by date
> 2. **logs** - 450.2 GB, not partitioned"

### MCP Server Implementation

**Server Entry Point:**

```python
# src/aws2openstack/mcp_server/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from aws2openstack.persistence.db import get_engine, SessionLocal
from aws2openstack.mcp_server.tools import tools, execute_tool

server = Server("aws2openstack-mcp")

@server.list_tools()
async def list_tools():
    """List available tools for Claude."""
    return tools

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute a tool requested by Claude."""
    session = SessionLocal(bind=get_engine())
    try:
        result = execute_tool(session, name, arguments)
        return result
    finally:
        session.close()

async def main():
    """Run MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Running the MCP Server:**

```bash
# Start MCP server
python -m aws2openstack.mcp_server

# Configure in Claude Desktop config:
{
  "mcpServers": {
    "aws2openstack": {
      "command": "python",
      "args": ["-m", "aws2openstack.mcp_server"],
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/aws2openstack"
      }
    }
  }
}
```

---

## Component 4: Streamlit Dashboard

### Dashboard Structure

Two main views accessible via sidebar navigation:

#### View 1: Assessment Dashboard

**Overview Page:**

```python
import streamlit as st
import plotly.express as px
from aws2openstack.persistence.repository import AssessmentRepository

st.set_page_config(page_title="AWS to OpenStack Migration", layout="wide")

# Sidebar navigation
view = st.sidebar.radio("View", ["Assessment", "Migration"])

if view == "Assessment":
    # Get latest assessment
    repo = AssessmentRepository(session)
    assessment = repo.get_latest_assessment(region, account_id)

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Databases", assessment.total_databases)
    col2.metric("Total Tables", assessment.total_tables)
    col3.metric("Migration Ready", assessment.migration_ready)
    col4.metric("Need Conversion", assessment.needs_conversion)

    # Readiness pie chart
    fig = px.pie(
        values=[assessment.migration_ready, assessment.needs_conversion, assessment.unknown],
        names=["READY", "NEEDS_CONVERSION", "UNKNOWN"],
        title="Migration Readiness",
        color_discrete_map={"READY": "green", "NEEDS_CONVERSION": "yellow", "UNKNOWN": "red"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Format breakdown bar chart
    format_data = repo.get_tables_by_format(assessment.id)
    fig = px.bar(format_data, x="format", y="count", title="Tables by Format")
    st.plotly_chart(fig, use_container_width=True)
```

**Database Explorer Page:**

- Searchable/filterable table of all databases
- Columns: database name, table count, total size, Iceberg %
- Click database → drill down to tables view
- Export filtered results to CSV

**Table Details Page:**

- Sortable/filterable table list with all metadata
- Columns: table name, database, format, size, partitions, readiness, notes
- Color coding: 🟢 READY, 🟡 NEEDS_CONVERSION, 🔴 UNKNOWN
- Multi-select filters: readiness status, format, size range
- Search by table name pattern

#### View 2: Migration Dashboard

**Active Migrations Page:**

```python
import boto3
from streamlit_autorefresh import st_autorefresh

# Auto-refresh every 30 seconds
st_autorefresh(interval=30000, key="migration_refresh")

cloudwatch = boto3.client('cloudwatch')

# AWS DMS Tasks
st.subheader("AWS DMS Replication Tasks")
dms_tasks = get_dms_task_metrics(cloudwatch)
for task in dms_tasks:
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.write(f"**{task['name']}**")
    col2.metric("Progress", f"{task['progress']}%")
    col3.metric("Status", task['status'])
    st.progress(task['progress'] / 100)

# DataSync Tasks
st.subheader("AWS DataSync Tasks")
datasync_tasks = get_datasync_metrics(cloudwatch)
for task in datasync_tasks:
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.write(f"**{task['name']}**")
    col2.metric("Bytes Transferred", format_bytes(task['bytes_transferred']))
    col3.metric("Status", task['status'])

# Glue Jobs
st.subheader("AWS Glue ETL Jobs")
glue_jobs = get_glue_job_metrics(cloudwatch)
for job in glue_jobs:
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.write(f"**{job['name']}**")
    col2.metric("Duration", f"{job['duration_min']} min")
    col3.metric("Status", job['status'])
```

**Migration History Page:**

- Completed migrations from PostgreSQL `migration_jobs` table
- Link back to original assessed tables
- Success rate, average duration, common errors
- Timeline chart showing migrations over time

### Technology Stack

**Dashboard Components:**
- **Streamlit**: Core UI framework
- **Plotly**: Interactive charts (pie, bar, timeline)
- **boto3**: CloudWatch metrics API
- **SQLAlchemy**: PostgreSQL queries
- **streamlit-autorefresh**: Auto-refresh for live data
- **pandas**: Data manipulation for tables

**Running the Dashboard:**

```bash
# Install dependencies
pip install streamlit plotly streamlit-autorefresh

# Run dashboard
streamlit run src/aws2openstack/dashboard/app.py

# Opens browser at http://localhost:8501
```

### Dashboard Features

**Assessment View:**
- 📊 Interactive charts (drill-down on pie slices)
- 🔍 Full-text search across tables
- 📁 Export filtered data to CSV
- 📅 Historical trend analysis (compare assessments over time)
- 🎨 Color-coded readiness indicators

**Migration View:**
- 🔄 Auto-refresh every 30 seconds
- ⚡ Real-time CloudWatch metrics
- 📈 Progress bars for active migrations
- 🚨 Alert indicators for failed tasks
- 📊 Historical success rate charts

---

## Implementation Phases

### Phase 2.1: PostgreSQL Foundation (Week 1-2)
- Set up PostgreSQL schema and Alembic migrations
- Create SQLAlchemy models
- Implement repository layer
- Extend CLI with `--save-to-db` flag
- Test with Phase 1 assessment data

### Phase 2.2: MCP Server (Week 3)
- Implement MCP server with 6 query tools
- Test tools in Claude Desktop
- Document tool usage for consultants
- Create example queries documentation

### Phase 2.3: Streamlit Assessment View (Week 4)
- Build overview page with charts
- Implement database explorer
- Create table details view with filters
- Add CSV export functionality

### Phase 2.4: Streamlit Migration View (Week 5)
- Integrate CloudWatch API for DMS/DataSync/Glue
- Build active migrations dashboard
- Add auto-refresh for live updates
- Implement migration history page

### Phase 2.5: Integration & Polish (Week 6)
- End-to-end testing of all components
- Performance optimization (query tuning, caching)
- Documentation (setup guide, user guide)
- Deployment guide (Docker Compose for PostgreSQL + Streamlit)

---

## Deployment Architecture

### Development Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: aws2openstack
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/aws2openstack
    depends_on:
      - postgres

volumes:
  postgres_data:
```

**Run with Docker Compose:**
```bash
docker-compose up -d
```

### Production Considerations

**PostgreSQL:**
- Use managed service (AWS RDS, CloudSQL, Azure Database)
- Enable SSL connections
- Regular backups via automated snapshots
- Connection pooling (PgBouncer)

**Streamlit:**
- Deploy on cloud VM or container service
- Use reverse proxy (nginx) with SSL
- Authentication via Streamlit Cloud or custom OAuth
- Restrict access to VPN or IP whitelist

**MCP Server:**
- Runs locally on consultant machines (Claude Desktop)
- Connects to PostgreSQL via SSL
- Read-only database user for security

---

## Security Considerations

### Database Access

1. **Least Privilege**:
   - CLI: Read-write access to `assessments`, `databases`, `tables`
   - MCP Server: Read-only access (SELECT only)
   - Streamlit: Read-only for assessment view, read-write for migration jobs

2. **Connection Security**:
   - SSL/TLS required for all connections
   - No plaintext passwords in code
   - Use environment variables or secrets management

3. **Data Protection**:
   - No sensitive AWS credentials stored in database
   - AWS account IDs and regions are metadata (non-sensitive)
   - Table metadata may contain location info (S3 paths)

### Authentication

**MCP Server:**
- Uses local Claude Desktop installation
- No exposed network port
- Database credentials from environment

**Streamlit:**
- Add Streamlit authentication or OAuth
- Restrict to VPN/internal network
- Read-only views for non-admin users

---

## Testing Strategy

### Unit Tests
- Repository layer: Mock SQLAlchemy sessions
- MCP tools: Mock database queries
- Streamlit components: Test chart generation logic

### Integration Tests
- CLI → PostgreSQL: Verify assessment persistence
- MCP Server: Test tool execution with real database
- Streamlit → PostgreSQL: Query correctness

### End-to-End Tests
1. Run CLI assessment → verify database records
2. Query via MCP → verify results match database
3. View in Streamlit → verify charts/tables display correctly

---

## Success Criteria

Phase 2 is complete when:

- ✅ CLI can persist assessments to PostgreSQL
- ✅ MCP server enables Claude queries on assessment data
- ✅ Streamlit dashboard visualizes assessments
- ✅ CloudWatch integration shows live migration metrics
- ✅ All components documented and tested
- ✅ Docker Compose setup for local development
- ✅ Deployment guide for production

---

## Future Enhancements (Phase 3+)

**Phase 3: Migration Orchestration**
- CLI commands to trigger migrations
- Track migration jobs in PostgreSQL
- Link CloudWatch metrics to job records

**Phase 4: Migration Automation**
- Automated DMS task creation from assessments
- Batch migration scheduling
- Validation and rollback procedures

**Phase 5: Multi-Cloud Support**
- Support for Azure, GCP migrations
- Generic cloud → cloud framework
- Extensible architecture for new sources/targets

---

## Open Questions

None - design is approved and ready for implementation planning.
