.PHONY: bootstrap test-env-up test-env-down test-env-clean test-env-status test-env-logs test-env-shell test-env-validate help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)AWS2OpenStack Dev/Test Environment$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}'

bootstrap: ## One-time setup of Terraform state infrastructure
	@echo "$(BLUE)🏗️  Creating Terraform state infrastructure...$(NC)"
	@cd terraform/bootstrap && terraform init
	@cd terraform/bootstrap && terraform apply
	@echo "$(GREEN)✅ Bootstrap complete. State bucket ready.$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Copy the backend configuration from outputs above"
	@echo "  2. Add it to terraform/test-env/main.tf"
	@echo "  3. Run: make test-env-up"

test-env-validate: ## Check prerequisites before provisioning
	@echo "$(BLUE)🔍 Validating prerequisites...$(NC)"
	@command -v aws >/dev/null 2>&1 || { echo "$(RED)❌ AWS CLI not found$(NC)"; exit 1; }
	@command -v terraform >/dev/null 2>&1 || { echo "$(RED)❌ Terraform not found$(NC)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)❌ Docker not found$(NC)"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)❌ Python 3 not found$(NC)"; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "$(RED)❌ Docker daemon not running$(NC)"; exit 1; }
	@aws sts get-caller-identity >/dev/null 2>&1 || { echo "$(RED)❌ AWS credentials not configured$(NC)"; exit 1; }
	@terraform version | grep -q "v1\.[5-9]\|v1\.[1-9][0-9]" || { echo "$(RED)❌ Terraform >= 1.5 required$(NC)"; exit 1; }
	@lsof -i :5432 >/dev/null 2>&1 && { echo "$(RED)❌ Port 5432 already in use$(NC)"; exit 1; } || true
	@echo "$(GREEN)✅ All prerequisites satisfied$(NC)"

test-env-up: test-env-validate ## Create full dev/test environment
	@echo "$(BLUE)🚀 Starting dev/test environment...$(NC)"
	@if [ ! -f .env.test ]; then \
		echo "$(YELLOW)⚠️  Creating .env.test from template...$(NC)"; \
		cp .env.test.template .env.test; \
	fi
	@echo "$(BLUE)🐘 Starting PostgreSQL...$(NC)"
	@docker compose -f docker/docker-compose.yml up -d
	@echo "$(YELLOW)⏳ Waiting for PostgreSQL health check...$(NC)"
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker exec aws2openstack-test-db pg_isready -U testuser -d aws2openstack_test >/dev/null 2>&1; then \
			echo "$(GREEN)✅ PostgreSQL ready$(NC)"; \
			break; \
		fi; \
		sleep 1; \
		timeout=$$((timeout - 1)); \
	done; \
	if [ $$timeout -eq 0 ]; then \
		echo "$(RED)❌ PostgreSQL failed to start$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)📊 Generating test data...$(NC)"
	@python3 scripts/generate_test_data.py
	@echo "$(BLUE)☁️  Provisioning AWS resources...$(NC)"
	@cd terraform/test-env && terraform init
	@cd terraform/test-env && terraform apply -auto-approve
	@echo "$(BLUE)📤 Uploading test data to S3...$(NC)"
	@./scripts/upload_test_data.sh
	@echo "$(BLUE)🗄️  Running database migrations...$(NC)"
	@. .env.test && alembic upgrade head
	@echo "$(GREEN)✅ Environment ready!$(NC)"
	@echo ""
	@make test-env-status

test-env-down: ## Destroy test environment (keeps PostgreSQL data)
	@echo "$(BLUE)🧹 Tearing down test environment...$(NC)"
	@cd terraform/test-env && terraform destroy -auto-approve || true
	@docker compose -f docker/docker-compose.yml down
	@echo "$(GREEN)✅ Environment destroyed$(NC)"

test-env-clean: test-env-down ## Full cleanup including generated data
	@echo "$(BLUE)🗑️  Removing generated test data...$(NC)"
	@rm -rf testdata/generated/
	@echo "$(GREEN)✅ Clean complete$(NC)"

test-env-status: ## Show environment status
	@echo "$(BLUE)📊 Test Environment Status$(NC)"
	@echo "─────────────────────────────────────────"
	@echo "$(YELLOW)Docker Containers:$(NC)"
	@docker compose -f docker/docker-compose.yml ps || true
	@echo ""
	@if [ -d terraform/test-env/.terraform ]; then \
		echo "$(YELLOW)Terraform Outputs:$(NC)"; \
		cd terraform/test-env && terraform output 2>/dev/null || echo "  No outputs available"; \
	else \
		echo "$(YELLOW)Terraform:$(NC) Not initialized"; \
	fi

test-env-logs: ## Show PostgreSQL container logs
	@docker compose -f docker/docker-compose.yml logs -f postgres

test-env-shell: ## Open psql shell to test database
	@docker exec -it aws2openstack-test-db psql -U testuser -d aws2openstack_test
