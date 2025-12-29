"""add_last_shutdown_time_to_game_time

Revision ID: 50e9f71cf746
Revises: 8297afe33eae
Create Date: 2025-12-25 11:02:59.421743

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50e9f71cf746"
down_revision: str | Sequence[str] | None = "8297afe33eae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    game_time_columns = (
        [col["name"] for col in inspector.get_columns("game_time")]
        if "game_time" in inspector.get_table_names()
        else []
    )

    # Add last_shutdown_time column to game_time table
    if "last_shutdown_time" not in game_time_columns:
        op.add_column(
            "game_time", sa.Column("last_shutdown_time", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove last_shutdown_time column from game_time table
    op.drop_column("game_time", "last_shutdown_time")
