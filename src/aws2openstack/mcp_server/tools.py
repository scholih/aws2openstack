"""Tool implementations for MCP server."""

import json
from typing import Any, Dict
from uuid import UUID

from aws2openstack.persistence.repository import AssessmentRepository


def get_latest_assessment_impl(
    repository: AssessmentRepository, arguments: Dict[str, Any]
) -> str:
    """Get the most recent assessment for a region/account.

    Args:
        repository: Assessment repository instance
        arguments: Tool arguments with optional region and account_id

    Returns:
        JSON string with assessment details
    """
    region = arguments.get("region")
    account_id = arguments.get("account_id")

    assessment = repository.get_latest_assessment(region=region, account_id=account_id)

    if not assessment:
        return json.dumps(
            {
                "success": False,
                "error": f"No assessment found for region={region}, account_id={account_id}",
            }
        )

    # Get database summary for this assessment
    summary = repository.get_database_summary(assessment.id)

    return json.dumps(
        {
            "success": True,
            "assessment": {
                "id": str(assessment.id),
                "timestamp": assessment.timestamp.isoformat(),
                "region": assessment.region,
                "account_id": assessment.aws_account_id,
                "tool_version": assessment.tool_version,
                "services": assessment.services,
                "status": assessment.status,
                "summary": summary,
            },
        },
        indent=2,
    )


def query_tables_by_readiness_impl(
    repository: AssessmentRepository, arguments: Dict[str, Any]
) -> str:
    """Find tables by migration readiness status.

    Args:
        repository: Assessment repository instance
        arguments: Tool arguments with assessment_id and readiness

    Returns:
        JSON string with matching tables
    """
    try:
        assessment_id = UUID(arguments["assessment_id"])
        readiness = arguments["readiness"]
    except (KeyError, ValueError) as e:
        return json.dumps({"success": False, "error": str(e)})

    tables = repository.query_tables_by_readiness(assessment_id, readiness)

    return json.dumps(
        {
            "success": True,
            "count": len(tables),
            "readiness": readiness,
            "tables": [
                {
                    "id": str(table.id),
                    "database_name": table.database.database_name,
                    "table_name": table.table_name,
                    "format": table.table_format,
                    "location": table.storage_location,
                    "size_gb": float(table.estimated_size_gb) if table.estimated_size_gb else None,
                    "partition_keys": table.partition_keys,
                    "is_iceberg": table.is_iceberg,
                    "readiness": table.migration_readiness,
                    "notes": table.notes,
                }
                for table in tables
            ],
        },
        indent=2,
    )


def get_database_summary_impl(
    repository: AssessmentRepository, arguments: Dict[str, Any]
) -> str:
    """Get summary statistics for an assessment.

    Args:
        repository: Assessment repository instance
        arguments: Tool arguments with assessment_id

    Returns:
        JSON string with summary statistics
    """
    try:
        assessment_id = UUID(arguments["assessment_id"])
    except (KeyError, ValueError) as e:
        return json.dumps({"success": False, "error": str(e)})

    # Check if assessment exists
    assessment = repository.get_assessment(assessment_id)
    if not assessment:
        return json.dumps(
            {"success": False, "error": f"Assessment {assessment_id} not found"}
        )

    summary = repository.get_database_summary(assessment_id)

    return json.dumps(
        {
            "success": True,
            "assessment_id": str(assessment_id),
            "region": assessment.region,
            "account_id": assessment.aws_account_id,
            "timestamp": assessment.timestamp.isoformat(),
            "summary": summary,
        },
        indent=2,
    )


def search_tables_impl(
    repository: AssessmentRepository, arguments: Dict[str, Any]
) -> str:
    """Search for tables by name pattern.

    Args:
        repository: Assessment repository instance
        arguments: Tool arguments with assessment_id and pattern

    Returns:
        JSON string with matching tables
    """
    try:
        assessment_id = UUID(arguments["assessment_id"])
        pattern = arguments["pattern"]
    except (KeyError, ValueError) as e:
        return json.dumps({"success": False, "error": str(e)})

    # Get all tables for assessment and filter by pattern
    # Use SQL LIKE pattern matching
    from sqlalchemy import or_
    from aws2openstack.persistence.models import GlueTable

    session = repository.session
    tables = (
        session.query(GlueTable)
        .filter(
            GlueTable.assessment_id == assessment_id,
            or_(
                GlueTable.table_name.like(pattern),
                GlueTable.database.has(database_name=pattern),
            ),
        )
        .all()
    )

    return json.dumps(
        {
            "success": True,
            "count": len(tables),
            "pattern": pattern,
            "tables": [
                {
                    "id": str(table.id),
                    "database_name": table.database.database_name,
                    "table_name": table.table_name,
                    "format": table.table_format,
                    "location": table.storage_location,
                    "size_gb": float(table.estimated_size_gb) if table.estimated_size_gb else None,
                    "readiness": table.migration_readiness,
                    "is_iceberg": table.is_iceberg,
                }
                for table in tables
            ],
        },
        indent=2,
    )


