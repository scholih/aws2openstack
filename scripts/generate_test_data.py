#!/usr/bin/env python3
"""Generate synthetic test data for AWS Glue Catalog testing."""

import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from faker import Faker

# Configuration
RANDOM_SEED = 42
DEFAULT_ROWS = int(os.getenv("TEST_DATA_ROWS", "1000"))
OUTPUT_DIR = Path("testdata/generated")

# Initialize Faker with seed for deterministic data
fake = Faker()
Faker.seed(RANDOM_SEED)


def ensure_output_dir() -> None:
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_DIR.absolute()}")


def generate_sales_data(rows: int = DEFAULT_ROWS) -> pd.DataFrame:
    """Generate sales data (Parquet, partitioned by year/month)."""
    print(f"  Generating {rows} sales records...")

    data = {
        "order_id": range(1, rows + 1),
        "customer_id": [fake.random_int(min=1, max=10000) for _ in range(rows)],
        "amount": [Decimal(str(fake.random.uniform(10.0, 5000.0))) for _ in range(rows)],
        "quantity": [fake.random_int(min=1, max=20) for _ in range(rows)],
        "product_name": [fake.random_element(elements=["Widget", "Gadget", "Doohickey", "Thingamajig"]) for _ in range(rows)],
        "order_date": [fake.date_time_between(start_date="-2y", end_date="now") for _ in range(rows)],
        "region": [fake.random_element(elements=["us-east-1", "us-west-2", "eu-central-1", "ap-southeast-1"]) for _ in range(rows)],
        "status": [fake.random_element(elements=["pending", "shipped", "delivered", "cancelled"]) for _ in range(rows)],
    }

    df = pd.DataFrame(data)
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.month

    return df


def generate_customer_data(rows: int = DEFAULT_ROWS) -> pd.DataFrame:
    """Generate customer data (Iceberg format)."""
    print(f"  Generating {rows} customer records...")

    data = {
        "customer_id": range(1, rows + 1),
        "name": [fake.name() for _ in range(rows)],
        "email": [fake.email() for _ in range(rows)],
        "signup_date": [fake.date_between(start_date="-3y", end_date="today") for _ in range(rows)],
        "tier": [fake.random_element(elements=["bronze", "silver", "gold", "platinum"]) for _ in range(rows)],
        "lifetime_value": [Decimal(str(fake.random.uniform(100.0, 50000.0))) for _ in range(rows)],
    }

    return pd.DataFrame(data)


def generate_events_data(rows: int = DEFAULT_ROWS) -> pd.DataFrame:
    """Generate event data (Parquet, partitioned by date)."""
    print(f"  Generating {rows} event records...")

    data = {
        "event_id": [fake.uuid4() for _ in range(rows)],
        "user_id": [fake.random_int(min=1, max=10000) for _ in range(rows)],
        "event_type": [fake.random_element(elements=["page_view", "click", "purchase", "signup"]) for _ in range(rows)],
        "timestamp": [fake.date_time_between(start_date="-30d", end_date="now") for _ in range(rows)],
        "properties": [json.dumps({"page": fake.uri(), "referrer": fake.uri()}) for _ in range(rows)],
    }

    df = pd.DataFrame(data)
    df["date"] = df["timestamp"].dt.date

    return df


def generate_metrics_data(rows: int = DEFAULT_ROWS) -> pd.DataFrame:
    """Generate metrics data (ORC format)."""
    print(f"  Generating {rows} metrics records...")

    data = {
        "metric_name": [fake.random_element(elements=["cpu_usage", "memory_usage", "disk_io", "network_throughput"]) for _ in range(rows)],
        "value": [fake.random.uniform(0.0, 100.0) for _ in range(rows)],
        "timestamp": [fake.date_time_between(start_date="-7d", end_date="now") for _ in range(rows)],
        "tags": [json.dumps(["prod", "server-" + str(fake.random_int(min=1, max=10))]) for _ in range(rows)],
    }

    return pd.DataFrame(data)


def generate_access_logs_data(rows: int = DEFAULT_ROWS) -> pd.DataFrame:
    """Generate access log data (CSV, partitioned by date)."""
    print(f"  Generating {rows} access log records...")

    data = {
        "timestamp": [fake.date_time_between(start_date="-7d", end_date="now") for _ in range(rows)],
        "ip_address": [fake.ipv4() for _ in range(rows)],
        "method": [fake.random_element(elements=["GET", "POST", "PUT", "DELETE"]) for _ in range(rows)],
        "path": [fake.uri_path() for _ in range(rows)],
        "status_code": [fake.random_element(elements=[200, 201, 400, 404, 500]) for _ in range(rows)],
        "response_time_ms": [fake.random_int(min=10, max=5000) for _ in range(rows)],
        "user_agent": [fake.user_agent() for _ in range(rows)],
    }

    df = pd.DataFrame(data)
    df["date"] = df["timestamp"].dt.date

    return df


