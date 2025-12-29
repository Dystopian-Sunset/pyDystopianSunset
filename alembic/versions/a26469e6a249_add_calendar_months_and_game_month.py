"""add_calendar_months_and_game_month

Revision ID: a26469e6a249
Revises: 4ba90b8ff4a4
Create Date: 2025-12-24 16:52:04.555680

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a26469e6a249"
down_revision: str | Sequence[str] | None = "4ba90b8ff4a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns/tables already exist (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if game_month column exists
    game_time_columns = (
        [col["name"] for col in inspector.get_columns("game_time")]
        if "game_time" in inspector.get_table_names()
        else []
    )

    # Add game_month column to game_time table
    if "game_month" not in game_time_columns:
        op.add_column("game_time", sa.Column("game_month", sa.Integer(), nullable=True))

    # Check existing tables
    existing_tables = inspector.get_table_names()

    # Create calendar_months table
    if "calendar_months" not in existing_tables:
        op.create_table(
            "calendar_months",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("month_number", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("short_name", sa.String(length=50), nullable=True),
            sa.Column("days", sa.Integer(), nullable=False, server_default="22"),
            sa.Column("season", sa.String(), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("history", sa.String(), nullable=True),
            sa.Column(
                "cultural_significance", postgresql.JSON(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("regional_variations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_calendar_months_month_number"),
            "calendar_months",
            ["month_number"],
            unique=True,
        )

    # Update game_time_config to include months_per_year and days_per_month
    # Cast JSON to JSONB for jsonb_set function
    op.execute("""
        UPDATE game_time 
        SET game_time_config = jsonb_set(
            jsonb_set(
                game_time_config::jsonb,
                '{months_per_year}',
                '18'::jsonb
            ),
            '{days_per_month}',
            '22'::jsonb
        )::json
        WHERE game_time_config IS NOT NULL;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop calendar_months table
    op.drop_index(op.f("ix_calendar_months_month_number"), table_name="calendar_months")
    op.drop_table("calendar_months")

    # Remove game_month column from game_time table
    op.drop_column("game_time", "game_month")
