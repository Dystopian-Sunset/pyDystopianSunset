"""Change embedding dimensions from 1536 to 768

Revision ID: 2cc4c69b7fe8
Revises: be9a604b6be3
Create Date: 2025-12-25 15:45:02.289143

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2cc4c69b7fe8"
down_revision: str | Sequence[str] | None = "195a5d532906"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: Change embedding dimensions from 1536 to 768."""
    # Note: Changing vector dimensions requires dropping and recreating the column
    # This will lose existing embedding data, but that's acceptable for this migration

    # Update episode_memories.embedding
    op.execute("""
        ALTER TABLE episode_memories 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE episode_memories 
        ADD COLUMN embedding vector(768);
    """)

    # Update world_memories.embedding
    op.execute("""
        ALTER TABLE world_memories 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE world_memories 
        ADD COLUMN embedding vector(768);
    """)

    # Update npc_memories.embedding
    op.execute("""
        ALTER TABLE npc_memories 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE npc_memories 
        ADD COLUMN embedding vector(768);
    """)

    # Update game_history_embeddings.embedding
    op.execute("""
        ALTER TABLE game_history_embeddings 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE game_history_embeddings 
        ADD COLUMN embedding vector(768);
    """)

    # Recreate indexes if they exist
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_world_embedding 
        ON world_memories 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_episode_embedding 
        ON episode_memories 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50);
    """)


def downgrade() -> None:
    """Downgrade schema: Change embedding dimensions from 768 back to 1536."""
    # Update episode_memories.embedding
    op.execute("""
        ALTER TABLE episode_memories 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE episode_memories 
        ADD COLUMN embedding vector(1536);
    """)

    # Update world_memories.embedding
    op.execute("""
        ALTER TABLE world_memories 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE world_memories 
        ADD COLUMN embedding vector(1536);
    """)

    # Update npc_memories.embedding
    op.execute("""
        ALTER TABLE npc_memories 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE npc_memories 
        ADD COLUMN embedding vector(1536);
    """)

    # Update game_history_embeddings.embedding
    op.execute("""
        ALTER TABLE game_history_embeddings 
        DROP COLUMN IF EXISTS embedding;
    """)
    op.execute("""
        ALTER TABLE game_history_embeddings 
        ADD COLUMN embedding vector(1536);
    """)

    # Recreate indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_world_embedding 
        ON world_memories 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_episode_embedding 
        ON episode_memories 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50);
    """)
