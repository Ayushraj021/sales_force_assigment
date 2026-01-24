"""Add geo_experiments table

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for geo experiment status
    geo_experiment_status = postgresql.ENUM(
        'draft', 'designing', 'ready', 'running', 'completed', 'analyzed', 'archived',
        name='geoexperimentstatus',
        create_type=False
    )
    geo_experiment_status.create(op.get_bind(), checkfirst=True)

    # Create geo_experiments table
    op.create_table(
        'geo_experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', postgresql.ENUM('draft', 'designing', 'ready', 'running', 'completed', 'analyzed', 'archived', name='geoexperimentstatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('test_regions', postgresql.JSONB, nullable=False),
        sa.Column('control_regions', postgresql.JSONB, nullable=False),
        sa.Column('holdout_regions', postgresql.JSONB),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('warmup_days', sa.Integer, server_default='7'),
        sa.Column('power_analysis', postgresql.JSONB),
        sa.Column('minimum_detectable_effect', sa.Float),
        sa.Column('target_power', sa.Float, server_default='0.8'),
        sa.Column('results', postgresql.JSONB),
        sa.Column('absolute_lift', sa.Float),
        sa.Column('relative_lift', sa.Float),
        sa.Column('p_value', sa.Float),
        sa.Column('confidence_interval_lower', sa.Float),
        sa.Column('confidence_interval_upper', sa.Float),
        sa.Column('primary_metric', sa.String(100)),
        sa.Column('secondary_metrics', postgresql.JSONB),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
    )

    # Create indexes
    op.create_index('ix_geo_experiments_organization_id', 'geo_experiments', ['organization_id'])
    op.create_index('ix_geo_experiments_status', 'geo_experiments', ['status'])
    op.create_index('ix_geo_experiments_created_by_id', 'geo_experiments', ['created_by_id'])


def downgrade() -> None:
    op.drop_index('ix_geo_experiments_created_by_id', table_name='geo_experiments')
    op.drop_index('ix_geo_experiments_status', table_name='geo_experiments')
    op.drop_index('ix_geo_experiments_organization_id', table_name='geo_experiments')
    op.drop_table('geo_experiments')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS geoexperimentstatus')
