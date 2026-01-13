# AWS to OpenStack Migration Toolkit

Migration assessment and automation tools for AWS lakehouse infrastructure to OpenStack environments.

## Overview

This toolkit provides end-to-end migration capabilities for AWS data lakehouse infrastructure (Glue Catalog, Athena, S3, Spark) to OpenStack-based environments using open-source alternatives (Trino, Iceberg, Hive).

**Key Capabilities:**
- Assess AWS Glue Catalog and classify migration readiness
- Transform AWS services to OpenStack equivalents via mapping rules
- Generate Terraform infrastructure-as-code for target environment
- Orchestrate data migration with progress tracking
- Monitor migrations via PostgreSQL-backed state and Streamlit dashboard

---

## Architecture

### Migration Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    1. ASSESS                                 │
│  Inventory AWS infrastructure (Glue, Athena, S3, IAM, VPC)  │
│  • Detect table formats (Iceberg, Parquet, ORC)            │
│  • Classify migration readiness                             │
│  • Generate detailed reports (JSON + Markdown)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 2. TRANSFORM                                 │
│  Apply mapping rules: AWS → OpenStack                       │
│  • Glue Catalog → Iceberg REST Catalog (for Iceberg)       │
│  • Glue Catalog → Hive Metastore (for Parquet/ORC)        │
│  • Athena → Trino                                           │
│  • S3 → Swift/Ceph                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 3. GENERATE                                  │
│  Create Terraform infrastructure-as-code                     │
│  • Catalog infrastructure (Iceberg REST / Hive Metastore)   │
│  • Trino query engine configuration                         │
│  • Database schemas and table definitions                   │
│  • Networking and access control                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 4. MIGRATE                                   │
│  Orchestrate data copy with progress tracking               │
│  • Hybrid approach: AWS DataSync + rclone                   │
│  • Parallel table migrations                                │
│  • Resume on failure, progress monitoring                   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 5. MONITOR                                   │
│  PostgreSQL-backed tracking + Streamlit dashboard           │
│  • Assessment history and comparisons                       │
│  • Transformation results preview                           │
│  • Real-time migration progress                             │
│  • CloudWatch integration for AWS services                  │
└─────────────────────────────────────────────────────────────┘
```

### Central PostgreSQL Database

All project state stored in PostgreSQL:

- **Assessments** - Historical inventory of AWS infrastructure
- **Mapping Templates** - Rule-based transformation logic (customizable per customer)
- **Transformation Results** - Generated Terraform outputs  
- **Migration Jobs** - Data copy progress, status, errors

Benefits:
- Cross-session persistence
- MCP server integration (Claude can query assessment data interactively)
- Team collaboration
- Historical analysis

---


## Migration Strategies

The toolkit supports two deployment approaches to meet different business requirements:

### 1. Big Bang Migration

**One-time cutover with coordinated switchover:**

```
Day 1: Assess → Transform → Generate Terraform
Day 2: Apply infrastructure in OpenStack
Day 3: Full data copy (all tables in parallel)
Day 4: Validate data integrity
Day 5: DNS/endpoint cutover → Go live
```

**Characteristics:**
- Single synchronized cutover event
- Shorter total timeline (days to weeks)
- Higher risk - requires extensive pre-migration validation
- Suitable for: Dev/test environments, smaller datasets, maintenance window-tolerant workloads

**Data Copy:**
- Full table copy using AWS DataSync or rclone
- Parallel migration of independent tables
- Checkpoint/resume capability for large tables

### 2. Shadow Running (Full + Incremental Sync)

**Production-grade migration with parallel validation:**

```
Week 1: Assess → Transform → Generate → Deploy target infrastructure
Week 2: Initial full data copy (baseline sync)
Week 3-N: Incremental sync running continuously (CDC)
        → Both systems active (shadow mode)
        → Data validation and reconciliation
        → Gradual query migration to new system
