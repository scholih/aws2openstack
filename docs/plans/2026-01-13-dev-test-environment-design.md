# Dev/Test Environment Design

**Date:** 2026-01-13
**Status:** Approved
**Owner:** hjscholing

## Overview

Design for an ephemeral dev/test environment that creates AWS Glue Catalog resources with test data for rapid development and testing. The environment can be created and destroyed with a single command using Terraform and Docker Compose.

## Goals

- **Fast provisioning**: Create complete test environment in <5 minutes
- **Single command**: `make test-env-up` creates everything, `make test-env-down` destroys it
- **Cost effective**: Minimal AWS resources, local PostgreSQL
- **Realistic testing**: Multiple data formats, proper Glue schemas
- **Clean teardown**: Force-delete all resources including S3 data

## Architecture

### Three-Layer Design

**Layer 1: Infrastructure Foundation**
- S3 bucket for Terraform state (long-lived)
- DynamoDB table for state locking
- Local PostgreSQL via Docker Compose

**Layer 2: Test AWS Resources (ephemeral)**
- 1-2 Glue databases
- 5-10 Glue tables (all migration-ready)
- S3 buckets with test data
- All in eu-central-1 region

**Layer 3: Test Data Generation**
- Python script generates synthetic data
- Multiple formats: Parquet, ORC, Iceberg, CSV
- Small file sizes (KB-MB range)
- Deterministic and reproducible

### Component Interaction

```
make test-env-up
  ├─> docker compose up (PostgreSQL)
  ├─> python generate_test_data.py (create files)
  ├─> terraform apply (provision AWS)
  ├─> aws s3 sync (upload data)
  └─> alembic upgrade head (migrate DB)
```

## Terraform Structure

### Directory Layout

```
terraform/
├── bootstrap/
│   ├── main.tf          # S3 state bucket + DynamoDB
│   ├── outputs.tf       # Bucket/table names
│   └── variables.tf     # Region, naming
└── test-env/
    ├── main.tf          # Provider + backend config
    ├── glue.tf          # Glue databases and tables
    ├── s3.tf            # Test data buckets
    ├── variables.tf     # Configuration parameters
    └── outputs.tf       # Export resource details
```

### Bootstrap Resources (terraform/bootstrap/)

**Purpose:** One-time setup of Terraform state infrastructure

**Resources:**
- `aws_s3_bucket.terraform_state` - Stores .tfstate files
- `aws_s3_bucket_versioning` - Enable versioning for recovery
- `aws_s3_bucket_server_side_encryption_configuration` - AES256 encryption
- `aws_dynamodb_table.terraform_locks` - State locking
  - Hash key: `LockID`
  - Billing mode: PAY_PER_REQUEST

**State Management:** Uses local state (bootstrap.tfstate)

**Tags:**
- `Project: aws2openstack`
- `Component: terraform-state`
- `Lifecycle: permanent`

### Test Environment Resources (terraform/test-env/)

**Backend Configuration:**
```hcl
terraform {
  backend "s3" {
    bucket         = "aws2openstack-tfstate-<random>"
    key            = "test-env/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "aws2openstack-tfstate-locks"
    encrypt        = true
  }
}
```

**Glue Databases:**
- Database 1: `test_analytics` (3 tables)
- Database 2: `test_logs` (2 tables)

**Glue Tables:**

| Table | Format | Partitions | Columns | Notes |
|-------|--------|------------|---------|-------|
| sales_data | Parquet | year, month | 8 | Partitioned, ready |
| customer_data | Iceberg | none | 6 | Iceberg, ready |
| events_raw | Parquet | date | 5 | Single partition, ready |
| metrics_orc | ORC | none | 4 | ORC format, ready |
| access_logs | CSV | date | 7 | CSV, ready |

All tables have `migration_readiness=ready` status.

**S3 Buckets:**
- `aws2openstack-test-data-<random>` - Main test data bucket
- `force_destroy = true` for clean teardown
- Lifecycle rules: Delete all objects after 7 days (safety net)

