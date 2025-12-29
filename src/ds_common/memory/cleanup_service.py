"""Cleanup service for expiring memories and archiving snapshots."""

import logging
from datetime import UTC, datetime, timedelta

from ds_common.repository.episode_memory import EpisodeMemoryRepository
from ds_common.repository.memory_settings import MemorySettingsRepository
from ds_common.repository.memory_snapshot import MemorySnapshotRepository
from ds_common.repository.session_memory import SessionMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CleanupService:
    """Service for cleaning up expired memories and old snapshots."""

    def __init__(self, postgres_manager: PostgresManager):
        """
        Initialize the cleanup service.

        Args:
            postgres_manager: PostgreSQL manager
        """
        self.logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager

        # Initialize repositories
        self.session_repo = SessionMemoryRepository(postgres_manager)
        self.episode_repo = EpisodeMemoryRepository(postgres_manager)
        self.snapshot_repo = MemorySnapshotRepository(postgres_manager)
        self.settings_repo = MemorySettingsRepository(postgres_manager)

    async def cleanup_expired_memories(self) -> dict:
        """
        Clean up expired session and episode memories.

        Returns:
            Dictionary with cleanup statistics
        """
        self.logger.info("Starting memory cleanup")

        # Check if cleanup is enabled
        settings = await self.settings_repo.get_settings()
        if not settings.auto_cleanup_enabled:
            self.logger.info("Auto cleanup is disabled")
            return {"enabled": False}

        stats = {
            "session_memories_deleted": 0,
            "episode_memories_deleted": 0,
        }

        # Clean up expired session memories
        expired_sessions = await self.session_repo.get_expired()
        for memory in expired_sessions:
            try:
                await self.session_repo.delete(memory.id)
                stats["session_memories_deleted"] += 1
            except Exception as e:
                self.logger.error(f"Failed to delete session memory {memory.id}: {e}")

        # Clean up expired episode memories
        expired_episodes = await self.episode_repo.get_expired()
        for episode in expired_episodes:
            try:
                await self.episode_repo.delete(episode.id)
                stats["episode_memories_deleted"] += 1
            except Exception as e:
                self.logger.error(f"Failed to delete episode memory {episode.id}: {e}")

        self.logger.info(
            f"Cleanup complete: deleted {stats['session_memories_deleted']} session memories, "
            f"{stats['episode_memories_deleted']} episode memories"
        )

        return stats

    async def archive_old_snapshots(self) -> dict:
        """
        Archive old snapshots based on retention policy.

        Returns:
            Dictionary with archiving statistics
        """
        self.logger.info("Starting snapshot archiving")

        settings = await self.settings_repo.get_settings()
        if not settings.auto_cleanup_enabled:
            self.logger.info("Auto cleanup is disabled")
            return {"enabled": False}

        # Get all snapshots
        all_snapshots = await self.snapshot_repo.get_all_snapshots()
        # Convert to naive UTC for comparison (database stores as TIMESTAMP WITHOUT TIME ZONE)
        cutoff_date = (
            datetime.now(UTC) - timedelta(days=settings.snapshot_retention_days)
        ).replace(tzinfo=None)

        stats = {"snapshots_archived": 0}

        for snapshot in all_snapshots:
            # Only archive unwound snapshots older than retention period
            # unwound_at is stored as naive datetime, so compare with naive cutoff_date
            if snapshot.unwound_at and snapshot.unwound_at < cutoff_date:
                try:
                    await self.snapshot_repo.delete(snapshot.id)
                    stats["snapshots_archived"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to archive snapshot {snapshot.id}: {e}")

        self.logger.info(f"Archived {stats['snapshots_archived']} old snapshots")

        return stats