Week N+1: Final cutover when validated
```

**Characteristics:**
- Initial full copy + continuous incremental synchronization
- Both AWS and OpenStack environments run in parallel
- Zero-downtime cutover (gradual DNS/traffic shift)
- Lower risk - can validate and roll back
- Suitable for: Production lakehouses, critical workloads, large datasets

**Data Synchronization:**
- **Full sync:** Initial baseline copy of all tables
- **Incremental sync:** Change Data Capture (CDC) mechanisms:
  - S3 event notifications → trigger incremental copies
  - Periodic diff detection for Glue Catalog changes
  - Timestamp-based incremental table updates
- **Validation:** Continuous data reconciliation during shadow period
- **Cutover:** Gradual traffic shift (read queries first, then writes)

### Architectural Support

Both strategies share the same core pipeline (assess → transform → generate) but differ in orchestration:

**PostgreSQL Tracking:**
- `migration_jobs` table tracks both full and incremental copies
- `last_sync_timestamp` per table for incremental updates
- `sync_mode` field: `full`, `incremental`, `completed`

**Data Orchestration (Phase 3):**
- Big Bang: Parallel full table copies, progress tracking
- Shadow Running: Initial full copy + continuous incremental jobs
- CDC integration: S3 events, Glue Catalog change streams
- Reconciliation: Row counts, checksums, sample data validation

### Business Value

**Why Both Matter:**
- **Dev/Test migrations:** Big bang is faster and simpler
- **Production migrations:** Shadow running is enterprise requirement
- **Customer choice:** Different risk tolerances and downtime windows
- **Competitive advantage:** Most tools only support big bang

**Implementation Priority:**
- Phase 2: Data orchestration tracking (schema supports both modes)
- Phase 3: Big bang implementation (simpler, validates architecture)
- Phase 4: Incremental sync + CDC (production-grade capability)

---

## Data Quality & Validation

Data quality validation is **core infrastructure**, not optional. Every migration includes automated validation at multiple stages with comprehensive reporting.

### Validation Stages

**1. Pre-Migration Assessment**
```
Schema validation:     ✓ Column types compatible
                       ✓ Partition schemes supported
                       ✓ Nested types handled
Size estimation:       ✓ Storage requirements calculated
                       ✓ Network bandwidth planned
Format compatibility:  ✓ Iceberg/Parquet/ORC versions supported
```

**2. During Migration (Real-time)**
```
Transfer validation:   ✓ Bytes copied vs expected
                       ✓ Files transferred vs catalog count
                       ✓ Error rate monitoring
Progress tracking:     ✓ Per-table completion %
                       ✓ ETA calculations
                       ✓ Bottleneck detection
```

**3. Post-Migration (Certification)**
```
Completeness:          ✓ Row count reconciliation
                       ✓ Partition coverage verification
                       ✓ All tables migrated check
Data integrity:        ✓ Checksum validation (sample-based)
                       ✓ Schema round-trip verification
                       ✓ NULL value distribution match
Query validation:      ✓ Test queries produce identical results
                       ✓ Aggregation accuracy
                       ✓ Join correctness
