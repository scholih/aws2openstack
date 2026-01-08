"""AWS Glue Catalog assessment."""

import boto3

from aws2openstack.models.catalog import GlueDatabase


class GlueCatalogAssessor:
    """Assess AWS Glue Catalog for migration readiness."""

    def __init__(self, region: str, profile: str | None = None) -> None:
        """Initialize the assessor with AWS credentials.

        Args:
            region: AWS region to assess
            profile: Optional AWS profile name (uses default credential chain if None)
        """
        self.region = region

        if profile:
            session = boto3.Session(profile_name=profile)
            self.glue_client = session.client("glue", region_name=region)
            sts_client = session.client("sts", region_name=region)
        else:
            self.glue_client = boto3.client("glue", region_name=region)
            sts_client = boto3.client("sts", region_name=region)

        # Get AWS account ID
        caller_identity = sts_client.get_caller_identity()
        self.aws_account_id = caller_identity["Account"]

    def list_databases(self) -> list[GlueDatabase]:
        """List all databases in the Glue Catalog.

        Returns:
            List of GlueDatabase objects
        """
        databases: list[GlueDatabase] = []
        next_token = None

        while True:
            if next_token:
                response = self.glue_client.get_databases(NextToken=next_token)
            else:
                response = self.glue_client.get_databases()

            for db_dict in response.get("DatabaseList", []):
                database = GlueDatabase(
                    database_name=db_dict["Name"],
                    description=db_dict.get("Description"),
                    location_uri=db_dict.get("LocationUri"),
                    table_count=0,  # Will be updated when we count tables
                )
                databases.append(database)

            next_token = response.get("NextToken")
            if not next_token:
                break

        return databases