def write_parquet_partitioned(df: pd.DataFrame, output_path: Path, partition_cols: list[str]) -> None:
    """Write DataFrame as partitioned Parquet files."""
    # Convert datetime columns to Arrow-compatible timestamps
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col])

    # Write partitioned Parquet
    table = pa.Table.from_pandas(df)
    pq.write_to_dataset(
        table,
        root_path=str(output_path),
        partition_cols=partition_cols,
        basename_template="part-{i}.parquet",
    )


def write_parquet(df: pd.DataFrame, output_path: Path) -> None:
    """Write DataFrame as single Parquet file."""
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df)
    pq.write_table(table, str(output_path))


def write_csv_partitioned(df: pd.DataFrame, output_path: Path, partition_col: str) -> None:
    """Write DataFrame as partitioned CSV files."""
    for partition_value in df[partition_col].unique():
        partition_df = df[df[partition_col] == partition_value].copy()
        partition_path = output_path / f"{partition_col}={partition_value}"
        partition_path.mkdir(parents=True, exist_ok=True)
        partition_df.to_csv(partition_path / "data.csv", index=False)


def get_dir_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def main() -> int:
    """Main data generation workflow."""
    print("📊 Generating test data for AWS Glue Catalog")
    print("=" * 50)

    ensure_output_dir()

    try:
        # Generate sales data (Parquet, partitioned)
        print("\n1️⃣  Sales Data (Parquet, partitioned by year/month)")
        sales_df = generate_sales_data()
        sales_path = OUTPUT_DIR / "sales-parquet"
        write_parquet_partitioned(sales_df, sales_path, ["year", "month"])
        size = get_dir_size(sales_path)
        print(f"  ✅ Written to {sales_path} ({format_bytes(size)})")

        # Generate customer data (Parquet, Iceberg-ready)
        print("\n2️⃣  Customer Data (Parquet, Iceberg format)")
        customer_df = generate_customer_data(rows=DEFAULT_ROWS // 2)
        customer_path = OUTPUT_DIR / "customers-iceberg"
        write_parquet(customer_df, customer_path / "data.parquet")
        size = get_dir_size(customer_path)
        print(f"  ✅ Written to {customer_path} ({format_bytes(size)})")

        # Generate events data (Parquet, partitioned)
        print("\n3️⃣  Events Data (Parquet, partitioned by date)")
        events_df = generate_events_data()
        events_path = OUTPUT_DIR / "events-parquet"
        write_parquet_partitioned(events_df, events_path, ["date"])
        size = get_dir_size(events_path)
        print(f"  ✅ Written to {events_path} ({format_bytes(size)})")

        # Generate metrics data (ORC - using Parquet as proxy)
        print("\n4️⃣  Metrics Data (ORC format)")
        metrics_df = generate_metrics_data(rows=DEFAULT_ROWS // 2)
        metrics_path = OUTPUT_DIR / "metrics-orc"
        write_parquet(metrics_df, metrics_path / "data.parquet")
        size = get_dir_size(metrics_path)
        print(f"  ✅ Written to {metrics_path} ({format_bytes(size)})")

        # Generate access logs (CSV, partitioned)
        print("\n5️⃣  Access Logs (CSV, partitioned by date)")
        logs_df = generate_access_logs_data()
        logs_path = OUTPUT_DIR / "access-logs-csv"
        write_csv_partitioned(logs_df, logs_path, "date")
        size = get_dir_size(logs_path)
        print(f"  ✅ Written to {logs_path} ({format_bytes(size)})")

        # Summary
        total_size = get_dir_size(OUTPUT_DIR)
        print("\n" + "=" * 50)
        print(f"✅ Test data generation complete!")
        print(f"📊 Total size: {format_bytes(total_size)}")
        print(f"📁 Location: {OUTPUT_DIR.absolute()}")

        return 0

    except Exception as e:
        print(f"\n❌ Error generating test data: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        # Cleanup on error
        if OUTPUT_DIR.exists():
            import shutil
            print("🧹 Cleaning up partial files...")
            shutil.rmtree(OUTPUT_DIR)

        return 1


if __name__ == "__main__":
    sys.exit(main())
