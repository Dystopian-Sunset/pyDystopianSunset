"""
Background tasks for game time advancement, event processing, and calendar activation.
"""

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from ds_common.memory.calendar_service import CalendarService
from ds_common.memory.cleanup_service import CleanupService
from ds_common.memory.event_processor import EventProcessor
from ds_common.memory.game_time_service import GameTimeService
from ds_common.metrics.service import get_metrics_service
from ds_common.repository.game_settings import GameSettingsRepository
from ds_discord_bot.postgres_manager import PostgresManager


class BackgroundTasks:
    """
    Background task manager for automated game world processes.
    """

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres_manager = postgres_manager
        self.logger = logging.getLogger(__name__)
        self.game_time_service = GameTimeService(postgres_manager)
        self.event_processor = EventProcessor(postgres_manager, self.game_time_service)
        self.calendar_service = CalendarService(postgres_manager, self.game_time_service)
        self.cleanup_service = CleanupService(postgres_manager)
        self.metrics = get_metrics_service()
        self._running = False
        self._tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> None:
        """Start all background tasks."""
        if self._running:
            self.logger.warning("Background tasks already running")
            return

        self._running = True
        self.logger.info("Starting background tasks...")

        # Start game time advancement task (runs every minute)
        time_task = asyncio.create_task(self._time_advancement_loop())
        self._tasks.append(time_task)

        # Start event processing task (runs every 5 minutes)
        event_task = asyncio.create_task(self._event_processing_loop())
        self._tasks.append(event_task)

        # Start calendar activation task (runs every 10 minutes)
        calendar_task = asyncio.create_task(self._calendar_activation_loop())
        self._tasks.append(calendar_task)

        # Start cleanup task (runs every hour)
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._tasks.append(cleanup_task)

        # Start game time persistence task (runs at configurable interval)
        persistence_task = asyncio.create_task(self._game_time_persistence_loop())
        self._tasks.append(persistence_task)

        self.logger.info("Background tasks started")

    async def stop(self) -> None:
        """Stop all background tasks."""
        if not self._running:
            return

        self.logger.info("Stopping background tasks...")
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        self.logger.info("Background tasks stopped")

    async def _time_advancement_loop(self) -> None:
        """Advance game time periodically (every minute)."""
        while self._running:
            start_time = time.time()
            status = "success"
            try:
                # Advance game time by 1 real minute
                await self.game_time_service.advance_game_time(1.0)

                # Check for day/night transitions
                game_time = await self.game_time_service.get_current_game_time()
                was_daytime = game_time.is_daytime

                # The advance_game_time method already updates is_daytime
                # We could add transition notifications here if needed

                # Check for season changes
                # Season is updated in advance_game_time, but we could add notifications

                await asyncio.sleep(60)  # Wait 1 minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                status = "error"
                self.logger.error(f"Error in time advancement loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
            finally:
                duration = time.time() - start_time
                self.metrics.record_background_task("time_advancement", duration, status)

    async def _event_processing_loop(self) -> None:
        """Process world events periodically (every 5 minutes)."""
        while self._running:
            start_time = time.time()
            status = "success"
            try:
                # Process all events
                updated_events = await self.event_processor.process_all_events()

                if updated_events:
                    self.logger.info(f"Processed {len(updated_events)} world events")

                await asyncio.sleep(300)  # Wait 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                status = "error"
                self.logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(300)  # Wait before retrying
            finally:
                duration = time.time() - start_time
                self.metrics.record_background_task("event_processing", duration, status)

    async def _calendar_activation_loop(self) -> None:
        """Activate/deactivate calendar events periodically (every 10 minutes)."""
        while self._running:
            start_time = time.time()
            status = "success"
            try:
                # Get active events
                active_events = await self.calendar_service.get_active_events()

                # Create world memories for newly active events if needed
                # This could be optimized to only create memories once per event activation
                for event in active_events:
                    # Check if memory already exists for this activation
                    # For now, we'll skip to avoid duplicates
                    # In production, you'd track which events have had memories created
                    pass

                await asyncio.sleep(600)  # Wait 10 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                status = "error"
                self.logger.error(f"Error in calendar activation loop: {e}")
                await asyncio.sleep(600)  # Wait before retrying
            finally:
                duration = time.time() - start_time
                self.metrics.record_background_task("calendar_activation", duration, status)

    async def _cleanup_loop(self) -> None:
        """Clean up expired memories and archive old snapshots periodically (every hour)."""
        while self._running:
            start_time = time.time()
            status = "success"
            try:
                # Clean up expired memories
                cleanup_stats = await self.cleanup_service.cleanup_expired_memories()
                if cleanup_stats.get("enabled"):
                    self.logger.info(
                        f"Memory cleanup: deleted {cleanup_stats.get('session_memories_deleted', 0)} session memories, "
                        f"{cleanup_stats.get('episode_memories_deleted', 0)} episode memories"
                    )

                # Archive old snapshots
                archive_stats = await self.cleanup_service.archive_old_snapshots()
                if archive_stats.get("enabled"):
                    self.logger.info(
                        f"Snapshot archiving: archived {archive_stats.get('snapshots_archived', 0)} snapshots"
                    )

                await asyncio.sleep(3600)  # Wait 1 hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                status = "error"
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)  # Wait before retrying
            finally:
                duration = time.time() - start_time
                self.metrics.record_background_task("cleanup", duration, status)

    async def _game_time_persistence_loop(self) -> None:
        """Persist game time state periodically at configurable interval."""
        while self._running:
            start_time = time.time()
            status = "success"
            try:
                # Get persistence interval from game settings
                settings_repo = GameSettingsRepository(self.postgres_manager)
                default_id = UUID("00000000-0000-0000-0000-000000000001")
                settings = await settings_repo.get_by_id(default_id)

                if settings and settings.game_time_persistence_interval_minutes > 0:
                    interval_seconds = settings.game_time_persistence_interval_minutes * 60

                    # Persist game time state
                    await self.game_time_service.persist_game_time_incremental()

                    await asyncio.sleep(interval_seconds)
                else:
                    # If persistence is disabled (interval = 0), check again in 5 minutes
                    await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                status = "error"
                self.logger.error(f"Error in game time persistence loop: {e}")
                # Wait 5 minutes before retrying if there's an error
                await asyncio.sleep(300)
            finally:
                duration = time.time() - start_time
                self.metrics.record_background_task("game_time_persistence", duration, status)
