from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.session_memory import SessionMemory
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class SessionMemoryRepository(BaseRepository[SessionMemory]):
    """Repository for session memory operations."""

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, SessionMemory)

    async def get_by_session(
        self,
        session_id: UUID,
        processed: bool | None = None,
        session: AsyncSession | None = None,
    ) -> list[SessionMemory]:
        """
        Get all session memories for a session.

        Args:
            session_id: Game session ID
            processed: Filter by processed status (None = all)
            session: Optional database session

        Returns:
            List of session memories
        """
        self.logger.debug(f"Getting session memories for session {session_id}")

        async def _execute(sess: AsyncSession):
            stmt = select(SessionMemory).where(SessionMemory.session_id == session_id)
            if processed is not None:
                stmt = stmt.where(SessionMemory.processed == processed)
            stmt = stmt.order_by(SessionMemory.timestamp)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_unprocessed(
        self,
        session: AsyncSession | None = None,
    ) -> list[SessionMemory]:
        """
        Get all unprocessed session memories.

        Args:
            session: Optional database session

        Returns:
            List of unprocessed session memories
        """
        self.logger.debug("Getting unprocessed session memories")

        async def _execute(sess: AsyncSession):
            stmt = (
                select(SessionMemory)
                .where(SessionMemory.processed == False)
                .order_by(SessionMemory.timestamp)
            )  # noqa: E712
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def mark_processed(
        self,
        memory_ids: list[UUID],
        session: AsyncSession | None = None,
    ) -> None:
        """
        Mark session memories as processed.

        Args:
            memory_ids: List of memory IDs to mark as processed
            session: Optional database session
        """
        self.logger.debug(f"Marking {len(memory_ids)} session memories as processed")

        async def _execute(sess: AsyncSession):
            stmt = select(SessionMemory).where(SessionMemory.id.in_(memory_ids))
            result = await sess.execute(stmt)
            memories = result.scalars().all()
            for memory in memories:
                memory.processed = True
            await sess.commit()

        await self._with_session(_execute, session)

    async def get_expired(
        self,
        session: AsyncSession | None = None,
    ) -> list[SessionMemory]:
        """
        Get all expired session memories.

        Args:
            session: Optional database session

        Returns:
            List of expired session memories
        """
        self.logger.debug("Getting expired session memories")

        async def _execute(sess: AsyncSession):
            # Convert timezone-aware datetime to naive UTC for comparison with TIMESTAMP WITHOUT TIME ZONE
            now_naive = datetime.now(UTC).replace(tzinfo=None)
            stmt = select(SessionMemory).where(
                SessionMemory.expires_at.isnot(None),
                SessionMemory.expires_at < now_naive,
                SessionMemory.processed == True,  # noqa: E712
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)
