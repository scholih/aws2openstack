variable "aws_region" {
  description = "AWS region for Terraform state infrastructure"
  type        = string
  default     = "eu-central-1"
}

variable "state_bucket_prefix" {
  description = "Prefix for Terraform state S3 bucket name"
  type        = string
  default     = "aws2openstack-tfstate"
}

variable "lock_table_name" {
  description = "DynamoDB table name for Terraform state locking"
  type        = string
  default     = "aws2openstack-tfstate-locks"
}
