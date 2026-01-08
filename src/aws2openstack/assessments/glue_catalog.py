"""AWS Glue Catalog assessment."""

import boto3


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
