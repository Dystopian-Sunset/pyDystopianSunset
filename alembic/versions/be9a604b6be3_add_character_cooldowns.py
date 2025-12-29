"""add character cooldowns

Revision ID: be9a604b6be3
Revises: 20e59196ebcb
Create Date: 2025-12-25 13:20:33.345104

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be9a604b6be3"
down_revision: str | Sequence[str] | None = "20e59196ebcb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create character_cooldowns table
    op.create_table(
        "character_cooldowns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("cooldown_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cooldown_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("expires_at_game_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_game_hours", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
        ),
    )
    op.create_index(
        op.f("ix_character_cooldowns_cooldown_name"),
        "character_cooldowns",
        ["cooldown_name"],
        unique=False,
    )
    # Add index on character_id and expires_at for efficient queries
    op.create_index(
        "ix_character_cooldowns_character_expires",
        "character_cooldowns",
        ["character_id", "expires_at_game_time"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_character_cooldowns_character_expires", table_name="character_cooldowns")
    op.drop_index(op.f("ix_character_cooldowns_cooldown_name"), table_name="character_cooldowns")
    op.drop_table("character_cooldowns")
