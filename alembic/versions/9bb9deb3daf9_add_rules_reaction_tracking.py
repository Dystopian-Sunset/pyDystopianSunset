"""add rules reaction tracking

Revision ID: 9bb9deb3daf9
Revises: b2c3d4e5f6a7
Create Date: 2025-12-25 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9bb9deb3daf9"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create player_rules_reactions table with message_id directly (configured via TOML)
    op.create_table(
        "player_rules_reactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("reacted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
        ),
    )
    op.create_index(
        op.f("ix_player_rules_reactions_player_id"),
        "player_rules_reactions",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_rules_reactions_message_id"),
        "player_rules_reactions",
        ["message_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_player_rules_reaction", "player_rules_reactions", ["player_id", "message_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_player_rules_reaction", "player_rules_reactions", type_="unique")
    op.drop_index(op.f("ix_player_rules_reactions_message_id"), table_name="player_rules_reactions")
    op.drop_index(op.f("ix_player_rules_reactions_player_id"), table_name="player_rules_reactions")
    op.drop_table("player_rules_reactions")