**Resource Tagging:**
- `Environment: test`
- `ManagedBy: terraform`
- `Project: aws2openstack`
- `Lifecycle: ephemeral`

**Variables:**
```hcl
variable "aws_region" {
  default = "eu-central-1"
}

variable "environment_name" {
  default = "test"
}

variable "database_count" {
  default = 2
}

variable "tables_per_database" {
  default = 5
}
```

## Test Data Generation

### Script: scripts/generate_test_data.py

**Dependencies:**
- pandas >= 2.1.0
- pyarrow >= 14.0.0
- faker >= 20.0.0 (for realistic synthetic data)

**Output Directory:** `testdata/generated/` (gitignored)

**Data Schemas:**

**Sales Data (Parquet, partitioned by year/month):**
```python
{
    'order_id': int,
    'customer_id': int,
    'amount': decimal,
    'quantity': int,
    'product_name': str,
    'order_date': timestamp,
    'region': str,
    'status': str
}
```

**Customer Data (Iceberg):**
```python
{
    'customer_id': int,
    'name': str,
    'email': str,
    'signup_date': date,
    'tier': str,
    'lifetime_value': decimal
}
```

**Events Raw (Parquet, partitioned by date):**
```python
{
    'event_id': str,
    'user_id': int,
    'event_type': str,
    'timestamp': timestamp,
    'properties': json
}
```

**Metrics ORC (ORC):**
```python
{
    'metric_name': str,
    'value': float,
    'timestamp': timestamp,
    'tags': array<str>
}
```

**Access Logs (CSV, partitioned by date):**
```python
{
    'timestamp': timestamp,
    'ip_address': str,
    'method': str,
    'path': str,
    'status_code': int,
    'response_time_ms': int,
    'user_agent': str
}
```

**Generation Parameters:**
- Rows per file: 1000 (configurable)
- Random seed: 42 (deterministic)
- Total size: ~5-10 MB
- Partitions: 2-3 per partitioned table

**Script Features:**
- Progress output with file sizes
- Validation of generated files
- Cleanup on error
- Exit codes for Makefile integration

## Docker Compose Setup

### File: docker/docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: aws2openstack-test-db
    environment:
      POSTGRES_DB: aws2openstack_test
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d aws2openstack_test"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
```

### Environment File: .env.test

```bash
# Database
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/aws2openstack_test

# AWS Configuration
AWS_REGION=eu-central-1
AWS_PROFILE=default

# Test Data Configuration
TEST_DATA_SIZE=small
TEST_DATA_ROWS=1000
```

**Usage:** `source .env.test` before running commands

## Makefile Orchestration

### File: Makefile

**Targets:**

**`make bootstrap`** - One-time setup
```makefile
bootstrap:
    @echo "🏗️  Creating Terraform state infrastructure..."
    cd terraform/bootstrap && terraform init
    cd terraform/bootstrap && terraform apply
    @echo "✅ Bootstrap complete. State bucket ready."
```

**`make test-env-up`** - Full environment creation
```makefile
test-env-up:
    @echo "🚀 Starting dev/test environment..."
    # Step 1: Start PostgreSQL
    docker compose -f docker/docker-compose.yml up -d
    @echo "⏳ Waiting for PostgreSQL..."
    @sleep 10
    # Step 2: Generate test data
    @echo "📊 Generating test data..."
    python scripts/generate_test_data.py
    # Step 3: Provision AWS resources
    @echo "☁️  Provisioning AWS resources..."
    cd terraform/test-env && terraform init
    cd terraform/test-env && terraform apply -auto-approve
    # Step 4: Upload test data to S3
    @echo "📤 Uploading test data to S3..."
    ./scripts/upload_test_data.sh
    # Step 5: Run database migrations
    @echo "🗄️  Running database migrations..."
    source .env.test && alembic upgrade head
    @echo "✅ Environment ready!"
    @make test-env-status
