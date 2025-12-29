"""
Repository for Encounter model.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.encounter import Encounter, EncounterStatus
from ds_common.models.game_session import GameSession
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class EncounterRepository(BaseRepository[Encounter]):
    """
    Repository for Encounter model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, Encounter)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_active_encounter(
        self, game_session: GameSession, session: AsyncSession | None = None
    ) -> Encounter | None:
        """
        Get the active encounter for a game session.

        Args:
            game_session: GameSession instance
            session: Optional database session

        Returns:
            Active Encounter instance or None
        """

        async def _execute(sess: AsyncSession):
            stmt = (
                select(Encounter)
                .where(Encounter.game_session_id == game_session.id)
                .where(Encounter.status == EncounterStatus.ACTIVE)
            )
            result = await sess.execute(stmt)
            return result.scalar_one_or_none()

        return await self._with_session(_execute, session)

    async def end_encounter(
        self, encounter: Encounter, session: AsyncSession | None = None
    ) -> Encounter:
        """
        End an encounter by setting its status to completed.

        Args:
            encounter: Encounter instance to end
            session: Optional database session

        Returns:
            Updated Encounter instance
        """

        async def _execute(sess: AsyncSession):
            encounter.status = EncounterStatus.COMPLETED
            sess.add(encounter)
            await sess.commit()
            await sess.refresh(encounter)
            return encounter

        return await self._with_session(_execute, session)

    async def check_and_mark_dead_npcs(
        self, encounter: Encounter, session: AsyncSession | None = None
    ) -> Encounter:
        """
        Check all NPCs in the encounter and mark any incapacitated ones as dead.

        Args:
            encounter: Encounter instance to check
            session: Optional database session

        Returns:
            Updated Encounter instance
        """

        async def _execute(sess: AsyncSession):
            # Refresh encounter with NPCs
            await sess.refresh(encounter, ["npcs"])

            if not encounter.npcs:
                return encounter

            if not encounter.dead_npcs:
                encounter.dead_npcs = []

            # Check each NPC and mark as dead if incapacitated
            for npc in encounter.npcs:
                if npc.is_incapacitated and npc.id not in encounter.dead_npcs:
                    encounter.dead_npcs.append(npc.id)

            if encounter.dead_npcs:
                sess.add(encounter)
                await sess.commit()
                await sess.refresh(encounter)

            return encounter

        return await self._with_session(_execute, session)

    async def mark_npc_searched(
        self, encounter: Encounter, npc_id: UUID, session: AsyncSession | None = None
    ) -> Encounter:
        """
        Mark an NPC as searched in an encounter.

        Args:
            encounter: Encounter instance
            npc_id: NPC ID to mark as searched
            session: Optional database session

        Returns:
            Updated Encounter instance
        """

        async def _execute(sess: AsyncSession):
            if not encounter.searched_npcs:
                encounter.searched_npcs = []

            if npc_id not in encounter.searched_npcs:
                encounter.searched_npcs.append(npc_id)
                sess.add(encounter)
                await sess.commit()
                await sess.refresh(encounter)

            return encounter

        return await self._with_session(_execute, session)