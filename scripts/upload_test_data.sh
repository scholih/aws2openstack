#!/usr/bin/env bash
# Upload generated test data to S3 bucket

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get S3 bucket name from Terraform output
BUCKET_NAME=$(cd terraform/test-env && terraform output -raw test_data_bucket 2>/dev/null)

if [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}❌ Error: Could not get S3 bucket name from Terraform${NC}"
    echo "Make sure Terraform has been applied successfully"
    exit 1
fi

echo -e "${BLUE}📤 Uploading test data to S3: ${BUCKET_NAME}${NC}"

# Check if test data exists
if [ ! -d "testdata/generated" ]; then
    echo -e "${RED}❌ Error: testdata/generated/ directory not found${NC}"
    echo "Run: python3 scripts/generate_test_data.py"
    exit 1
fi

# Upload each dataset
echo -e "${YELLOW}  Uploading sales-parquet/...${NC}"
aws s3 sync testdata/generated/sales-parquet/ "s3://${BUCKET_NAME}/sales-parquet/" --quiet

echo -e "${YELLOW}  Uploading customers-iceberg/...${NC}"
aws s3 sync testdata/generated/customers-iceberg/ "s3://${BUCKET_NAME}/customers-iceberg/" --quiet

echo -e "${YELLOW}  Uploading events-parquet/...${NC}"
aws s3 sync testdata/generated/events-parquet/ "s3://${BUCKET_NAME}/events-parquet/" --quiet

echo -e "${YELLOW}  Uploading metrics-orc/...${NC}"
aws s3 sync testdata/generated/metrics-orc/ "s3://${BUCKET_NAME}/metrics-orc/" --quiet

echo -e "${YELLOW}  Uploading access-logs-csv/...${NC}"
aws s3 sync testdata/generated/access-logs-csv/ "s3://${BUCKET_NAME}/access-logs-csv/" --quiet

echo -e "${GREEN}✅ Upload complete${NC}"
echo -e "${BLUE}📊 S3 Contents:${NC}"
aws s3 ls "s3://${BUCKET_NAME}/" --human-readable --summarize