```

**`make test-env-down`** - Clean teardown
```makefile
test-env-down:
    @echo "🧹 Tearing down test environment..."
    cd terraform/test-env && terraform destroy -auto-approve
    docker compose -f docker/docker-compose.yml down
    @echo "✅ Environment destroyed."
```

**`make test-env-clean`** - Full cleanup
```makefile
test-env-clean: test-env-down
    @echo "🗑️  Removing generated data..."
    rm -rf testdata/generated/
    @echo "✅ Clean complete."
```

**`make test-env-status`** - Show environment state
```makefile
test-env-status:
    @echo "📊 Test Environment Status"
    @echo "─────────────────────────"
    @docker compose -f docker/docker-compose.yml ps
    @echo ""
    @cd terraform/test-env && terraform output
```

**Helper Targets:**
- `make test-env-logs` - PostgreSQL logs
- `make test-env-shell` - psql shell
- `make test-env-validate` - Pre-flight checks

### Pre-flight Checks (make test-env-validate)

Validates before provisioning:
- ✓ AWS CLI installed and configured
- ✓ Terraform >= 1.5 installed
- ✓ Docker daemon running
- ✓ Python >= 3.12 available
- ✓ Port 5432 available
- ✓ AWS credentials valid
- ✓ Sufficient disk space

## Error Handling & Recovery

### Terraform Failures

**Scenario:** `terraform apply` fails mid-run

**Recovery:**
1. State is preserved in S3
2. Re-run `make test-env-up` - continues from last state
3. Manual inspection: `cd terraform/test-env && terraform state list`
4. Force cleanup: `make test-env-down` (always runs destroy)

**State Lock Issues:**
```bash
# Check lock
aws dynamodb get-item \
  --table-name aws2openstack-tfstate-locks \
  --key '{"LockID":{"S":"aws2openstack-tfstate/test-env/terraform.tfstate"}}'

# Force unlock (if stale)
cd terraform/test-env && terraform force-unlock <lock-id>
```

### Data Generation Failures

**Checks:**
- Output directory writable
- AWS credentials valid
- Sufficient disk space
- Python dependencies installed

**On Failure:**
- Cleans up partial files
- Exits with non-zero code
- Makefile stops provisioning

### Docker Compose Issues

**Health Check:** 10 retries x 5s = 50s max wait

**Common Issues:**
- Port 5432 in use → Clear error, suggest `lsof -i :5432`
- Container fails → Show logs via `make test-env-logs`
- Volume permission issues → Document chown/chmod fix

### Common Scenarios

**AWS credentials expired:**
```
❌ Error: AWS credentials expired
→ Run: aws sso login --profile <profile>
```

**S3 bucket name conflict:**
- Uses random suffix (timestamp + 4 random chars)
- Example: `aws2openstack-test-data-20260113-x7k2`

**Terraform state locked:**
```
❌ Error: State locked by user@host
→ Lock ID: <uuid>
→ To force unlock: cd terraform/test-env && terraform force-unlock <uuid>
```

**PostgreSQL migration fails:**
- Alembic rollback to previous version
- Data preserved
- Manual fix: `source .env.test && alembic downgrade -1`

## Testing the Environment

### Workflow After Provisioning

**1. Run Assessment:**
```bash
source .env.test
aws2openstack assess glue-catalog \
  --region eu-central-1 \
  --output-dir ./output \
  --save-to-db
```

**2. View in Dashboard:**
```bash
streamlit run src/aws2openstack/dashboard/app.py
```

**3. Query via MCP:**
```bash
# Start MCP server
python -m aws2openstack.mcp_server.server

# Or test tools directly
pytest tests/test_mcp_server.py
```

### Validation Checks

After `make test-env-up` succeeds:
- ✓ PostgreSQL accessible on localhost:5432
- ✓ Glue databases visible: `aws glue get-databases`
- ✓ Glue tables visible: `aws glue get-tables --database test_analytics`
- ✓ S3 data uploaded: `aws s3 ls s3://aws2openstack-test-data-<random>/`
- ✓ Alembic migrations applied: `alembic current`

