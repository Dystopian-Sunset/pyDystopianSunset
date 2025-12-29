"""fix_datetime_timezone_columns

Revision ID: 4ba90b8ff4a4
Revises: f9a0b1c2d3e4
Create Date: 2025-12-24 16:48:06.396599

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ba90b8ff4a4"
down_revision: str | Sequence[str] | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix game_time table datetime columns to be timezone-aware
    # If columns are TIMESTAMP WITHOUT TIME ZONE, convert them assuming UTC
    # If they're already TIMESTAMP WITH TIME ZONE, this will be a no-op
    op.execute("""
        DO $$
        BEGIN
            -- Check if current_game_time needs conversion
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'game_time' 
                AND column_name = 'current_game_time'
                AND data_type = 'timestamp without time zone'
            ) THEN
                ALTER TABLE game_time 
                ALTER COLUMN current_game_time TYPE TIMESTAMP WITH TIME ZONE 
                USING current_game_time AT TIME ZONE 'UTC';
            END IF;
            
            -- Check if epoch_start needs conversion
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'game_time' 
                AND column_name = 'epoch_start'
                AND data_type = 'timestamp without time zone'
            ) THEN
                ALTER TABLE game_time 
                ALTER COLUMN epoch_start TYPE TIMESTAMP WITH TIME ZONE 
                USING epoch_start AT TIME ZONE 'UTC';
            END IF;
        END $$;
    """)

    # Fix game_settings game_epoch_start if it exists and needs fixing
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'game_settings' 
                AND column_name = 'game_epoch_start'
                AND data_type = 'timestamp without time zone'
            ) THEN
                ALTER TABLE game_settings 
                ALTER COLUMN game_epoch_start TYPE TIMESTAMP WITH TIME ZONE 
                USING game_epoch_start AT TIME ZONE 'UTC';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to TIMESTAMP WITHOUT TIME ZONE (not recommended, but provided for completeness)
    op.execute("""
        ALTER TABLE game_time 
        ALTER COLUMN current_game_time TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
    op.execute("""
        ALTER TABLE game_time 
        ALTER COLUMN epoch_start TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
    op.execute("""
        ALTER TABLE game_settings 
        ALTER COLUMN game_epoch_start TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
