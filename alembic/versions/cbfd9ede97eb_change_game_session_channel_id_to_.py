"""Change game_session.channel_id to BIGINT for 64-bit Discord channel IDs

Revision ID: cbfd9ede97eb
Revises: 195a5d532906
Create Date: 2025-12-24 13:33:34.723146

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbfd9ede97eb"
down_revision: str | Sequence[str] | None = "195a5d532906"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change channel_id from INTEGER (32-bit) to BigInteger (64-bit) for Discord channel IDs
    op.alter_column(
        "game_sessions",
        "channel_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # NOTE: This downgrade cannot safely convert BIGINT channel_ids back to INTEGER
    # because Discord channel IDs are 64-bit and exceed INTEGER range (32-bit).
    #
    # During a full database reset (downgrade base), this table will be dropped anyway,
    # so we skip the downgrade to avoid errors. If you need to downgrade in production,
    # you would need to manually clear or migrate the channel_id data first.
    #
    # For now, we make this a no-op to allow clean downgrades during resets.
