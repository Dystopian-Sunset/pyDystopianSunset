"""merge_heads_before_time_fields_removal

Revision ID: a1b2c3d4e5f6
Revises: ['8297b817c2d1', '0d8eb8b7d334', '7647b4d2c70', '2cc4c69b7fe8', 'cbfd9ede97eb']
Create Date: 2025-01-27 00:00:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = [
    "8297b817c2d1",
    "0d8eb8b7d334",
    "7647b4d2c70",
    "2cc4c69b7fe8",
    "cbfd9ede97eb",
]
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge multiple migration heads."""


def downgrade() -> None:
    """Downgrade schema."""
