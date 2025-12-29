import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.metrics.service import get_metrics_service
from ds_common.models.character import Character
from ds_common.models.junction_tables import CharacterQuest
from ds_common.models.quest import Quest
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class QuestRepository(BaseRepository[Quest]):
    """
    Repository for Quest model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, Quest)
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.metrics = get_metrics_service()

    async def create(self, model: Quest, session=None):
        """Create a quest and log/metric the world state change."""
        created_quest = await super().create(model, session)
        
        # Log and record metrics for world state change
        self.logger.info(
            f"World state change: Quest created - {created_quest.name} "
            f"(ID: {created_quest.id}, Tasks: {len(created_quest.tasks)})"
        )
        self.metrics.record_world_state_change("quest", "created")
        
        return created_quest

    async def get_character_quests(
        self, character: Character, session: AsyncSession | None = None
    ) -> list[Quest]:
        """
        Get all quests for a character.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            List of Quest instances
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(character, ["quests"])
                return character.quests or []
            fresh_character = await sess.get(Character, character.id)
            if not fresh_character:
                return []
            await sess.refresh(fresh_character, ["quests"])
            return fresh_character.quests or []

        return await self._with_session(_execute, session, read_only=True)

    async def add_character_quest(
        self,
        character: Character,
        quest: Quest,
        items_given: list[dict] | None = None,
        session_id: UUID | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """
        Add a quest to a character.

        Args:
            character: Character instance
            quest: Quest instance
            items_given: Optional list of items given when accepting the quest.
                        Format: [{'name': 'Item Name', 'quantity': 1, 'instance_id': '...'}]
            session_id: Optional game session ID when quest was accepted (for cleanup)
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            # Check if relationship already exists
            stmt = select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
            result = await sess.execute(stmt)
            if result.scalar_one_or_none():
                return  # Already exists

            # Create junction table entry with items_given and session_id
            junction = CharacterQuest(
                character_id=character.id,
                quest_id=quest.id,
                items_given=items_given or [],
                session_id=session_id,
            )
            sess.add(junction)
            await sess.commit()

        await self._with_session(_execute, session)
        self.logger.debug(
            f"Character quest added: {quest} with {len(items_given or [])} items in session {session_id}"
        )

    async def get_quests_by_session(
        self, session_id: UUID, session: AsyncSession | None = None
    ) -> list[CharacterQuest]:
        """
        Get all character-quest relationships for a specific session.

        Args:
            session_id: Game session ID
            session: Optional database session

        Returns:
            List of CharacterQuest instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(CharacterQuest).where(CharacterQuest.session_id == session_id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session, read_only=True)

    async def get_character_quest_items(
        self, character: Character, quest: Quest, session: AsyncSession | None = None
    ) -> list[dict]:
        """
        Get items that were given to a character when accepting a quest.

        Args:
            character: Character instance
            quest: Quest instance
            session: Optional database session

        Returns:
            List of item dictionaries that were given with the quest
        """

        async def _execute(sess: AsyncSession):
            stmt = select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
            result = await sess.execute(stmt)
            junction = result.scalar_one_or_none()
            if junction:
                return junction.items_given or []
            return []

        return await self._with_session(_execute, session, read_only=True)

    async def remove_character_quest(
        self, character: Character, quest: Quest, session: AsyncSession | None = None
    ) -> list[dict]:
        """
        Remove a quest from a character (abandon quest).

        Args:
            character: Character instance
            quest: Quest instance to remove
            session: Optional database session

        Returns:
            List of items that were given with the quest (to be removed from inventory)
        """

        async def _execute(sess: AsyncSession):
            # Find and remove the junction table entry
            stmt = select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
            result = await sess.execute(stmt)
            junction = result.scalar_one_or_none()
            items_to_remove = []
            if junction:
                items_to_remove = junction.items_given or []
                await sess.delete(junction)
                await sess.commit()
            return items_to_remove

        items_to_remove = await self._with_session(_execute, session)
        self.logger.debug(
            f"Character quest removed: {quest}, returning {len(items_to_remove)} items for removal"
        )
        return items_to_remove
