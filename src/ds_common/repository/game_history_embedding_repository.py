import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.game_history_embedding import GameHistoryEmbedding
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class GameHistoryEmbeddingRepository(BaseRepository[GameHistoryEmbedding]):
    """
    Repository for GameHistoryEmbedding model with vector similarity search.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, GameHistoryEmbedding)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def store_history(
        self,
        game_session_id: str,
        history_text: str,
        embedding: list[float],
        metadata: dict[str, str] | None = None,
        session: AsyncSession | None = None,
    ) -> GameHistoryEmbedding:
        """
        Store a new game history entry with embedding.

        Args:
            game_session_id: Game session UUID
            history_text: The history text content
            embedding: Vector embedding (1536 dimensions)
            metadata: Optional metadata dictionary
            session: Optional database session

        Returns:
            Created GameHistoryEmbedding instance
        """
        history = GameHistoryEmbedding(
            game_session_id=game_session_id,
            history_text=history_text,
            embedding=embedding,
            meta_data=metadata,
        )
        return await self.create(history, session=session)

    async def search_similar(
        self,
        query_embedding: list[float],
        game_session_id: str | None = None,
        limit: int = 10,
        session: AsyncSession | None = None,
    ) -> list[tuple[GameHistoryEmbedding, float]]:
        """
        Search for similar history entries using vector similarity.

        Args:
            query_embedding: Query vector embedding (1536 dimensions)
            game_session_id: Optional game session ID to filter by
            limit: Maximum number of results
            session: Optional database session

        Returns:
            List of tuples (GameHistoryEmbedding, similarity_score)
        """

        async def _execute(sess: AsyncSession):
            # Use pgvector cosine distance operator (<->)
            # Lower distance = more similar
            from pgvector.sqlalchemy import Vector
            from sqlalchemy import cast

            # Cast query embedding to Vector type for comparison
            query_vec = cast(query_embedding, Vector(768))

            stmt = select(
                GameHistoryEmbedding,
                (GameHistoryEmbedding.embedding.op("<->")(query_vec)).label("distance"),
            )

            if game_session_id:
                stmt = stmt.where(GameHistoryEmbedding.game_session_id == game_session_id)

            stmt = stmt.order_by("distance").limit(limit)

            result = await sess.execute(stmt)
            return [(row[0], row[1]) for row in result.all()]

        return await self._with_session(_execute, session)

    async def get_by_game_session(
        self, game_session_id: str, session: AsyncSession | None = None
    ) -> list[GameHistoryEmbedding]:
        """
        Get all history entries for a game session.

        Args:
            game_session_id: Game session UUID
            session: Optional database session

        Returns:
            List of GameHistoryEmbedding instances
        """
        from sqlmodel import select

        async def _execute(sess: AsyncSession):
            stmt = select(GameHistoryEmbedding).where(
                GameHistoryEmbedding.game_session_id == game_session_id
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)
