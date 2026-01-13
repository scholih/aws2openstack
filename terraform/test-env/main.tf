terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend configuration - will be configured after bootstrap
  # Run `make bootstrap` first to create state bucket
  # Then uncomment and update with actual bucket name from bootstrap outputs
  #
  # backend "s3" {
  #   bucket         = "aws2openstack-tfstate-XXXXXXXX"
  #   key            = "test-env/terraform.tfstate"
  #   region         = "eu-central-1"
  #   dynamodb_table = "aws2openstack-tfstate-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aws2openstack"
      Environment = var.environment_name
      ManagedBy   = "terraform"
      Lifecycle   = "ephemeral"
    }
  }
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}
