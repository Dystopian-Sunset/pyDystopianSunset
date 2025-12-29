"""Add memory system tables

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2025-12-24 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: str | Sequence[str] | None = "7ced9fef83a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if tables already exist (for idempotency with multiple heads)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create session_memories table
    if "session_memories" not in existing_tables:
        op.create_table(
            "session_memories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("memory_type", sa.String(), nullable=True),
            sa.Column("content", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "participants", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True
            ),
            sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("importance_score", sa.Float(), nullable=True),
            sa.Column("emotional_valence", sa.Float(), nullable=True),
            sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["game_sessions.id"],
            ),
            sa.ForeignKeyConstraint(
                ["character_id"],
                ["characters.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_session_memories_session_id"), "session_memories", ["session_id"], unique=False
        )
        op.create_index(
            op.f("ix_session_memories_character_id"),
            "session_memories",
            ["character_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_session_memories_processed"), "session_memories", ["processed"], unique=False
        )
        op.create_index(
            op.f("ix_session_memories_expires_at"), "session_memories", ["expires_at"], unique=False
        )

    # Create episode_memories table
    if "episode_memories" not in existing_tables:
        op.create_table(
            "episode_memories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("summary", sa.String(), nullable=True),
            sa.Column("one_sentence_summary", sa.String(), nullable=True),
            sa.Column(
                "key_moments",
                postgresql.ARRAY(postgresql.JSON(astext_type=sa.Text())),
                nullable=True,
            ),
            sa.Column(
                "relationships_changed", postgresql.JSON(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("themes", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("cliffhangers", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("characters", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
            sa.Column("locations", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
            sa.Column(
                "session_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True
            ),
            sa.Column("embedding", Vector(1536), nullable=True),
            sa.Column("importance_score", sa.Float(), nullable=True),
            sa.Column("promoted_to_world", sa.Boolean(), nullable=False, server_default="false"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_episode_memories_expires_at"), "episode_memories", ["expires_at"], unique=False
        )
        op.create_index(
            op.f("ix_episode_memories_promoted_to_world"),
            "episode_memories",
            ["promoted_to_world"],
            unique=False,
        )
        # Create IVFFlat index for episode embeddings
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_episode_embedding 
            ON episode_memories 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
        """)

    # Create world_memories table
    if "world_memories" not in existing_tables:
        op.create_table(
            "world_memories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("memory_category", sa.String(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("full_narrative", sa.String(), nullable=True),
            sa.Column("related_entities", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "source_episodes", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True
            ),
            sa.Column("consequences", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("embedding", Vector(1536), nullable=True),
            sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("impact_level", sa.String(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "discovery_requirements", postgresql.JSON(astext_type=sa.Text()), nullable=True
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_world_memories_impact_level"), "world_memories", ["impact_level"], unique=False
        )
        op.create_index(
            op.f("ix_world_memories_is_public"), "world_memories", ["is_public"], unique=False
        )
        # Create IVFFlat index for world embeddings
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_world_embedding 
            ON world_memories 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

    # Create character_recognition table
    if "character_recognition" not in existing_tables:
        op.create_table(
            "character_recognition",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("known_character_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("first_met_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("known_name", sa.String(length=255), nullable=True),
            sa.Column("known_details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("relationship_type", sa.String(length=50), nullable=True),
            sa.Column("trust_level", sa.Float(), nullable=True),
            sa.Column(
                "shared_episodes", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True
            ),
            sa.ForeignKeyConstraint(
                ["character_id"],
                ["characters.id"],
            ),
            sa.ForeignKeyConstraint(
                ["known_character_id"],
                ["characters.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "character_id", "known_character_id", name="uq_character_known_character"
            ),
        )
        op.create_index(
            op.f("ix_character_recognition_character_id"),
            "character_recognition",
            ["character_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_character_recognition_known_character_id"),
            "character_recognition",
            ["known_character_id"],
            unique=False,
        )

    # Create memory_snapshots table
    if "memory_snapshots" not in existing_tables:
        op.create_table(
            "memory_snapshots",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("snapshot_type", sa.String(), nullable=False),
            sa.Column("snapshot_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("world_memory_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_reason", sa.String(), nullable=False),
            sa.Column("can_unwind", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("unwound_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("unwound_by", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_memory_snapshots_world_memory_id"),
            "memory_snapshots",
            ["world_memory_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_memory_snapshots_episode_id"), "memory_snapshots", ["episode_id"], unique=False
        )

    # Create memory_settings table
    if "memory_settings" not in existing_tables:
        op.create_table(
            "memory_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "session_memory_expiration_hours", sa.Integer(), nullable=False, server_default="4"
            ),
            sa.Column(
                "episode_memory_expiration_hours", sa.Integer(), nullable=False, server_default="48"
            ),
            sa.Column("snapshot_retention_days", sa.Integer(), nullable=False, server_default="90"),
            sa.Column("auto_cleanup_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.PrimaryKeyConstraint("id"),
        )
        # Insert default settings record
        op.execute("""
            INSERT INTO memory_settings (id, created_at, updated_at)
            VALUES (gen_random_uuid(), NOW(), NOW())
            ON CONFLICT DO NOTHING
        """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop memory_settings table
    op.drop_table("memory_settings")

    # Drop memory_snapshots table
    op.drop_index(op.f("ix_memory_snapshots_episode_id"), table_name="memory_snapshots")
    op.drop_index(op.f("ix_memory_snapshots_world_memory_id"), table_name="memory_snapshots")
    op.drop_table("memory_snapshots")

    # Drop character_recognition table
    op.drop_index(
        op.f("ix_character_recognition_known_character_id"), table_name="character_recognition"
    )
    op.drop_index(op.f("ix_character_recognition_character_id"), table_name="character_recognition")
    op.drop_table("character_recognition")

    # Drop world_memories table
    op.execute("DROP INDEX IF EXISTS idx_world_embedding")
    op.drop_index(op.f("ix_world_memories_is_public"), table_name="world_memories")
    op.drop_index(op.f("ix_world_memories_impact_level"), table_name="world_memories")
    op.drop_table("world_memories")

    # Drop episode_memories table
    op.execute("DROP INDEX IF EXISTS idx_episode_embedding")
    op.drop_index(op.f("ix_episode_memories_promoted_to_world"), table_name="episode_memories")
    op.drop_index(op.f("ix_episode_memories_expires_at"), table_name="episode_memories")
    op.drop_table("episode_memories")

    # Drop session_memories table
    op.drop_index(op.f("ix_session_memories_expires_at"), table_name="session_memories")
    op.drop_index(op.f("ix_session_memories_processed"), table_name="session_memories")
    op.drop_index(op.f("ix_session_memories_character_id"), table_name="session_memories")
    op.drop_index(op.f("ix_session_memories_session_id"), table_name="session_memories")
    op.drop_table("session_memories")
