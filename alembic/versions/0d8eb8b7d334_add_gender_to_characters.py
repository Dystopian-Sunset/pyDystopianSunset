"""add_gender_to_characters

Revision ID: 0d8eb8b7d334
Revises: 626f200cb024
Create Date: 2025-12-25 19:47:57.176071

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d8eb8b7d334"
down_revision: str | Sequence[str] | None = "626f200cb024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    characters_columns = (
        [col["name"] for col in inspector.get_columns("characters")]
        if "characters" in inspector.get_table_names()
        else []
    )

    # Add gender column to characters table
    if "gender" not in characters_columns:
        op.add_column("characters", sa.Column("gender", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove gender column from characters table
    op.drop_column("characters", "gender")
