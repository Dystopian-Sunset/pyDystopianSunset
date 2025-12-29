from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.memory_snapshot import MemorySnapshot
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class MemorySnapshotRepository(BaseRepository[MemorySnapshot]):
    """Repository for memory snapshot operations."""

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, MemorySnapshot)

    async def create_snapshot(
        self,
        snapshot: MemorySnapshot,
        session: AsyncSession | None = None,
    ) -> MemorySnapshot:
        """
        Create a new snapshot.

        Args:
            snapshot: Snapshot to create
            session: Optional database session

        Returns:
            Created snapshot
        """
        return await self.create(snapshot, session)

    async def get_snapshots_for_world_memory(
        self,
        world_memory_id: UUID,
        unwound: bool | None = None,
        session: AsyncSession | None = None,
    ) -> list[MemorySnapshot]:
        """
        Get snapshots for a specific world memory.

        Args:
            world_memory_id: World memory ID
            unwound: Filter by unwound status (None = all)
            session: Optional database session

        Returns:
            List of snapshots
        """
        self.logger.debug(f"Getting snapshots for world memory {world_memory_id}")

        async def _execute(sess: AsyncSession):
            stmt = select(MemorySnapshot).where(MemorySnapshot.world_memory_id == world_memory_id)
            if unwound is not None:
                if unwound:
                    stmt = stmt.where(MemorySnapshot.unwound_at.isnot(None))
                else:
                    stmt = stmt.where(MemorySnapshot.unwound_at.is_(None))
            stmt = stmt.order_by(MemorySnapshot.created_at.desc())
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_all_snapshots(
        self,
        unwound: bool | None = None,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[MemorySnapshot]:
        """
        Get all snapshots with optional filtering.

        Args:
            unwound: Filter by unwound status (None = all)
            limit: Maximum number of results
            session: Optional database session

        Returns:
            List of snapshots
        """
        self.logger.debug("Getting all snapshots")

        async def _execute(sess: AsyncSession):
            stmt = select(MemorySnapshot)
            if unwound is not None:
                if unwound:
                    stmt = stmt.where(MemorySnapshot.unwound_at.isnot(None))
                else:
                    stmt = stmt.where(MemorySnapshot.unwound_at.is_(None))
            stmt = stmt.order_by(MemorySnapshot.created_at.desc())
            if limit:
                stmt = stmt.limit(limit)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_unwound_snapshots(
        self,
        session: AsyncSession | None = None,
    ) -> list[MemorySnapshot]:
        """
        Get all unwound snapshots.

        Args:
            session: Optional database session

        Returns:
            List of unwound snapshots
        """
        return await self.get_all_snapshots(unwound=True, session=session)

    async def mark_unwound(
        self,
        snapshot_id: UUID,
        unwound_by: int,
        session: AsyncSession | None = None,
    ) -> MemorySnapshot:
        """
        Mark a snapshot as unwound.

        Args:
            snapshot_id: Snapshot ID
            unwound_by: Discord user ID who performed the unwind
            session: Optional database session

        Returns:
            Updated snapshot
        """
        self.logger.debug(f"Marking snapshot {snapshot_id} as unwound")

        async def _execute(sess: AsyncSession):
            snapshot = await sess.get(MemorySnapshot, snapshot_id)
            if snapshot:
                snapshot.unwound_at = datetime.now(UTC)
                snapshot.unwound_by = unwound_by
                await sess.commit()
                await sess.refresh(snapshot)
                return snapshot
            raise ValueError(f"Snapshot {snapshot_id} not found")

        return await self._with_session(_execute, session)
