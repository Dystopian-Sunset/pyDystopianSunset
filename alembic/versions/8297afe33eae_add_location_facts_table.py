"""add_location_facts_table

Revision ID: 8297afe33eae
Revises: 5ba7bb80a028
Create Date: 2025-12-24 17:45:12.754068

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8297afe33eae"
down_revision: str | Sequence[str] | None = "5ba7bb80a028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects import postgresql

    # Check if table already exists (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create location_facts table
    if "location_facts" not in existing_tables:
        op.create_table(
            "location_facts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("location_name", sa.String(length=255), nullable=False),
            sa.Column("location_type", sa.String(), nullable=False),
            sa.Column("facts", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("connections", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "travel_requirements", postgresql.JSON(astext_type=sa.Text()), nullable=False
            ),
            sa.Column(
                "physical_properties", postgresql.JSON(astext_type=sa.Text()), nullable=False
            ),
            sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("constraints", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["region_id"],
                ["world_regions.id"],
            ),
        )
        op.create_index(
            op.f("ix_location_facts_location_name"),
            "location_facts",
            ["location_name"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_location_facts_location_name"), table_name="location_facts")
    op.drop_table("location_facts")
