"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Enable TimescaleDB extension
    op.execute('CREATE EXTENSION IF NOT EXISTS timescaledb')

    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('subscription_tier', sa.String(50), default='free'),
        sa.Column('max_users', sa.Integer, default=5),
        sa.Column('max_models', sa.Integer, default=10),
        sa.Column('max_datasets', sa.Integer, default=20),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Permissions table
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('resource', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Role-Permission association table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('roles.id'), primary_key=True),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('permissions.id'), primary_key=True),
    )

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # User-Role association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('roles.id'), primary_key=True),
    )

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('rate_limit_requests', sa.Integer, default=1000),
        sa.Column('rate_limit_period', sa.Integer, default=3600),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Data Sources table
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False, index=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('connection_config', postgresql.JSONB, default={}),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Datasets table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('schema_definition', postgresql.JSONB, default={}),
        sa.Column('column_types', postgresql.JSONB, default={}),
        sa.Column('row_count', sa.BigInteger, nullable=True),
        sa.Column('column_count', sa.Integer, nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger, nullable=True),
        sa.Column('start_date', sa.String(50), nullable=True),
        sa.Column('end_date', sa.String(50), nullable=True),
        sa.Column('time_granularity', sa.String(20), nullable=True),
        sa.Column('tags', postgresql.JSONB, default=[]),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('storage_format', sa.String(20), default='parquet'),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('data_sources.id'), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Data Versions table
    op.create_table(
        'data_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_current', sa.Boolean, default=False),
        sa.Column('dvc_hash', sa.String(100), nullable=True),
        sa.Column('dvc_path', sa.String(500), nullable=True),
        sa.Column('changes_summary', postgresql.JSONB, default={}),
        sa.Column('row_count', sa.BigInteger, nullable=True),
        sa.Column('checksum', sa.String(100), nullable=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('datasets.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Channels table
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('channel_type', sa.String(50), nullable=False),
        sa.Column('spend_column', sa.String(100), nullable=True),
        sa.Column('impression_column', sa.String(100), nullable=True),
        sa.Column('click_column', sa.String(100), nullable=True),
        sa.Column('default_adstock_type', sa.String(50), default='geometric'),
        sa.Column('default_saturation_type', sa.String(50), default='hill'),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('datasets.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Metrics table
    op.create_table(
        'metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('column_name', sa.String(100), nullable=False),
        sa.Column('aggregation_method', sa.String(20), default='sum'),
        sa.Column('is_target', sa.Boolean, default=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('datasets.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Models table
    op.create_table(
        'models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('model_type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('hyperparameters', postgresql.JSONB, default={}),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('datasets.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Model Versions table
    op.create_table(
        'model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_current', sa.Boolean, default=False),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('training_duration_seconds', sa.Float, nullable=True),
        sa.Column('trained_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mlflow_run_id', sa.String(100), nullable=True),
        sa.Column('mlflow_model_uri', sa.String(500), nullable=True),
        sa.Column('metrics', postgresql.JSONB, default={}),
        sa.Column('artifact_path', sa.String(500), nullable=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('models.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Model Parameters table
    op.create_table(
        'model_parameters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parameter_name', sa.String(255), nullable=False, index=True),
        sa.Column('parameter_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Float, nullable=True),
        sa.Column('std_error', sa.Float, nullable=True),
        sa.Column('ci_lower', sa.Float, nullable=True),
        sa.Column('ci_upper', sa.Float, nullable=True),
        sa.Column('posterior_mean', sa.Float, nullable=True),
        sa.Column('posterior_std', sa.Float, nullable=True),
        sa.Column('hdi_lower', sa.Float, nullable=True),
        sa.Column('hdi_upper', sa.Float, nullable=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('models.id'), nullable=False, index=True),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('model_versions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Adstock Configs table
    op.create_table(
        'adstock_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_name', sa.String(255), nullable=False, index=True),
        sa.Column('adstock_type', sa.String(50), nullable=False),
        sa.Column('decay_rate', sa.Float, nullable=True),
        sa.Column('shape', sa.Float, nullable=True),
        sa.Column('scale', sa.Float, nullable=True),
        sa.Column('max_lag', sa.Integer, default=8),
        sa.Column('normalize', sa.Boolean, default=True),
        sa.Column('prior_config', postgresql.JSONB, default={}),
        sa.Column('fitted_params', postgresql.JSONB, default={}),
        sa.Column('model_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('models.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Saturation Configs table
    op.create_table(
        'saturation_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_name', sa.String(255), nullable=False, index=True),
        sa.Column('saturation_type', sa.String(50), nullable=False),
        sa.Column('alpha', sa.Float, nullable=True),
        sa.Column('gamma', sa.Float, nullable=True),
        sa.Column('k', sa.Float, nullable=True),
        sa.Column('m', sa.Float, nullable=True),
        sa.Column('vmax', sa.Float, nullable=True),
        sa.Column('km', sa.Float, nullable=True),
        sa.Column('prior_config', postgresql.JSONB, default={}),
        sa.Column('fitted_params', postgresql.JSONB, default={}),
        sa.Column('model_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('models.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Experiments table
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('mlflow_experiment_id', sa.String(100), nullable=True),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('tags', postgresql.JSONB, default=[]),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Experiment Runs table
    op.create_table(
        'experiment_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('mlflow_run_id', sa.String(100), nullable=True),
        sa.Column('parameters', postgresql.JSONB, default={}),
        sa.Column('hyperparameters', postgresql.JSONB, default={}),
        sa.Column('metrics', postgresql.JSONB, default={}),
        sa.Column('artifacts', postgresql.JSONB, default={}),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('experiments.id'), nullable=False, index=True),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('model_versions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Budget Scenarios table
    op.create_table(
        'budget_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('total_budget', sa.Float, nullable=False),
        sa.Column('budget_period', sa.String(20), nullable=False),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('objective', sa.String(50), nullable=False),
        sa.Column('target_value', sa.Float, nullable=True),
        sa.Column('start_date', sa.String(20), nullable=True),
        sa.Column('end_date', sa.String(20), nullable=True),
        sa.Column('periods', sa.Integer, default=1),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('models.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Optimization Constraints table
    op.create_table(
        'optimization_constraints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('constraint_type', sa.String(50), nullable=False),
        sa.Column('channel_name', sa.String(255), nullable=True),
        sa.Column('min_value', sa.Float, nullable=True),
        sa.Column('max_value', sa.Float, nullable=True),
        sa.Column('fixed_value', sa.Float, nullable=True),
        sa.Column('min_ratio', sa.Float, nullable=True),
        sa.Column('max_ratio', sa.Float, nullable=True),
        sa.Column('max_increase_pct', sa.Float, nullable=True),
        sa.Column('max_decrease_pct', sa.Float, nullable=True),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('budget_scenarios.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Optimization Results table
    op.create_table(
        'optimization_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('solver_status', sa.String(50), nullable=True),
        sa.Column('objective_value', sa.Float, nullable=True),
        sa.Column('baseline_value', sa.Float, nullable=True),
        sa.Column('improvement_pct', sa.Float, nullable=True),
        sa.Column('total_spend', sa.Float, nullable=True),
        sa.Column('expected_revenue', sa.Float, nullable=True),
        sa.Column('expected_roi', sa.Float, nullable=True),
        sa.Column('solver_time_seconds', sa.Float, nullable=True),
        sa.Column('iterations', sa.Integer, nullable=True),
        sa.Column('results_json', postgresql.JSONB, default={}),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('budget_scenarios.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Budget Allocations table
    op.create_table(
        'budget_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_name', sa.String(255), nullable=False, index=True),
        sa.Column('period', sa.Integer, default=1),
        sa.Column('allocated_budget', sa.Float, nullable=False),
        sa.Column('baseline_budget', sa.Float, nullable=True),
        sa.Column('change_pct', sa.Float, nullable=True),
        sa.Column('expected_contribution', sa.Float, nullable=True),
        sa.Column('expected_roi', sa.Float, nullable=True),
        sa.Column('marginal_roi', sa.Float, nullable=True),
        sa.Column('saturation_level', sa.Float, nullable=True),
        sa.Column('optimization_result_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('optimization_results.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Dashboards table
    op.create_table(
        'dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('layout', postgresql.JSONB, default={}),
        sa.Column('theme', sa.String(50), default='light'),
        sa.Column('default_filters', postgresql.JSONB, default={}),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Widgets table
    op.create_table(
        'widgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('widget_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('position_x', sa.Integer, default=0),
        sa.Column('position_y', sa.Integer, default=0),
        sa.Column('width', sa.Integer, default=4),
        sa.Column('height', sa.Integer, default=3),
        sa.Column('data_source', sa.String(100), nullable=True),
        sa.Column('data_config', postgresql.JSONB, default={}),
        sa.Column('chart_config', postgresql.JSONB, default={}),
        sa.Column('auto_refresh', sa.Boolean, default=False),
        sa.Column('refresh_interval_seconds', sa.Integer, default=300),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('dashboards.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('template', postgresql.JSONB, default={}),
        sa.Column('sections', postgresql.JSONB, default=[]),
        sa.Column('available_formats', postgresql.JSONB, default=['pdf', 'excel', 'pptx']),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Scheduled Reports table
    op.create_table(
        'scheduled_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('schedule_type', sa.String(20), nullable=False),
        sa.Column('schedule_config', postgresql.JSONB, default={}),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('delivery_method', sa.String(20), nullable=False),
        sa.Column('delivery_config', postgresql.JSONB, default={}),
        sa.Column('recipients', postgresql.JSONB, default=[]),
        sa.Column('export_format', sa.String(20), default='pdf'),
        sa.Column('last_run_at', sa.String(50), nullable=True),
        sa.Column('last_run_status', sa.String(20), nullable=True),
        sa.Column('next_run_at', sa.String(50), nullable=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('reports.id'), nullable=False, index=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Exports table
    op.create_table(
        'exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('export_type', sa.String(50), nullable=False),
        sa.Column('export_format', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger, nullable=True),
        sa.Column('download_url', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Audit Logs table (will be a hypertable - requires composite primary key)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id'), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(100), nullable=False, index=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('details', postgresql.JSONB, default={}),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), default='success'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.PrimaryKeyConstraint('id', 'timestamp'),
    )

    # Convert audit_logs to TimescaleDB hypertable (optional - skip if TimescaleDB not installed)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                PERFORM create_hypertable('audit_logs', 'timestamp', if_not_exists => TRUE);
            END IF;
        END $$;
    """)

    # Insert default roles
    op.execute("""
        INSERT INTO roles (id, name, description, is_default)
        VALUES
            (uuid_generate_v4(), 'admin', 'Administrator with full access', false),
            (uuid_generate_v4(), 'analyst', 'Data analyst with read/write access to models', false),
            (uuid_generate_v4(), 'viewer', 'Read-only access to dashboards and reports', true)
    """)

    # Insert default permissions
    op.execute("""
        INSERT INTO permissions (id, name, description, resource, action)
        VALUES
            (uuid_generate_v4(), 'model:create', 'Create new models', 'model', 'create'),
            (uuid_generate_v4(), 'model:read', 'View models', 'model', 'read'),
            (uuid_generate_v4(), 'model:update', 'Update models', 'model', 'update'),
            (uuid_generate_v4(), 'model:delete', 'Delete models', 'model', 'delete'),
            (uuid_generate_v4(), 'model:train', 'Train models', 'model', 'train'),
            (uuid_generate_v4(), 'dataset:create', 'Create datasets', 'dataset', 'create'),
            (uuid_generate_v4(), 'dataset:read', 'View datasets', 'dataset', 'read'),
            (uuid_generate_v4(), 'dataset:update', 'Update datasets', 'dataset', 'update'),
            (uuid_generate_v4(), 'dataset:delete', 'Delete datasets', 'dataset', 'delete'),
            (uuid_generate_v4(), 'dashboard:create', 'Create dashboards', 'dashboard', 'create'),
            (uuid_generate_v4(), 'dashboard:read', 'View dashboards', 'dashboard', 'read'),
            (uuid_generate_v4(), 'dashboard:update', 'Update dashboards', 'dashboard', 'update'),
            (uuid_generate_v4(), 'dashboard:delete', 'Delete dashboards', 'dashboard', 'delete'),
            (uuid_generate_v4(), 'optimization:run', 'Run optimizations', 'optimization', 'run'),
            (uuid_generate_v4(), 'report:export', 'Export reports', 'report', 'export'),
            (uuid_generate_v4(), 'user:manage', 'Manage users', 'user', 'manage')
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('exports')
    op.drop_table('scheduled_reports')
    op.drop_table('reports')
    op.drop_table('widgets')
    op.drop_table('dashboards')
    op.drop_table('budget_allocations')
    op.drop_table('optimization_results')
    op.drop_table('optimization_constraints')
    op.drop_table('budget_scenarios')
    op.drop_table('experiment_runs')
    op.drop_table('experiments')
    op.drop_table('saturation_configs')
    op.drop_table('adstock_configs')
    op.drop_table('model_parameters')
    op.drop_table('model_versions')
    op.drop_table('models')
    op.drop_table('metrics')
    op.drop_table('channels')
    op.drop_table('data_versions')
    op.drop_table('datasets')
    op.drop_table('data_sources')
    op.drop_table('api_keys')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('organizations')
