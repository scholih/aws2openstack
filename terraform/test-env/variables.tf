variable "aws_region" {
  description = "AWS region for test environment"
  type        = string
  default     = "eu-central-1"
}

variable "environment_name" {
  description = "Environment name (test, dev, etc.)"
  type        = string
  default     = "test"
}

variable "database_count" {
  description = "Number of Glue databases to create"
  type        = number
  default     = 2

  validation {
    condition     = var.database_count >= 1 && var.database_count <= 5
    error_message = "Database count must be between 1 and 5."
  }
}
