"""initial schema

Revision ID: 24d8e3b192ac
Revises: 
Create Date: 2026-01-13 06:52:00.473598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24d8e3b192ac'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Core assessments table
    op.create_table(
        'assessments',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('aws_account_id', sa.String(12), nullable=False),
        sa.Column('tool_version', sa.String(20), nullable=False),
        sa.Column('services', sa.ARRAY(sa.Text()), nullable=False),
        sa.Column('status', sa.String(20), server_default='completed', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_assessments_timestamp', 'assessments', ['timestamp'], unique=False, postgresql_using='btree')
    op.create_index('idx_assessments_account_region', 'assessments', ['aws_account_id', 'region'], unique=False)

    # Mapping templates (rule-based transformation logic)
    op.create_table(
        'mapping_templates',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('source_service', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('rules', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_mapping_templates_service', 'mapping_templates', ['source_service', 'source_type'], unique=False)

    # Transformation results
    op.create_table(
        'transformation_results',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('terraform_output_path', sa.Text(), nullable=False),
        sa.Column('target_catalog_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['mapping_templates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_transformation_results_assessment', 'transformation_results', ['assessment_id'], unique=False)

    # Migration jobs tracking
    op.create_table(
        'migration_jobs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.UUID(), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('aws_job_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('bytes_copied', sa.BigInteger(), nullable=True),
        sa.Column('rows_copied', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('sync_mode', sa.String(20), nullable=True),
        sa.Column('last_sync_timestamp', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('validation_status', sa.String(20), nullable=True),
        sa.Column('last_validated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('validation_details', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_migration_jobs_assessment', 'migration_jobs', ['assessment_id'], unique=False)
    op.create_index('idx_migration_jobs_status', 'migration_jobs', ['status'], unique=False)
    op.create_index('idx_migration_jobs_resource', 'migration_jobs', ['resource_type', 'resource_id'], unique=False)

    # Validation results
    op.create_table(
        'validation_results',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('migration_job_id', sa.UUID(), nullable=False),
        sa.Column('validation_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('source_value', sa.Text(), nullable=True),
        sa.Column('target_value', sa.Text(), nullable=True),
        sa.Column('difference', sa.Text(), nullable=True),
        sa.Column('validated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['migration_job_id'], ['migration_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_validation_results_job', 'validation_results', ['migration_job_id'], unique=False)
    op.create_index('idx_validation_results_status', 'validation_results', ['status'], unique=False)

    # Glue-specific tables (service extensions)
    op.create_table(
        'glue_databases',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('database_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location_uri', sa.Text(), nullable=True),
        sa.Column('table_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_glue_databases_assessment', 'glue_databases', ['assessment_id'], unique=False)
    op.create_index('idx_glue_databases_name', 'glue_databases', ['database_name'], unique=False)

    op.create_table(
        'glue_tables',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('database_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('table_name', sa.String(255), nullable=False),
        sa.Column('table_format', sa.String(50), nullable=False),
        sa.Column('storage_location', sa.Text(), nullable=False),
        sa.Column('estimated_size_gb', sa.Numeric(12, 2), nullable=True),
        sa.Column('partition_keys', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('column_count', sa.Integer(), nullable=False),
        sa.Column('last_updated', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_iceberg', sa.Boolean(), nullable=False),
        sa.Column('migration_readiness', sa.String(20), nullable=False),
        sa.Column('notes', sa.ARRAY(sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['database_id'], ['glue_databases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_glue_tables_database', 'glue_tables', ['database_id'], unique=False)
    op.create_index('idx_glue_tables_assessment', 'glue_tables', ['assessment_id'], unique=False)
    op.create_index('idx_glue_tables_readiness', 'glue_tables', ['migration_readiness'], unique=False)
    op.create_index('idx_glue_tables_format', 'glue_tables', ['table_format'], unique=False)
    op.create_index('idx_glue_tables_name', 'glue_tables', ['table_name'], unique=False)

    # IAM roles (infrastructure context)
    op.create_table(
        'iam_roles',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('role_name', sa.String(255), nullable=False),
        sa.Column('role_arn', sa.Text(), nullable=False),
        sa.Column('policy_document', sa.JSON(), nullable=True),
        sa.Column('used_by_services', sa.ARRAY(sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_iam_roles_assessment', 'iam_roles', ['assessment_id'], unique=False)

    # VPC resources (infrastructure context)
    op.create_table(
        'vpc_resources',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('vpc_id', sa.String(50), nullable=False),
        sa.Column('subnet_ids', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('security_group_ids', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vpc_resources_assessment', 'vpc_resources', ['assessment_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_vpc_resources_assessment', table_name='vpc_resources')
    op.drop_table('vpc_resources')
    
    op.drop_index('idx_iam_roles_assessment', table_name='iam_roles')
    op.drop_table('iam_roles')
    
    op.drop_index('idx_glue_tables_name', table_name='glue_tables')
    op.drop_index('idx_glue_tables_format', table_name='glue_tables')
    op.drop_index('idx_glue_tables_readiness', table_name='glue_tables')
    op.drop_index('idx_glue_tables_assessment', table_name='glue_tables')
    op.drop_index('idx_glue_tables_database', table_name='glue_tables')
    op.drop_table('glue_tables')
    
    op.drop_index('idx_glue_databases_name', table_name='glue_databases')
    op.drop_index('idx_glue_databases_assessment', table_name='glue_databases')
    op.drop_table('glue_databases')
    
    op.drop_index('idx_validation_results_status', table_name='validation_results')
    op.drop_index('idx_validation_results_job', table_name='validation_results')
    op.drop_table('validation_results')
    
    op.drop_index('idx_migration_jobs_resource', table_name='migration_jobs')
    op.drop_index('idx_migration_jobs_status', table_name='migration_jobs')
    op.drop_index('idx_migration_jobs_assessment', table_name='migration_jobs')
    op.drop_table('migration_jobs')
    
    op.drop_index('idx_transformation_results_assessment', table_name='transformation_results')
    op.drop_table('transformation_results')
    
    op.drop_index('idx_mapping_templates_service', table_name='mapping_templates')
    op.drop_table('mapping_templates')
    
    op.drop_index('idx_assessments_account_region', table_name='assessments')
    op.drop_index('idx_assessments_timestamp', table_name='assessments')
    op.drop_table('assessments')
