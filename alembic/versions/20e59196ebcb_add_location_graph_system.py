"""add location graph system

Revision ID: 20e59196ebcb
Revises: 7ced9fef83a3
Create Date: 2025-12-25 12:10:53.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20e59196ebcb"
down_revision: str | Sequence[str] | None = "7ced9fef83a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create location_nodes table (without self-referential FK first)
    op.create_table(
        "location_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("location_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("atmosphere", sa.JSON(), nullable=True),
        sa.Column("physical_properties", sa.JSON(), nullable=True),
        sa.Column("theme", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("character_associations", sa.JSON(), nullable=True),
        sa.Column("location_fact_id", sa.Uuid(), nullable=True),
        sa.Column("parent_location_id", sa.Uuid(), nullable=True),
        sa.Column("discovered_by", sa.Uuid(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_in_session", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["location_fact_id"],
            ["location_facts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["discovered_by"],
            ["characters.id"],
        ),
        sa.ForeignKeyConstraint(
            ["discovered_in_session"],
            ["game_sessions.id"],
        ),
    )
    # Now add self-referential foreign key after table exists
    op.create_foreign_key(
        "fk_location_nodes_parent_location",
        "location_nodes",
        "location_nodes",
        ["parent_location_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_location_nodes_location_name"), "location_nodes", ["location_name"], unique=True
    )

    # Create location_edges table
    op.create_table(
        "location_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_location_id", sa.Uuid(), nullable=False),
        sa.Column("to_location_id", sa.Uuid(), nullable=False),
        sa.Column("edge_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("travel_method", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("travel_time", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("narrative_description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("discovered_by", sa.Uuid(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_in_session", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["from_location_id"],
            ["location_nodes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["to_location_id"],
            ["location_nodes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["discovered_by"],
            ["characters.id"],
        ),
        sa.ForeignKeyConstraint(
            ["discovered_in_session"],
            ["game_sessions.id"],
        ),
        sa.UniqueConstraint(
            "from_location_id", "to_location_id", "edge_type", name="uq_location_edge"
        ),
    )

    # Add current_location field to characters table
    op.add_column("characters", sa.Column("current_location", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_characters_current_location",
        "characters",
        "location_nodes",
        ["current_location"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove current_location field from characters table
    op.drop_constraint("fk_characters_current_location", "characters", type_="foreignkey")
    op.drop_column("characters", "current_location")

    # Drop location_edges table
    op.drop_table("location_edges")

    # Drop location_nodes table (drop self-referential FK first)
    op.drop_constraint("fk_location_nodes_parent_location", "location_nodes", type_="foreignkey")
    op.drop_index(op.f("ix_location_nodes_location_name"), table_name="location_nodes")
    op.drop_table("location_nodes")
