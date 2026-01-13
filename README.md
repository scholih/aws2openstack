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