```

### Quality Checks Implemented

**Table-Level Validation:**
```sql
-- Example: Completeness check stored in PostgreSQL
CREATE TABLE validation_results (
    id UUID PRIMARY KEY,
    migration_job_id UUID REFERENCES migration_jobs(id),
    validation_type VARCHAR(50),  -- 'row_count', 'checksum', 'schema', 'sample'
    status VARCHAR(20),            -- 'passed', 'failed', 'warning'
    source_value TEXT,
    target_value TEXT,
    difference TEXT,
    validated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Validation Types:**

1. **Row Count Reconciliation**
   - Source: `SELECT COUNT(*) FROM glue_catalog.table`
   - Target: `SELECT COUNT(*) FROM trino.schema.table`
   - Tolerance: Configurable threshold (e.g., 0.01% for shadow running)

2. **Checksum Validation**
   - Deterministic hash of sample rows (e.g., 10,000 random rows)
   - Includes all columns to detect silent data corruption
   - Partition-aware sampling for large tables

3. **Schema Validation**
   - Column names match (case-insensitive option)
   - Data types compatible (e.g., AWS BIGINT → Trino BIGINT)
   - Partition columns preserved
   - NOT NULL constraints maintained

4. **Statistical Validation**
   - Min/max values per numeric column
   - Distinct value counts for low-cardinality columns
   - NULL percentage per column
   - String length distributions

5. **Sample Data Comparison**
   - Export 1000 rows from source and target
   - Side-by-side comparison in validation report
   - Human-reviewable for sensitive data migrations

### Validation Workflows

**Big Bang Migration:**
```
1. Pre-migration:  Full schema validation
2. Post-copy:      Immediate row count + checksum validation
3. Before cutover: Complete validation suite (all checks)
4. Sign-off:       Generate certification report
```

**Shadow Running:**
```
1. Initial sync:   Full validation after baseline copy
2. Incremental:    Validate each sync batch
3. Continuous:     Scheduled reconciliation (hourly/daily)
4. Dashboard:      Real-time drift detection
5. Cutover:        Final validation + certification
```

### Monitoring & Dashboards

**Streamlit Validation Dashboard:**

```python
# Real-time validation metrics
┌─────────────────────────────────────────────────────────────┐
│ Validation Status: 145/150 tables validated ✓               │
│                    5 tables pending validation               │
│                    0 validation failures                     │
└─────────────────────────────────────────────────────────────┘

Tables by Validation Status:
  ✓ Passed:  145 (96.7%)
  ⚠ Warning:   5 (3.3%)  - Row count drift < 0.01%
  ✗ Failed:    0 (0%)

Recent Validations:
  analytics.events_table     ✓ Passed (1.2M rows matched)
  logs.access_logs          ⚠ Warning (source +10 rows - incremental sync lag)
  warehouse.orders          ✓ Passed (checksum matched)
```

**Validation Metrics:**
- Overall completeness percentage
- Tables pending validation
- Failed validations requiring attention
- Data drift detection (for shadow running)
- Historical validation trends

### Automated Reconciliation

**Continuous Reconciliation Loop (Shadow Running):**

```python
# Runs every hour during shadow period
1. Query source table row count
2. Query target table row count
3. If drift > threshold:
   → Trigger incremental sync
   → Alert monitoring
   → Log to validation_results
4. Sample-based checksum every 6 hours
5. Full validation once per day
```

**Reconciliation Actions:**
- **Acceptable drift:** Log and continue (e.g., < 0.01% for incremental lag)
- **Drift exceeded:** Auto-trigger incremental sync
- **Validation failure:** Alert consultant, block cutover
- **Schema mismatch:** Critical alert, manual intervention required

### Certification Reports

**Migration Certification Document (Auto-Generated):**

```markdown
# Migration Certification Report
Assessment ID: assessment-a3f2dd
Migration Period: 2026-01-10 to 2026-01-24
Validated: 2026-01-24 15:30 CET

## Summary
✓ 150/150 tables migrated successfully
✓ 100% row count validation passed
✓ 100% schema validation passed
✓ 99.8% checksum validation passed (3 tables under threshold)

## Detailed Results
Database: analytics (45 tables)
  All tables validated ✓
  Total rows: 1,245,332,891 (source) → 1,245,332,891 (target)
  Checksum match: 100%

Database: logs (80 tables)
  All tables validated ✓
  Total rows: 5,892,445,022 (source) → 5,892,445,108 (target)
  Drift: +86 rows (0.0000015%) - within tolerance

## Sign-off
This migration has passed all validation checks and is certified 
for production cutover.

Consultant: [Name]
Date: 2026-01-24
```

### Integration Points

**PostgreSQL Schema:**
```sql
-- Track validation results
validation_results (validation_type, status, source_value, target_value)

-- Link to migration jobs
migration_jobs.validation_status VARCHAR(20) -- 'pending', 'passed', 'failed'
migration_jobs.last_validated_at TIMESTAMPTZ
migration_jobs.validation_details JSONB
```

**CLI Commands:**
```bash
# Validate specific table
aws2openstack validate table   --assessment-id assessment-a3f2dd   --table analytics.events_table

# Validate all tables in assessment
aws2openstack validate all   --assessment-id assessment-a3f2dd   --checks row_count,schema,checksum

# Generate certification report
aws2openstack validate report   --assessment-id assessment-a3f2dd   --output ./certification-report.pdf
```

**MCP Server Tools:**
```
get_validation_status(assessment_id)
query_failed_validations(assessment_id)
get_data_drift_trend(table_name, days)
compare_table_statistics(source_table, target_table)
```

### Business Value

**Why Validation is Core:**

1. **Risk Mitigation:** Prove data integrity before cutover
2. **Compliance:** Audit trail for regulated industries (GDPR, finance)
3. **Customer Confidence:** Certification reports provide sign-off documentation
4. **Early Detection:** Catch issues during migration, not after cutover
5. **SLA Support:** Quantifiable metrics for migration success

**Competitive Advantage:**
- Most migration tools have basic row counts only
- Comprehensive validation is rare and highly valued
- Certification reports enable consultant sign-off
- Continuous validation during shadow running is differentiator

**Implementation Priority:**
- Phase 2: Validation schema and basic row count checks
- Phase 3: Full validation suite (checksum, schema, sampling)
- Phase 4: Continuous reconciliation for shadow running

---

## Current Status

### Phase 1: Complete ✅

**Glue Catalog Assessment CLI**

```bash
aws2openstack assess glue-catalog \
  --region us-east-1 \
  --profile my-profile \
  --output-dir ./assessment
```

**Features:**
- Discovers all Glue databases and tables
- Detects table formats (Iceberg, Parquet, ORC, Avro)
- Classifies migration readiness (READY, NEEDS_CONVERSION, UNKNOWN)
- Generates JSON + Markdown reports
- 22 tests, 93% coverage, mypy strict mode compliant

**Example Output:**

```
✅ Assessment complete!
  - JSON report: ./assessment/glue-catalog-assessment.json
  - Markdown report: ./assessment/glue-catalog-assessment.md

Summary:
  - 15 databases, 150 tables
  - 45 Iceberg tables → Ready for migration
  - 80 Parquet/ORC tables → Needs conversion consideration
  - 25 Unknown format → Manual review required
```

### Phase 2: Designed 🔄

**Complete migration pipeline architecture designed:**

- PostgreSQL schema for assessments, transformations, migrations
- Transformation pipeline (5 stages: Load → Classify → Transform → Generate → Store)
- Mapping templates with rule-based conditions
- Terraform generation for Iceberg REST Catalog + Hive Metastore + Trino
- Data orchestration layer (tracking + hybrid AWS/rclone strategy)
- MCP server for Claude-based interactive exploration
- Streamlit dashboard for monitoring

**Documentation:** `docs/plans/2026-01-09-persistence-mcp-dashboard-design.md`

**Implementation ready:** 18 beads issues created and prioritized

### Phase 3+: Planned 📋

- Athena query pattern analysis
- EMR cluster assessment
- Full S3 bucket inventory
- Multi-cloud support (Azure, GCP)

---

## Quick Start

### Prerequisites

- Python 3.12+
- AWS credentials with Glue read permissions
- (Optional) PostgreSQL 15+ for Phase 2 features

### Installation

```bash
# Clone repository
git clone https://github.com/scholih/aws2openstack.git
cd aws2openstack

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Run Assessment

```bash
# Assess Glue Catalog
aws2openstack assess glue-catalog \
  --region us-east-1 \
  --output-dir ./my-assessment

# View results
cat ./my-assessment/glue-catalog-assessment.md
```

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=aws2openstack --cov-report=term-missing

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

---

## Development Setup

### Required Tooling

#### 1. Claude Desktop + MCP Servers

**Claude Desktop** with MCP servers for semantic code navigation:

- **GitHub MCP** - Repository management
- **Serena** - Semantic code editing and exploration

**Install Claude Desktop:** https://claude.ai/download

**Configure MCP Servers** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-github-token"
      }
    },
    "serena": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/YOUR_USERNAME/repos:/workspace",
        "ghcr.io/emcie-co/serena:latest"
      ]
    }
  }
}
```

#### 2. Beads Issue Tracker

Persistent issue tracking that survives conversation compaction.

**Install:**
```bash
pip install beads-project
# Or download from: https://github.com/beadsprog/beads/releases
```

**Usage:**
```bash
# View issues
bd list

# See ready work (no blockers)
bd ready

# Start working
bd update aws2openstack-tae --status in_progress

# View details
bd show aws2openstack-tae
```

**Current state:** 18 issues created for Phase 2, with dependencies mapped

#### 3. Superpowers Skills

Reusable process skills for Claude (brainstorming, TDD, code review, etc.)

**Install:**
```bash
# Clone superpowers marketplace
mkdir -p ~/.claude/plugins/cache
cd ~/.claude/plugins/cache
git clone https://github.com/coleridge-ai/superpowers-marketplace.git

# Symlink
ln -s ~/.claude/plugins/cache/superpowers-marketplace/superpowers ~/.claude/skills/superpowers
```

**Key Skills:**
- `superpowers:brainstorming` - Refine ideas into designs
- `superpowers:using-git-worktrees` - Isolated feature development
- `superpowers:test-driven-development` - TDD workflow
- `superpowers:systematic-debugging` - Debug methodology
- `superpowers:code-reviewer` - Automated code review

### Local Configuration

Local configuration files included in repo (not .gitignored) for fast onboarding:

- `.beads/` - Issue database
- `.claude/` - Project-specific Claude configuration
- `pyproject.toml` - Python dependencies

After cloning, everything is configured and ready.

### Development Workflow

```bash
# 1. Sync with main
git pull origin main

# 2. Check ready issues
bd ready

# 3. Create feature branch
git checkout -b feature/your-feature

# 4. Work with Claude
# Use Claude Desktop with Serena for semantic code editing
# Track progress: bd update <issue-id> --status in_progress

# 5. Test frequently
pytest

# 6. Commit
git add .
git commit -m "feat: your feature"

# 7. Push and PR
git push origin feature/your-feature
gh pr create
```

---

## Technology Stack

**Core:**
- Python 3.12+ (type hints, async/await)
- PostgreSQL 15+ (JSONB, arrays, UUID)
- Click (CLI framework)
- Pydantic 2.x (data validation)

**AWS Integration:**
- boto3 (AWS SDK)
- boto3-stubs (type hints)

**Transformation:**
- SQLAlchemy 2.x (ORM)
- Alembic (database migrations)
- Jinja2 (Terraform templating)

**Target Stack:**
- Terraform (infrastructure-as-code)
- Trino/Presto (query engine)
- Apache Iceberg (table format)
- Hive Metastore (metadata)
- OpenStack Swift/Ceph (object storage)

**Monitoring:**
- Streamlit (dashboard UI)
- Plotly (charts)
- MCP (Model Context Protocol for Claude integration)

**Development:**
- pytest (testing)
- mypy (type checking)
- ruff (linting)
- beads (issue tracking)

---

## Project Structure

```
aws2openstack/
├── .beads/                      # Beads issue database
├── .claude/                     # Claude project config
├── docs/
│   └── plans/                   # Design documents
├── src/aws2openstack/
│   ├── cli.py                   # CLI entry point
│   ├── models/
│   │   └── catalog.py           # Pydantic models
│   ├── assessments/
│   │   └── glue_catalog.py      # Glue assessment (Phase 1)
│   ├── reporters/
│   │   ├── json_reporter.py
│   │   └── markdown_reporter.py
│   ├── persistence/             # Phase 2 (planned)
│   ├── transformation/          # Phase 2 (planned)
│   ├── mcp_server/              # Phase 2 (planned)
│   └── dashboard/               # Phase 2 (planned)
├── tests/                       # 22 tests, 93% coverage
└── pyproject.toml
```

---

## Roadmap

### Phase 1: Complete ✅
- Glue Catalog assessment CLI
- Migration readiness classification  
- JSON + Markdown reporting
- Test coverage

### Phase 2: Next (18 issues ready) 🔄
- PostgreSQL persistence
- Transformation pipeline
- Terraform generation
- MCP server
- Streamlit dashboard
- Data orchestration tracking

### Phase 3: Planned 📋
- Athena queries
- EMR clusters
- S3 inventory
- Data copy implementation

### Phase 4: Future 📋
- Multi-service assessment
- End-to-end automation
- Validation framework

---

## Development Standards

- **Type safety:** mypy strict mode, full type hints
- **Testing:** 80%+ coverage, pytest
- **Code style:** ruff (black-compatible)
- **Commits:** Conventional commits (feat:, fix:, docs:, chore:)
- **Git workflow:** Feature branches, PRs, no direct commits to main
- **AI-assisted:** Claude + Serena for semantic editing

---

## License

TBD

---

## Contact

**Hans Scholing**  
GitHub: [@scholih](https://github.com/scholih)  
Repository: https://github.com/scholih/aws2openstack
