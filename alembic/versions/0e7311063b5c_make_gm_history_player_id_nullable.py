"""make_gm_history_player_id_nullable

Revision ID: 0e7311063b5c
Revises: e8f9a0b1c2d3
Create Date: 2025-12-24 16:09:05.335244

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0e7311063b5c"
down_revision: str | Sequence[str] | None = "e8f9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make player_id nullable in gm_history table
    op.alter_column("gm_history", "player_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Delete rows with NULL player_id before making it non-nullable
    # This is necessary because the column was made nullable in upgrade()
    op.execute("DELETE FROM gm_history WHERE player_id IS NULL")

    # Make player_id non-nullable again
    op.alter_column("gm_history", "player_id", existing_type=sa.Uuid(), nullable=False)
