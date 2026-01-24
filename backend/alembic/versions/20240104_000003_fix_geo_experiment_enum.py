"""Fix geo_experiment_status enum to use uppercase values

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:03

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop and recreate the enum with uppercase values to match SQLAlchemy enum names
    # First drop the default
    op.execute("ALTER TABLE geo_experiments ALTER COLUMN status DROP DEFAULT")

    # Alter the column to use varchar temporarily
    op.execute("ALTER TABLE geo_experiments ALTER COLUMN status TYPE VARCHAR(50)")

    # Drop the old enum
    op.execute("DROP TYPE IF EXISTS geoexperimentstatus")

    # Create new enum with uppercase values (matching Python enum names)
    op.execute("""
        CREATE TYPE geoexperimentstatus AS ENUM (
            'DRAFT', 'DESIGNING', 'READY', 'RUNNING', 'COMPLETED', 'ANALYZED', 'ARCHIVED'
        )
    """)

    # Convert any existing lowercase values to uppercase
    op.execute("UPDATE geo_experiments SET status = UPPER(status)")

    # Alter column back to use the enum
    op.execute("""
        ALTER TABLE geo_experiments
        ALTER COLUMN status TYPE geoexperimentstatus
        USING status::geoexperimentstatus
    """)

    # Set default
    op.execute("ALTER TABLE geo_experiments ALTER COLUMN status SET DEFAULT 'DRAFT'")


def downgrade() -> None:
    # Revert to lowercase enum values
    op.execute("ALTER TABLE geo_experiments ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS geoexperimentstatus")
    op.execute("""
        CREATE TYPE geoexperimentstatus AS ENUM (
            'draft', 'designing', 'ready', 'running', 'completed', 'analyzed', 'archived'
        )
    """)
    op.execute("UPDATE geo_experiments SET status = LOWER(status)")
    op.execute("""
        ALTER TABLE geo_experiments
        ALTER COLUMN status TYPE geoexperimentstatus
        USING status::geoexperimentstatus
    """)
    op.execute("ALTER TABLE geo_experiments ALTER COLUMN status SET DEFAULT 'draft'")
