import logging
from datetime import UTC, datetime

from ds_common.memory.game_time_service import GameTimeService
from ds_common.models.world_event import EventStatus, WorldEvent
from ds_common.models.world_memory import WorldMemory
from ds_common.repository.world_event import WorldEventRepository
from ds_common.repository.world_memory import WorldMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class EventProcessor:
    """
    Service for processing world events, evaluating conditions, and managing state transitions.
    """

    def __init__(self, postgres_manager: PostgresManager, game_time_service: GameTimeService):
        self.postgres_manager = postgres_manager
        self.game_time_service = game_time_service
        self.event_repo = WorldEventRepository(postgres_manager)
        self.world_memory_repo = WorldMemoryRepository(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def evaluate_conditions(self, conditions: dict | None) -> bool:
        """
        Evaluate event conditions.

        Args:
            conditions: Condition dictionary

        Returns:
            True if conditions are met, False otherwise
        """
        if not conditions:
            return True

        # Check game time conditions
        if "game_time" in conditions:
            game_time = await self.game_time_service.get_current_game_time()
            time_conditions = conditions["game_time"]

            if "year" in time_conditions and game_time.game_year != time_conditions["year"]:
                return False
            if "day" in time_conditions and game_time.game_day != time_conditions["day"]:
                return False
            if "hour" in time_conditions and game_time.game_hour != time_conditions["hour"]:
                return False
            if "season" in time_conditions and game_time.season != time_conditions["season"]:
                return False

        # Check real time conditions
        if "real_time" in conditions:
            time_conditions = conditions["real_time"]
            now = datetime.now(UTC)

            if "after" in time_conditions:
                after_time = datetime.fromisoformat(time_conditions["after"].replace("Z", "+00:00"))
                if now < after_time:
                    return False

            if "before" in time_conditions:
                before_time = datetime.fromisoformat(
                    time_conditions["before"].replace("Z", "+00:00")
                )
                if now > before_time:
                    return False

        # Check faction standing conditions
        if "faction_standing" in conditions:
            raise NotImplementedError(
                "Faction standing checks are not yet implemented. "
                "The faction system needs to be implemented before events with faction standing conditions can be evaluated."
            )

        # Check other custom conditions
        if "custom" in conditions:
            # Custom condition evaluation logic
            # This would be extended based on specific game mechanics
            pass

        return True

    async def check_event_conditions(self, event: WorldEvent) -> tuple[bool, bool]:
        """
        Check if event start/end conditions are met.

        Args:
            event: WorldEvent to check

        Returns:
            Tuple of (start_conditions_met, end_conditions_met)
        """
        start_met = await self.evaluate_conditions(event.start_conditions)
        end_met = await self.evaluate_conditions(event.end_conditions)
        return start_met, end_met

    async def transition_event_status(
        self, event: WorldEvent, new_status: EventStatus
    ) -> WorldEvent:
        """
        Transition an event to a new status and create world memory if needed.

        Args:
            event: WorldEvent to transition
            new_status: New status

        Returns:
            Updated WorldEvent
        """
        old_status = event.status
        event.status = new_status

        # Create world memory for significant status changes
        if new_status == "ACTIVE" and old_status != "ACTIVE":
            await self._create_event_memory(event, "started")

        if new_status == "COMPLETED":
            await self._create_event_memory(event, "completed")

        return await self.event_repo.update(event)

    async def _create_event_memory(self, event: WorldEvent, action: str) -> WorldMemory:
        """
        Create a world memory for an event status change.

        Args:
            event: WorldEvent
            action: Action that occurred (started, completed, etc.)

        Returns:
            Created WorldMemory
        """
        game_time = await self.game_time_service.get_current_game_time()
        game_time_context = {
            "year": game_time.game_year,
            "day": game_time.game_day,
            "hour": game_time.game_hour,
            "season": game_time.season,
        }

        memory = WorldMemory(
            memory_category="event",
            title=f"{event.title} - {action.title()}",
            description=f"The event '{event.title}' has {action}.",
            full_narrative=f"Event: {event.title}\nDescription: {event.description or 'N/A'}\nStatus: {action}",
            impact_level=event.impact_level or "moderate",
            related_world_event_id=event.id,
            game_time_context=game_time_context,
            regional_context=event.regional_scope,
        )

        return await self.world_memory_repo.create(memory)

    async def process_all_events(self) -> list[WorldEvent]:
        """
        Process all active events and check their conditions.

        Returns:
            List of events that were updated
        """
        active_events = await self.event_repo.get_by_status("ACTIVE")
        planned_events = await self.event_repo.get_by_status("PLANNED")
        updated_events = []

        # Check planned events for activation
        for event in planned_events:
            start_met, _ = await self.check_event_conditions(event)
            if start_met:
                event = await self.transition_event_status(event, "ACTIVE")
                updated_events.append(event)

        # Check active events for completion
        for event in active_events:
            _, end_met = await self.check_event_conditions(event)
            if end_met:
                event = await self.transition_event_status(event, "COMPLETED")
                updated_events.append(event)

        return updated_events
