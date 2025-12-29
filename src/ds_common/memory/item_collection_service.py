import logging
from datetime import UTC, datetime
from uuid import UUID

from ds_common.memory.game_time_service import GameTimeService
from ds_common.models.world_item import WorldItem
from ds_common.models.world_memory import WorldMemory
from ds_common.repository.world_item import WorldItemRepository
from ds_common.repository.world_memory import WorldMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class ItemCollectionService:
    """
    Service for managing world item collection, quest updates, and first-come-first-served logic.
    """

    def __init__(self, postgres_manager: PostgresManager, game_time_service: GameTimeService):
        self.postgres_manager = postgres_manager
        self.game_time_service = game_time_service
        self.item_repo = WorldItemRepository(postgres_manager)
        self.world_memory_repo = WorldMemoryRepository(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def check_collection_conditions(
        self, item: WorldItem, character_id: UUID | None = None
    ) -> bool:
        """
        Check if collection conditions are met for an item.

        Args:
            item: WorldItem to check
            character_id: Optional character ID to check conditions against

        Returns:
            True if conditions are met, False otherwise

        Raises:
            NotImplementedError: If faction conditions are specified (faction system not yet implemented)
        """
        if not item.collection_condition:
            return True

        conditions = item.collection_condition

        # Check location conditions
        if "location" in conditions:
            if not character_id:
                self.logger.warning(
                    f"Location condition specified for item {item.name} but no character_id provided"
                )
                return False

            required_location = conditions["location"]
            if isinstance(required_location, str):
                # Get character's current location
                from ds_common.repository.character import CharacterRepository

                character_repo = CharacterRepository(self.postgres_manager)
                character = await character_repo.get_by_id(character_id)
                if not character or not character.current_location:
                    return False

                # Check if character is in required location
                from ds_common.repository.location_node import LocationNodeRepository

                node_repo = LocationNodeRepository(self.postgres_manager)
                character_location = await node_repo.get_by_id(character.current_location)
                if not character_location:
                    return False

                # Match by location name (case-insensitive)
                if character_location.location_name.lower() != required_location.lower():
                    # Also check parent location
                    if character_location.parent_location_id:
                        parent_location = await node_repo.get_by_id(
                            character_location.parent_location_id
                        )
                        if (
                            parent_location
                            and parent_location.location_name.lower() != required_location.lower()
                        ):
                            return False
                    else:
                        return False

        # Check quest conditions
        if "quest" in conditions:
            if not character_id:
                self.logger.warning(
                    f"Quest condition specified for item {item.name} but no character_id provided"
                )
                return False

            required_quest_id = conditions["quest"]
            if isinstance(required_quest_id, str):
                try:
                    from uuid import UUID

                    required_quest_id = UUID(required_quest_id)
                except ValueError:
                    self.logger.warning(
                        f"Invalid quest ID format in collection condition for item {item.name}"
                    )
                    return False

            # Check if character has the required quest
            from ds_common.repository.character import CharacterRepository
            from ds_common.repository.quest import QuestRepository

            character_repo = CharacterRepository(self.postgres_manager)
            quest_repo = QuestRepository(self.postgres_manager)

            character = await character_repo.get_by_id(character_id)
            if not character:
                return False

            character_quests = await quest_repo.get_character_quests(character)
            quest_ids = [quest.id for quest in character_quests]

            if required_quest_id not in quest_ids:
                return False

        # Check faction conditions
        if "faction" in conditions:
            raise NotImplementedError(
                "Faction standing checks are not yet implemented. "
                "The faction system needs to be implemented before items with faction conditions can be collected."
            )

        # Check custom conditions
        if "custom" in conditions:
            # Custom condition evaluation - for now, log and allow
            # This can be extended with custom evaluation logic
            self.logger.debug(
                f"Custom collection condition for item {item.name}: {conditions['custom']}"
            )

        return True

    async def collect_item(
        self,
        item: WorldItem,
        character_id: UUID,
        session_id: UUID | None = None,
    ) -> WorldItem:
        """
        Mark an item as collected by a character.

        Args:
            item: WorldItem to collect
            character_id: Character ID who collected it
            session_id: Optional session ID when collected

        Returns:
            Updated WorldItem

        Raises:
            ValueError: If item is not available or conditions not met
        """
        if item.status != "AVAILABLE":
            raise ValueError(f"Item {item.name} is not available (status: {item.status})")

        if not await self.check_collection_conditions(item):
            raise ValueError(f"Collection conditions not met for item {item.name}")

        # Mark as collected
        item.status = "COLLECTED"
        item.collected_by = character_id
        item.collected_at = datetime.now(UTC)
        item.collection_session_id = session_id

        # Get game time
        game_time = await self.game_time_service.get_current_game_time()
        item.collected_at_game_time = {
            "year": game_time.game_year,
            "day": game_time.game_day,
            "hour": game_time.game_hour,
        }

        # Create world memory
        await self._create_collection_memory(item, character_id)

        # Update related quests if item has quest_goals
        if item.quest_goals:
            await self._update_related_quests(item, character_id)

        return await self.item_repo.update(item)

    async def _update_related_quests(self, item: WorldItem, character_id: UUID) -> None:
        """
        Update quest progress when an item with quest_goals is collected.

        Args:
            item: WorldItem that was collected
            character_id: Character who collected it
        """
        from ds_common.repository.character import CharacterRepository
        from ds_common.repository.quest import QuestRepository

        character_repo = CharacterRepository(self.postgres_manager)
        quest_repo = QuestRepository(self.postgres_manager)

        character = await character_repo.get_by_id(character_id)
        if not character:
            self.logger.warning(
                f"Character {character_id} not found when updating quests for item {item.name}"
            )
            return

        # Get character's active quests
        character_quests = await quest_repo.get_character_quests(character)
        character_quest_ids = {quest.id for quest in character_quests}

        # Check each quest goal
        for quest_id in item.quest_goals:
            if quest_id in character_quest_ids:
                # Character has this quest, log the item collection
                quest = next(q for q in character_quests if q.id == quest_id)
                self.logger.info(
                    f"Character {character.name} collected item {item.name} "
                    f"for quest {quest.name} (quest_id: {quest_id})"
                )
                # Note: Quest progress tracking is not yet implemented in the database schema.
                # To implement this, the CharacterQuest junction table would need a field to track
                # completed tasks (e.g., completed_tasks: list[str] or progress: dict).
                # When that is added, this method should update the quest progress here.
            else:
                # Character doesn't have this quest, but item is quest-related
                # This is fine - they may get the quest later, or the item may be for multiple quests
                self.logger.debug(
                    f"Item {item.name} is related to quest {quest_id}, "
                    f"but character {character.name} doesn't have this quest yet"
                )

    async def _create_collection_memory(self, item: WorldItem, character_id: UUID) -> WorldMemory:
        """
        Create a world memory for item collection.

        Args:
            item: WorldItem that was collected
            character_id: Character who collected it

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
            title=f"{item.name} Collected",
            description=f"The world item '{item.name}' has been collected.",
            full_narrative=f"World Item: {item.name}\nType: {item.item_type}\nDescription: {item.description or 'N/A'}\nCollected by character: {character_id}",
            impact_level="moderate" if item.item_type == "UNIQUE" else "minor",
            related_world_item_id=item.id,
            game_time_context=game_time_context,
        )

        return await self.world_memory_repo.create(memory)

    async def reset_item(self, item: WorldItem) -> WorldItem:
        """
        Reset an item to available status.

        Args:
            item: WorldItem to reset

        Returns:
            Updated WorldItem
        """
        item.status = "AVAILABLE"
        item.collected_by = None
        item.collected_at = None
        item.collected_at_game_time = None
        item.collection_session_id = None

        return await self.item_repo.update(item)

    async def get_available_items_for_quest(self, quest_id: UUID) -> list[WorldItem]:
        """
        Get all available items required for a quest.

        Args:
            quest_id: Quest ID

        Returns:
            List of available WorldItem instances
        """
        quest_items = await self.item_repo.get_by_quest(quest_id)
        return [item for item in quest_items if item.status == "AVAILABLE"]
