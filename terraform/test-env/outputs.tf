output "test_data_bucket" {
  description = "S3 bucket name for test data"
  value       = aws_s3_bucket.test_data.bucket
}

output "test_data_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.test_data.arn
}

output "glue_databases" {
  description = "Glue database names"
  value = concat(
    [aws_glue_catalog_database.analytics.name],
    var.database_count >= 2 ? [aws_glue_catalog_database.logs[0].name] : []
  )
}

output "glue_tables" {
  description = "Glue table names by database"
  value = {
    (aws_glue_catalog_database.analytics.name) = [
      aws_glue_catalog_table.sales_data.name,
      aws_glue_catalog_table.customer_data.name,
      aws_glue_catalog_table.events_raw.name,
      aws_glue_catalog_table.metrics_orc.name,
    ]
    (var.database_count >= 2 ? aws_glue_catalog_database.logs[0].name : "none") = var.database_count >= 2 ? [
      aws_glue_catalog_table.access_logs[0].name,
    ] : []
  }
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment_name" {
  description = "Environment name"
  value       = var.environment_name
}
