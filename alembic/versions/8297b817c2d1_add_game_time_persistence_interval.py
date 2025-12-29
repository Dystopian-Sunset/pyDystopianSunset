"""add_game_time_persistence_interval

Revision ID: 8297b817c2d1
Revises: 50e9f71cf746
Create Date: 2025-12-25 11:04:19.275144

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8297b817c2d1"
down_revision: str | Sequence[str] | None = "50e9f71cf746"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    game_settings_columns = (
        [col["name"] for col in inspector.get_columns("game_settings")]
        if "game_settings" in inspector.get_table_names()
        else []
    )

    # Add game_time_persistence_interval_minutes to game_settings table
    if "game_time_persistence_interval_minutes" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "game_time_persistence_interval_minutes",
                sa.Integer(),
                nullable=True,
                server_default="5",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove game_time_persistence_interval_minutes from game_settings table
    op.drop_column("game_settings", "game_time_persistence_interval_minutes")
