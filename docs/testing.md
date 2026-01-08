# Testing Guide

## Running Tests

### All Tests
```bash
pytest
```

### With Coverage
```bash
pytest --cov=aws2openstack --cov-report=html
# Open htmlcov/index.html in browser
```

### Specific Test Files
```bash
pytest tests/test_models.py -v
pytest tests/test_glue_catalog.py -v
pytest tests/test_reporters.py -v
pytest tests/test_cli.py -v
pytest tests/test_integration.py -v
```

## Manual Testing

### Test with Mocked AWS (No AWS Account Required)

All unit tests use mocks, so you can run the full test suite without AWS credentials.

### Test with Real AWS Account (Optional)

If you have an AWS account with Glue Catalog:

1. Set up AWS credentials:
   ```bash
   aws configure --profile test-profile
   ```

2. Run the CLI:
   ```bash
   aws2openstack assess glue-catalog \
     --region us-east-1 \
     --profile test-profile \
     --output-dir ./test-output
   ```

3. Verify outputs:
   ```bash
   cat ./test-output/glue-catalog-assessment.md
   cat ./test-output/glue-catalog-assessment.json | jq
   ```

## Type Checking

```bash
mypy src/ --strict
```

## Code Quality

```bash
# Check with ruff
ruff check src/ tests/

# Format with ruff
ruff format src/ tests/
```

## Test Coverage Goals

- **Minimum**: 80% coverage
- **Target**: 90%+ coverage for core logic
- **Models**: 100% coverage
- **Assessments**: 90%+ coverage
- **Reporters**: 90%+ coverage
- **CLI**: 80%+ coverage (integration tested)
