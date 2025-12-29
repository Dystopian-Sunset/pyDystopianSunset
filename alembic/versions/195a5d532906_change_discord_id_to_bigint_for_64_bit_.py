"""Change discord_id to BIGINT for 64-bit Discord IDs

Revision ID: 195a5d532906
Revises: c4bc597cb529
Create Date: 2025-12-24 13:18:47.674752

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "195a5d532906"
down_revision: str | Sequence[str] | None = "be9a604b6be3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change discord_id from INTEGER (32-bit) to BigInteger (64-bit) for Discord IDs
    op.alter_column(
        "players", "discord_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # NOTE: This downgrade cannot safely convert BIGINT discord_ids back to INTEGER
    # because Discord IDs are 64-bit and exceed INTEGER range (32-bit).
    #
    # During a full database reset (downgrade base), this table will be dropped anyway,
    # so we skip the downgrade to avoid errors. If you need to downgrade in production,
    # you would need to manually clear or migrate the discord_id data first.
    #
    # For now, we make this a no-op to allow clean downgrades during resets.
