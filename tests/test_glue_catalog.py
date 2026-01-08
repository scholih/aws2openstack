"""Tests for Glue Catalog assessment."""

from unittest.mock import MagicMock, patch

import pytest

from aws2openstack.assessments.glue_catalog import GlueCatalogAssessor


@patch("boto3.client")
def test_assessor_init_default_credentials(mock_boto_client):
    """Test assessor initializes with default credentials."""
    mock_glue = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

    def client_factory(service, region_name=None):
        if service == "glue":
            return mock_glue
        elif service == "sts":
            return mock_sts
        raise ValueError(f"Unexpected service: {service}")

    mock_boto_client.side_effect = client_factory

    assessor = GlueCatalogAssessor(region="us-east-1")

    assert assessor.region == "us-east-1"
    assert assessor.aws_account_id == "123456789012"
    mock_boto_client.assert_any_call("glue", region_name="us-east-1")
    mock_boto_client.assert_any_call("sts", region_name="us-east-1")


@patch("boto3.Session")
def test_assessor_init_with_profile(mock_session):
    """Test assessor initializes with specific profile."""
    mock_glue = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "987654321098"}

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance

    def client_factory(service, region_name=None):
        if service == "glue":
            return mock_glue
        elif service == "sts":
            return mock_sts
        raise ValueError(f"Unexpected service: {service}")

    mock_session_instance.client.side_effect = client_factory

    assessor = GlueCatalogAssessor(region="eu-west-1", profile="my-profile")

    assert assessor.region == "eu-west-1"
    assert assessor.aws_account_id == "987654321098"
    mock_session.assert_called_once_with(profile_name="my-profile")
