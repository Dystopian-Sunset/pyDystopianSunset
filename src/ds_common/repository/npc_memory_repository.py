import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.npc_memory import NPCMemory
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class NPCMemoryRepository(BaseRepository[NPCMemory]):
    """
    Repository for NPCMemory model with vector similarity search.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, NPCMemory)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def store_memory(
        self,
        npc_id: str,
        memory_text: str,
        embedding: list[float],
        metadata: dict[str, str] | None = None,
        session: AsyncSession | None = None,
    ) -> NPCMemory:
        """
        Store a new NPC memory with embedding.

        Args:
            npc_id: NPC UUID
            memory_text: The memory text content
            embedding: Vector embedding (1536 dimensions)
            metadata: Optional metadata dictionary
            session: Optional database session

        Returns:
            Created NPCMemory instance
        """
        memory = NPCMemory(
            npc_id=npc_id,
            memory_text=memory_text,
            embedding=embedding,
            meta_data=metadata,
        )
        return await self.create(memory, session=session)

    async def search_similar(
        self,
        query_embedding: list[float],
        npc_id: str | None = None,
        limit: int = 10,
        session: AsyncSession | None = None,
    ) -> list[tuple[NPCMemory, float]]:
        """
        Search for similar memories using vector similarity.

        Args:
            query_embedding: Query vector embedding (1536 dimensions)
            npc_id: Optional NPC ID to filter by
            limit: Maximum number of results
            session: Optional database session

        Returns:
            List of tuples (NPCMemory, similarity_score)
        """

        async def _execute(sess: AsyncSession):
            # Use pgvector cosine distance operator (<->)
            # Lower distance = more similar
            # Note: This requires pgvector extension and proper column type
            from pgvector.sqlalchemy import Vector
            from sqlalchemy import cast

            # Cast query embedding to Vector type for comparison
            query_vec = cast(query_embedding, Vector(768))

            stmt = select(
                NPCMemory,
                (NPCMemory.embedding.op("<->")(query_vec)).label("distance"),
            )

            if npc_id:
                stmt = stmt.where(NPCMemory.npc_id == npc_id)

            stmt = stmt.order_by("distance").limit(limit)

            result = await sess.execute(stmt)
            return [(row[0], row[1]) for row in result.all()]

        return await self._with_session(_execute, session)

    async def get_by_npc(self, npc_id: str, session: AsyncSession | None = None) -> list[NPCMemory]:
        """
        Get all memories for an NPC.

        Args:
            npc_id: NPC UUID
            session: Optional database session

        Returns:
            List of NPCMemory instances
        """
        from sqlmodel import select

        async def _execute(sess: AsyncSession):
            stmt = select(NPCMemory).where(NPCMemory.npc_id == npc_id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)
