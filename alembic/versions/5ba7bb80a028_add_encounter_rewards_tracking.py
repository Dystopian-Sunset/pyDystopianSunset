"""add_encounter_rewards_tracking

Revision ID: 5ba7bb80a028
Revises: 5be26617ec45
Create Date: 2025-12-24 17:39:39.006749

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ba7bb80a028"
down_revision: str | Sequence[str] | None = "5be26617ec45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects import postgresql

    # Check if columns already exist (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    encounters_columns = (
        [col["name"] for col in inspector.get_columns("encounters")]
        if "encounters" in inspector.get_table_names()
        else []
    )

    # Add dead_npcs JSON column to encounters table
    if "dead_npcs" not in encounters_columns:
        op.add_column(
            "encounters",
            sa.Column(
                "dead_npcs",
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                server_default="[]",
            ),
        )

    # Add rewards_distributed boolean column to encounters table
    if "rewards_distributed" not in encounters_columns:
        op.add_column(
            "encounters",
            sa.Column("rewards_distributed", sa.Boolean(), nullable=False, server_default="false"),
        )

    # Add searched_npcs JSON column to encounters table
    if "searched_npcs" not in encounters_columns:
        op.add_column(
            "encounters",
            sa.Column(
                "searched_npcs",
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                server_default="[]",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from encounters table
    op.drop_column("encounters", "searched_npcs")
    op.drop_column("encounters", "rewards_distributed")
    op.drop_column("encounters", "dead_npcs")
