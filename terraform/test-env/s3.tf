# S3 bucket for test data
resource "aws_s3_bucket" "test_data" {
  bucket = "aws2openstack-test-data-${random_string.suffix.result}"

  # Allow force destroy for clean teardown
  force_destroy = true
}

# Block public access
resource "aws_s3_bucket_public_access_block" "test_data" {
  bucket = aws_s3_bucket.test_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rule for safety (delete after 7 days)
resource "aws_s3_bucket_lifecycle_configuration" "test_data" {
  bucket = aws_s3_bucket.test_data.id

  rule {
    id     = "delete-old-objects"
    status = "Enabled"

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}