def get_tables_by_format_impl(
    repository: AssessmentRepository, arguments: Dict[str, Any]
) -> str:
    """Find tables by table format.

    Args:
        repository: Assessment repository instance
        arguments: Tool arguments with assessment_id and format

    Returns:
        JSON string with matching tables
    """
    try:
        assessment_id = UUID(arguments["assessment_id"])
        table_format = arguments["format"]
    except (KeyError, ValueError) as e:
        return json.dumps({"success": False, "error": str(e)})

    tables = repository.query_tables_by_format(assessment_id, table_format)

    # Calculate total size
    total_size_gb = sum(
        float(t.estimated_size_gb) if t.estimated_size_gb else 0 for t in tables
    )

    return json.dumps(
        {
            "success": True,
            "count": len(tables),
            "format": table_format,
            "total_size_gb": total_size_gb,
            "tables": [
                {
                    "id": str(table.id),
                    "database_name": table.database.database_name,
                    "table_name": table.table_name,
                    "location": table.storage_location,
                    "size_gb": float(table.estimated_size_gb) if table.estimated_size_gb else None,
                    "partition_keys": table.partition_keys,
                    "column_count": table.column_count,
                    "readiness": table.migration_readiness,
                    "is_iceberg": table.is_iceberg,
                }
                for table in tables
            ],
        },
        indent=2,
    )


def compare_assessments_impl(
    repository: AssessmentRepository, arguments: Dict[str, Any]
) -> str:
    """Compare two assessments to see what changed.

    Args:
        repository: Assessment repository instance
        arguments: Tool arguments with assessment_id_1 and assessment_id_2

    Returns:
        JSON string with comparison results
    """
    try:
        assessment_id_1 = UUID(arguments["assessment_id_1"])
        assessment_id_2 = UUID(arguments["assessment_id_2"])
    except (KeyError, ValueError) as e:
        return json.dumps({"success": False, "error": str(e)})

    # Get both assessments
    assessment1 = repository.get_assessment(assessment_id_1)
    assessment2 = repository.get_assessment(assessment_id_2)

    if not assessment1 or not assessment2:
        return json.dumps(
            {"success": False, "error": "One or both assessments not found"}
        )

    # Get summaries
    summary1 = repository.get_database_summary(assessment_id_1)
    summary2 = repository.get_database_summary(assessment_id_2)

    # Get databases for each
    databases1 = repository.get_glue_databases(assessment_id_1, include_tables=True)
    databases2 = repository.get_glue_databases(assessment_id_2, include_tables=True)

    # Compare databases
    db_names1 = {db.database_name for db in databases1}
    db_names2 = {db.database_name for db in databases2}

    added_databases = db_names2 - db_names1
    removed_databases = db_names1 - db_names2
    common_databases = db_names1 & db_names2

    # Compare tables in common databases
    tables_added = []
    tables_removed = []
    tables_modified = []

    for db_name in common_databases:
        db1 = next(db for db in databases1 if db.database_name == db_name)
        db2 = next(db for db in databases2 if db.database_name == db_name)

        table_names1 = {t.table_name for t in db1.tables}
        table_names2 = {t.table_name for t in db2.tables}

        for added_table in table_names2 - table_names1:
            tables_added.append(f"{db_name}.{added_table}")

        for removed_table in table_names1 - table_names2:
            tables_removed.append(f"{db_name}.{removed_table}")

        # Check for modified tables (same name, different attributes)
        for table_name in table_names1 & table_names2:
            t1 = next(t for t in db1.tables if t.table_name == table_name)
            t2 = next(t for t in db2.tables if t.table_name == table_name)

            if (
                t1.table_format != t2.table_format
                or t1.migration_readiness != t2.migration_readiness
            ):
                tables_modified.append(
                    {
                        "name": f"{db_name}.{table_name}",
                        "format_changed": t1.table_format != t2.table_format,
                        "old_format": t1.table_format,
                        "new_format": t2.table_format,
                        "readiness_changed": t1.migration_readiness
                        != t2.migration_readiness,
                        "old_readiness": t1.migration_readiness,
                        "new_readiness": t2.migration_readiness,
                    }
                )

    return json.dumps(
        {
            "success": True,
            "assessment_1": {
                "id": str(assessment_id_1),
                "timestamp": assessment1.timestamp.isoformat(),
                "region": assessment1.region,
                "summary": summary1,
            },
            "assessment_2": {
                "id": str(assessment_id_2),
                "timestamp": assessment2.timestamp.isoformat(),
                "region": assessment2.region,
                "summary": summary2,
            },
            "changes": {
                "databases_added": list(added_databases),
                "databases_removed": list(removed_databases),
                "tables_added": tables_added,
                "tables_removed": tables_removed,
                "tables_modified": tables_modified,
            },
            "summary_changes": {
                "database_count": summary2["database_count"] - summary1["database_count"],
                "table_count": summary2["table_count"] - summary1["table_count"],
                "total_size_gb": summary2["total_estimated_size_gb"]
                - summary1["total_estimated_size_gb"],
            },
        },
        indent=2,
    )
