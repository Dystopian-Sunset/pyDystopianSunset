"""add_year_day_cycle_year_and_calendar_year_cycle

Revision ID: 5be26617ec45
Revises: a26469e6a249
Create Date: 2025-12-24 16:58:54.581169

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5be26617ec45"
down_revision: str | Sequence[str] | None = "a26469e6a249"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns/tables already exist (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check existing columns in game_time
    game_time_columns = (
        [col["name"] for col in inspector.get_columns("game_time")]
        if "game_time" in inspector.get_table_names()
        else []
    )

    # Add year_day and cycle_year columns to game_time table
    # First, rename game_day to year_day for existing data
    if "game_day" in game_time_columns and "year_day" not in game_time_columns:
        op.execute("""
            DO $$
            BEGIN
                ALTER TABLE game_time ADD COLUMN IF NOT EXISTS year_day INTEGER;
                UPDATE game_time SET year_day = game_day WHERE year_day IS NULL;
            END $$;
        """)
    elif "year_day" not in game_time_columns:
        op.add_column("game_time", sa.Column("year_day", sa.Integer(), nullable=True))

    # Add cycle_year column if it doesn't exist
    if "cycle_year" not in game_time_columns:
        op.add_column("game_time", sa.Column("cycle_year", sa.Integer(), nullable=True))

    # Check existing tables
    existing_tables = inspector.get_table_names()

    # Create calendar_year_cycles table
    if "calendar_year_cycles" not in existing_tables:
        op.create_table(
            "calendar_year_cycles",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("cycle_year", sa.Integer(), nullable=False),
            sa.Column("animal_name", sa.String(length=255), nullable=False),
            sa.Column("animal_description", sa.String(), nullable=True),
            sa.Column("traits", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
            sa.Column("cultural_significance", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_calendar_year_cycles_cycle_year"),
            "calendar_year_cycles",
            ["cycle_year"],
            unique=True,
        )

    # Calculate cycle_year for existing game_time records
    op.execute("""
        UPDATE game_time 
        SET cycle_year = ((game_year - 1) % 12) + 1
        WHERE cycle_year IS NULL;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop calendar_year_cycles table
    op.drop_index(op.f("ix_calendar_year_cycles_cycle_year"), table_name="calendar_year_cycles")
    op.drop_table("calendar_year_cycles")

    # Remove cycle_year column
    op.drop_column("game_time", "cycle_year")

    # Note: year_day column is kept for backward compatibility
    # If you want to remove it, uncomment the following:
    # op.drop_column('game_time', 'year_day')
