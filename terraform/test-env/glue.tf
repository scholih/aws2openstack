# Glue Database: Analytics
resource "aws_glue_catalog_database" "analytics" {
  name        = "${var.environment_name}_analytics"
  description = "Test analytics database for migration assessment"
}

# Glue Database: Logs
resource "aws_glue_catalog_database" "logs" {
  count = var.database_count >= 2 ? 1 : 0

  name        = "${var.environment_name}_logs"
  description = "Test logs database for migration assessment"
}

# Table 1: Sales Data (Parquet, partitioned by year/month)
resource "aws_glue_catalog_table" "sales_data" {
  database_name = aws_glue_catalog_database.analytics.name
  name          = "sales_data"

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.test_data.bucket}/sales-parquet/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "order_id"
      type = "bigint"
    }

    columns {
      name = "customer_id"
      type = "bigint"
    }

    columns {
      name = "amount"
      type = "decimal(10,2)"
    }

    columns {
      name = "quantity"
      type = "bigint"
    }

    columns {
      name = "product_name"
      type = "string"
    }

    columns {
      name = "order_date"
      type = "timestamp"
    }

    columns {
      name = "region"
      type = "string"
    }

    columns {
      name = "status"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }
}

# Table 2: Customer Data (Iceberg/Parquet)
resource "aws_glue_catalog_table" "customer_data" {
  database_name = aws_glue_catalog_database.analytics.name
  name          = "customer_data"

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.test_data.bucket}/customers-iceberg/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "customer_id"
      type = "bigint"
    }

    columns {
      name = "name"
      type = "string"
    }

    columns {
      name = "email"
      type = "string"
    }

    columns {
      name = "signup_date"
      type = "date"
    }

    columns {
      name = "tier"
      type = "string"
    }

    columns {
      name = "lifetime_value"
      type = "decimal(10,2)"
    }
  }
}

# Table 3: Events Data (Parquet, partitioned by date)
resource "aws_glue_catalog_table" "events_raw" {
  database_name = aws_glue_catalog_database.analytics.name
  name          = "events_raw"

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.test_data.bucket}/events-parquet/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "event_id"
      type = "string"
    }

    columns {
      name = "user_id"
      type = "bigint"
    }

    columns {
      name = "event_type"
      type = "string"
    }

    columns {
      name = "timestamp"
      type = "timestamp"
    }

    columns {
      name = "properties"
      type = "string"
    }
  }

  partition_keys {
    name = "date"
    type = "date"
  }
}

# Table 4: Metrics ORC (using Parquet as proxy)
resource "aws_glue_catalog_table" "metrics_orc" {
  database_name = aws_glue_catalog_database.analytics.name
  name          = "metrics_orc"

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.test_data.bucket}/metrics-orc/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "metric_name"
      type = "string"
    }

    columns {
      name = "value"
      type = "double"
    }

    columns {
      name = "timestamp"
      type = "timestamp"
    }

    columns {
      name = "tags"
      type = "string"
    }
  }
}

# Table 5: Access Logs (CSV, partitioned by date)
resource "aws_glue_catalog_table" "access_logs" {
  count = var.database_count >= 2 ? 1 : 0

  database_name = aws_glue_catalog_database.logs[0].name
  name          = "access_logs"

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.test_data.bucket}/access-logs-csv/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"

      parameters = {
        "separatorChar" = ","
        "skip.header.line.count" = "1"
      }
    }

    columns {
      name = "timestamp"
      type = "timestamp"
    }

    columns {
      name = "ip_address"
      type = "string"
    }

    columns {
      name = "method"
      type = "string"
    }

    columns {
      name = "path"
      type = "string"
    }

    columns {
      name = "status_code"
      type = "int"
    }

    columns {
      name = "response_time_ms"
      type = "int"
    }

    columns {
      name = "user_agent"
      type = "string"
    }
  }

  partition_keys {
    name = "date"
    type = "date"
  }
}
