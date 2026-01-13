"""MCP server implementation for assessment queries."""

import os
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from sqlalchemy.orm import sessionmaker

from aws2openstack.persistence import get_engine, AssessmentRepository
from aws2openstack.mcp_server.tools import (
    get_latest_assessment_impl,
    query_tables_by_readiness_impl,
    get_database_summary_impl,
    search_tables_impl,
    get_tables_by_format_impl,
    compare_assessments_impl,
)


def create_server() -> Server:
    """Create and configure MCP server with assessment query tools.

    Returns:
        Configured MCP server instance
    """
    server = Server("aws2openstack-mcp")

    # Tool definitions
    TOOLS = [
        Tool(
            name="get_latest_assessment",
            description="Get the most recent assessment for a region/account",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS region (e.g., us-east-1)",
                    },
                    "account_id": {
                        "type": "string",
                        "description": "AWS account ID (optional)",
                    },
                },
            },
        ),
        Tool(
            name="query_tables_by_readiness",
            description="Find tables by migration readiness status",
            inputSchema={
                "type": "object",
                "properties": {
                    "assessment_id": {
                        "type": "string",
                        "description": "Assessment UUID",
                    },
                    "readiness": {
                        "type": "string",
                        "description": "Readiness status (ready, needs_conversion, blocked)",
                    },
                },
                "required": ["assessment_id", "readiness"],
            },
        ),
        Tool(
            name="get_database_summary",
            description="Get summary statistics for an assessment",
            inputSchema={
                "type": "object",
                "properties": {
                    "assessment_id": {
                        "type": "string",
                        "description": "Assessment UUID",
                    },
                },
                "required": ["assessment_id"],
            },
        ),
        Tool(
            name="search_tables",
            description="Search for tables by name pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "assessment_id": {
                        "type": "string",
                        "description": "Assessment UUID",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (supports SQL LIKE wildcards)",
                    },
                },
                "required": ["assessment_id", "pattern"],
            },
        ),
        Tool(
            name="get_tables_by_format",
            description="Find tables by table format (parquet, iceberg, orc)",
            inputSchema={
                "type": "object",
                "properties": {
                    "assessment_id": {
                        "type": "string",
                        "description": "Assessment UUID",
                    },
                    "format": {
                        "type": "string",
                        "description": "Table format (parquet, iceberg, orc)",
                    },
                },
                "required": ["assessment_id", "format"],
            },
        ),
        Tool(
            name="compare_assessments",
            description="Compare two assessments to see what changed",
            inputSchema={
                "type": "object",
                "properties": {
                    "assessment_id_1": {
                        "type": "string",
                        "description": "First assessment UUID",
                    },
                    "assessment_id_2": {
                        "type": "string",
                        "description": "Second assessment UUID",
                    },
                },
                "required": ["assessment_id_1", "assessment_id_2"],
            },
        ),
    ]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available assessment query tools."""
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """Execute a tool with given arguments.

        Args:
            name: Tool name to execute
            arguments: Tool arguments

        Returns:
            List of text content responses

        Raises:
            ValueError: If tool not found or DATABASE_URL not set
        """
        # Check DATABASE_URL
        if not os.getenv("DATABASE_URL"):
            raise ValueError(
                "DATABASE_URL environment variable not set. "
                "Required for MCP server database access."
            )

        # Create database session
        engine = get_engine()
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        repository = AssessmentRepository(session)

        try:
            # Route to appropriate tool implementation
            if name == "get_latest_assessment":
                result = get_latest_assessment_impl(repository, arguments)
            elif name == "query_tables_by_readiness":
                result = query_tables_by_readiness_impl(repository, arguments)
            elif name == "get_database_summary":
                result = get_database_summary_impl(repository, arguments)
            elif name == "search_tables":
                result = search_tables_impl(repository, arguments)
            elif name == "get_tables_by_format":
                result = get_tables_by_format_impl(repository, arguments)
            elif name == "compare_assessments":
                result = compare_assessments_impl(repository, arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=result)]

        finally:
            session.close()

    return server


async def main():
    """Run MCP server using stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
