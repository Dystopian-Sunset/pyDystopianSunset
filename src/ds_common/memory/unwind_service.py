"""Unwind service for rolling back world state from snapshots."""

import logging
from uuid import UUID

from ds_common.models.world_memory import WorldMemory
from ds_common.repository.memory_snapshot import MemorySnapshotRepository
from ds_common.repository.world_memory import WorldMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class UnwindService:
    """Service for unwinding snapshots to restore world state."""

    def __init__(self, postgres_manager: PostgresManager):
        """
        Initialize the unwind service.

        Args:
            postgres_manager: PostgreSQL manager
        """
        self.logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager

        # Initialize repositories
        self.snapshot_repo = MemorySnapshotRepository(postgres_manager)
        self.world_repo = WorldMemoryRepository(postgres_manager)

    async def validate_unwind(
        self,
        snapshot_id: UUID,
    ) -> tuple[bool, str]:
        """
        Validate if a snapshot can be safely unwound.

        Args:
            snapshot_id: Snapshot ID to validate

        Returns:
            Tuple of (is_valid, reason)
        """
        self.logger.debug(f"Validating unwind for snapshot {snapshot_id}")

        snapshot = await self.snapshot_repo.get_by_id(snapshot_id)
        if not snapshot:
            return False, "Snapshot not found"

        if snapshot.unwound_at:
            return False, "Snapshot already unwound"

        if not snapshot.can_unwind:
            return False, "Snapshot cannot be unwound"

        # Check for dependent world memories created after snapshot
        snapshot_timestamp = snapshot.created_at
        all_memories = await self.world_repo.get_all()
        dependent_memories = [wm for wm in all_memories if wm.created_at > snapshot_timestamp]

        if dependent_memories:
            return (
                False,
                f"Found {len(dependent_memories)} world memories created after snapshot. Unwinding may cause inconsistencies.",
            )

        return True, "Snapshot is valid for unwinding"

    async def get_unwind_preview(
        self,
        snapshot_id: UUID,
    ) -> dict:
        """
        Get a preview of what will be restored.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Dictionary with preview information
        """
        self.logger.debug(f"Getting unwind preview for snapshot {snapshot_id}")

        snapshot = await self.snapshot_repo.get_by_id(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        snapshot_data = snapshot.snapshot_data
        world_memories_count = len(snapshot_data.get("world_memories", []))

        # Get current world state
        current_memories = await self.world_repo.get_all()
        current_count = len(current_memories)

        return {
            "snapshot_id": str(snapshot_id),
            "snapshot_created_at": snapshot.created_at.isoformat(),
            "snapshot_reason": snapshot.created_reason,
            "world_memories_in_snapshot": world_memories_count,
            "current_world_memories": current_count,
            "memories_to_restore": world_memories_count,
            "memories_to_remove": current_count - world_memories_count,
        }

    async def unwind_snapshot(
        self,
        snapshot_id: UUID,
        unwound_by: int,
    ) -> dict:
        """
        Unwind a snapshot to restore world state.

        Args:
            snapshot_id: Snapshot ID to unwind
            unwound_by: Discord user ID who performed the unwind

        Returns:
            Dictionary with unwind results
        """
        self.logger.info(f"Unwinding snapshot {snapshot_id}")

        # Validate
        is_valid, reason = await self.validate_unwind(snapshot_id)
        if not is_valid:
            raise ValueError(f"Cannot unwind snapshot: {reason}")

        snapshot = await self.snapshot_repo.get_by_id(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        snapshot_data = snapshot.snapshot_data
        world_memories_data = snapshot_data.get("world_memories", [])

        # Delete current world memories
        current_memories = await self.world_repo.get_all()
        for memory in current_memories:
            await self.world_repo.delete(memory.id)

        # Restore world memories from snapshot
        restored_count = 0
        for memory_data in world_memories_data:
            try:
                # Recreate world memory from snapshot data
                memory = WorldMemory(**memory_data)
                await self.world_repo.create(memory)
                restored_count += 1
            except Exception as e:
                self.logger.error(f"Failed to restore memory: {e}")

        # Mark snapshot as unwound
        await self.snapshot_repo.mark_unwound(snapshot_id, unwound_by)

        result = {
            "snapshot_id": str(snapshot_id),
            "restored_memories": restored_count,
            "removed_memories": len(current_memories),
        }

        self.logger.info(f"Unwound snapshot {snapshot_id}: restored {restored_count} memories")

        return result
