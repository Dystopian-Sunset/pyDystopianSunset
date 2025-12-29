"""add_items_given_to_character_quests

Revision ID: 626f200cb024
Revises: 50e9f71cf746
Create Date: 2025-12-25 19:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "626f200cb024"
down_revision: str | Sequence[str] | None = "50e9f71cf746"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    character_quests_columns = (
        [col["name"] for col in inspector.get_columns("character_quests")]
        if "character_quests" in inspector.get_table_names()
        else []
    )

    # Add items_given column to character_quests table
    if "items_given" not in character_quests_columns:
        op.add_column(
            "character_quests",
            sa.Column(
                "items_given",
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                server_default="[]",
            ),
        )

    # Add session_id column to track which session gave the items
    if "session_id" not in character_quests_columns:
        op.add_column(
            "character_quests",
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        # Add foreign key constraint
        op.create_foreign_key(
            "fk_character_quests_session_id",
            "character_quests",
            "game_sessions",
            ["session_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraint and session_id column
    op.drop_constraint("fk_character_quests_session_id", "character_quests", type_="foreignkey")
    op.drop_column("character_quests", "session_id")
    # Remove items_given column from character_quests table
    op.drop_column("character_quests", "items_given")
