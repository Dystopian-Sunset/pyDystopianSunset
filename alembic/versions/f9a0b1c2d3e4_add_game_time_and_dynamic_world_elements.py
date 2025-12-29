"""Add game time and dynamic world elements

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2025-12-24 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: str | Sequence[str] | None = "0e7311063b5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns already exist (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Get existing columns for game_settings
    game_settings_columns = (
        [col["name"] for col in inspector.get_columns("game_settings")]
        if "game_settings" in inspector.get_table_names()
        else []
    )

    # Get existing columns for world_memories
    world_memories_columns = (
        [col["name"] for col in inspector.get_columns("world_memories")]
        if "world_memories" in inspector.get_table_names()
        else []
    )

    # Extend game_settings table with game time fields
    if "game_time_enabled" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_time_enabled", sa.Boolean(), nullable=True, server_default="true"),
        )
    if "game_time_multiplier" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_time_multiplier", sa.Float(), nullable=True, server_default="60.0"),
        )
    if "game_hours_per_day" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_hours_per_day", sa.Integer(), nullable=True, server_default="30"),
        )
    if "game_days_per_year" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_days_per_year", sa.Integer(), nullable=True, server_default="400"),
        )
    if "game_day_start_hour" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_day_start_hour", sa.Integer(), nullable=True, server_default="0"),
        )
    if "game_night_start_hour" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_night_start_hour", sa.Integer(), nullable=True, server_default="15"),
        )
    if "game_epoch_start" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("game_epoch_start", sa.DateTime(timezone=True), nullable=True),
        )

    # Extend world_memories table with new fields
    if "related_world_event_id" not in world_memories_columns:
        op.add_column(
            "world_memories",
            sa.Column("related_world_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if "related_world_item_id" not in world_memories_columns:
        op.add_column(
            "world_memories",
            sa.Column("related_world_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if "regional_context" not in world_memories_columns:
        op.add_column(
            "world_memories",
            sa.Column("regional_context", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        )
    if "game_time_context" not in world_memories_columns:
        op.add_column(
            "world_memories",
            sa.Column("game_time_context", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        )

    # Check existing tables
    existing_tables = inspector.get_table_names()

    # Create game_time table (singleton)
    if "game_time" not in existing_tables:
        op.create_table(
            "game_time",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("current_game_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("game_year", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("game_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("game_hour", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("game_minute", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("season", sa.String(), nullable=True, server_default="SPRING"),
            sa.Column("day_of_week", sa.String(), nullable=True, server_default="MONDAY"),
            sa.Column("is_daytime", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("time_multiplier", sa.Float(), nullable=False, server_default="60.0"),
            sa.Column("epoch_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("game_time_config", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # Create world_events table
    if "world_events" not in existing_tables:
        op.create_table(
            "world_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="PLANNED"),
            sa.Column("start_conditions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("end_conditions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("start_game_time", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("end_game_time", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("recurrence_pattern", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("regional_scope", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "related_world_memories",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("impact_level", sa.String(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column(
                "affected_factions",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_world_events_status"), "world_events", ["status"], unique=False)
        op.create_index(
            op.f("ix_world_events_event_type"), "world_events", ["event_type"], unique=False
        )

    # Create calendar_events table
    if "calendar_events" not in existing_tables:
        op.create_table(
            "calendar_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("start_game_time", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("end_game_time", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("recurrence", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("regional_variations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("faction_specific", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "affected_factions",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("seasonal", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "related_world_memories",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default="{}",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_calendar_events_event_type"), "calendar_events", ["event_type"], unique=False
        )
        op.create_index(
            op.f("ix_calendar_events_is_recurring"),
            "calendar_events",
            ["is_recurring"],
            unique=False,
        )

    # Create world_items table
    if "world_items" not in existing_tables:
        op.create_table(
            "world_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("item_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="AVAILABLE"),
            sa.Column(
                "collection_condition", postgresql.JSON(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("collected_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "collected_at_game_time", postgresql.JSON(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("collection_session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "quest_goals",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("location_hint", sa.String(), nullable=True),
            sa.Column(
                "regional_availability", postgresql.JSON(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("faction_origin", sa.String(), nullable=True),
            sa.Column(
                "related_world_memories",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default="{}",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["collected_by"],
                ["characters.id"],
            ),
            sa.ForeignKeyConstraint(
                ["collection_session_id"],
                ["game_sessions.id"],
            ),
        )
        op.create_index(op.f("ix_world_items_status"), "world_items", ["status"], unique=False)
        op.create_index(
            op.f("ix_world_items_item_type"), "world_items", ["item_type"], unique=False
        )

    # Create world_regions table
    if "world_regions" not in existing_tables:
        op.create_table(
            "world_regions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("region_type", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("parent_region_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("hierarchy_level", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("city", sa.String(), nullable=True),
            sa.Column(
                "locations", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
            ),
            sa.Column(
                "factions", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
            ),
            sa.Column("custom_boundaries", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "active_events",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("regional_variations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["parent_region_id"],
                ["world_regions.id"],
            ),
        )
        op.create_index(
            op.f("ix_world_regions_region_type"), "world_regions", ["region_type"], unique=False
        )
        op.create_index(op.f("ix_world_regions_city"), "world_regions", ["city"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop world_regions table
    op.drop_index(op.f("ix_world_regions_city"), table_name="world_regions")
    op.drop_index(op.f("ix_world_regions_region_type"), table_name="world_regions")
    op.drop_table("world_regions")

    # Drop world_items table
    op.drop_index(op.f("ix_world_items_item_type"), table_name="world_items")
    op.drop_index(op.f("ix_world_items_status"), table_name="world_items")
    op.drop_table("world_items")

    # Drop calendar_events table
    op.drop_index(op.f("ix_calendar_events_is_recurring"), table_name="calendar_events")
    op.drop_index(op.f("ix_calendar_events_event_type"), table_name="calendar_events")
    op.drop_table("calendar_events")

    # Drop world_events table
    op.drop_index(op.f("ix_world_events_event_type"), table_name="world_events")
    op.drop_index(op.f("ix_world_events_status"), table_name="world_events")
    op.drop_table("world_events")

    # Drop game_time table
    op.drop_table("game_time")

    # Remove columns from world_memories
    op.drop_column("world_memories", "game_time_context")
    op.drop_column("world_memories", "regional_context")
    op.drop_column("world_memories", "related_world_item_id")
    op.drop_column("world_memories", "related_world_event_id")

    # Remove columns from game_settings
    op.drop_column("game_settings", "game_epoch_start")
    op.drop_column("game_settings", "game_night_start_hour")
    op.drop_column("game_settings", "game_day_start_hour")
    op.drop_column("game_settings", "game_days_per_year")
    op.drop_column("game_settings", "game_hours_per_day")
    op.drop_column("game_settings", "game_time_multiplier")
    op.drop_column("game_settings", "game_time_enabled")