## Cost Estimation

**Monthly Cost (if left running 24/7):**
- Glue Catalog: $0 (first million objects free)
- S3 storage: ~$0.02 (10 MB @ $0.023/GB)
- S3 requests: ~$0.01 (setup/teardown)
- DynamoDB: ~$0.25 (PAY_PER_REQUEST, minimal usage)
- **Total: ~$0.30/month**

**Recommended Usage:**
- Create when needed, destroy after testing
- Cost per dev session: ~$0.001 (negligible)

## Security Considerations

### IAM Permissions Required

**Terraform Operations:**
- `s3:*` on state bucket
- `dynamodb:*` on lock table
- `glue:*` on test databases/tables
- `s3:*` on test data buckets

**Principle of Least Privilege:**
- Create dedicated IAM user for test environment
- Restrict to eu-central-1 region
- Tag-based policies: `Lifecycle: ephemeral`

### Secrets Management

**Not stored in code:**
- PostgreSQL password (environment variable)
- AWS credentials (AWS CLI profile)
- Terraform state encryption key (AWS manages)

**Committed to git:**
- Terraform code (no secrets)
- Generated test data (synthetic, no PII)
- Docker Compose config (default local password okay)

## Documentation Requirements

### README Updates

**New Section:** "Development Environment Setup"
```markdown
## Development Environment

### Prerequisites
- AWS CLI configured with credentials
- Docker and Docker Compose
- Terraform >= 1.5
- Python >= 3.12

### Quick Start
# One-time setup
make bootstrap

# Create test environment
make test-env-up

# Run assessment
source .env.test
aws2openstack assess glue-catalog \
  --region eu-central-1 \
  --output-dir ./output \
  --save-to-db

# View results
streamlit run src/aws2openstack/dashboard/app.py

# Teardown
make test-env-down
```

### Troubleshooting Guide

**Common Issues:** Document in `docs/troubleshooting.md`
- Port conflicts
- AWS credential issues
- Terraform state lock problems
- PostgreSQL connection errors

## Implementation Plan

### Phase 1: Foundation (1-2 hours)
1. Create directory structure
2. Write Terraform bootstrap config
3. Write Docker Compose file
4. Create Makefile with bootstrap target
5. Test: `make bootstrap` succeeds

### Phase 2: Test Data Generation (2-3 hours)
1. Write Python data generation script
2. Add dependencies to pyproject.toml
3. Create example schemas
4. Test: Script generates valid files

### Phase 3: Terraform Test Environment (2-3 hours)
1. Write main.tf with backend config
2. Write glue.tf with databases/tables
3. Write s3.tf with buckets
4. Write variables.tf and outputs.tf
5. Test: `terraform apply` succeeds

### Phase 4: Orchestration (1-2 hours)
1. Complete Makefile targets
2. Write upload_test_data.sh script
3. Add pre-flight checks
4. Test: Full `make test-env-up` workflow

### Phase 5: Documentation (1 hour)
1. Update README
2. Create troubleshooting guide
3. Add inline comments
4. Write usage examples

**Total Estimated Time:** 7-11 hours

## Success Criteria

- ✓ `make bootstrap` creates state infrastructure
- ✓ `make test-env-up` provisions everything in <5 minutes
- ✓ Assessment tool successfully catalogs test resources
- ✓ Dashboard displays test assessment data
- ✓ `make test-env-down` cleanly destroys all resources
- ✓ No manual AWS console operations required
- ✓ Idempotent - can run multiple times safely

## Future Enhancements

**Not in initial scope:**
- Multiple environment profiles (small/medium/large)
- CI/CD integration for automated testing
- Cost tracking and alerts
- Multi-region support
- Shared team environments

These can be added later based on actual usage patterns.

## References

- Terraform AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- AWS Glue Terraform: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_table
- Docker Compose: https://docs.docker.com/compose/
- PostgreSQL Docker: https://hub.docker.com/_/postgres
