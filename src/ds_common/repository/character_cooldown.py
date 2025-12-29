"""
Repository for CharacterCooldown model.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.character_cooldown import CharacterCooldown, CooldownType
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterCooldownRepository(BaseRepository[CharacterCooldown]):
    """
    Repository for CharacterCooldown model with cooldown-specific queries.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, CharacterCooldown)

    async def get_by_character(
        self, character_id: UUID, session: AsyncSession | None = None
    ) -> list[CharacterCooldown]:
        """
        Get all cooldowns for a character.

        Args:
            character_id: Character ID
            session: Optional database session

        Returns:
            List of CharacterCooldown instances
        """
        async with self.postgres_manager.get_session() as sess:
            if session:
                sess = session
            stmt = select(CharacterCooldown).where(CharacterCooldown.character_id == character_id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

    async def get_active(
        self,
        character_id: UUID,
        current_game_time: datetime,
        session: AsyncSession | None = None,
    ) -> list[CharacterCooldown]:
        """
        Get all active (non-expired) cooldowns for a character.

        Args:
            character_id: Character ID
            current_game_time: Current game time to compare against
            session: Optional database session

        Returns:
            List of active CharacterCooldown instances
        """
        async with self.postgres_manager.get_session() as sess:
            if session:
                sess = session
            stmt = (
                select(CharacterCooldown)
                .where(CharacterCooldown.character_id == character_id)
                .where(CharacterCooldown.expires_at_game_time > current_game_time)
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

    async def get_by_type_and_name(
        self,
        character_id: UUID,
        cooldown_type: CooldownType,
        cooldown_name: str,
        session: AsyncSession | None = None,
    ) -> CharacterCooldown | None:
        """
        Get a specific cooldown by type and name.

        Args:
            character_id: Character ID
            cooldown_type: Type of cooldown
            cooldown_name: Name of the cooldown
            session: Optional database session

        Returns:
            CharacterCooldown instance or None
        """
        async with self.postgres_manager.get_session() as sess:
            if session:
                sess = session
            stmt = (
                select(CharacterCooldown)
                .where(CharacterCooldown.character_id == character_id)
                .where(CharacterCooldown.cooldown_type == cooldown_type)
                .where(CharacterCooldown.cooldown_name == cooldown_name)
            )
            result = await sess.execute(stmt)
            return result.scalar_one_or_none()

    async def delete_expired(
        self,
        character_id: UUID,
        current_game_time: datetime,
        session: AsyncSession | None = None,
    ) -> int:
        """
        Delete all expired cooldowns for a character.

        Args:
            character_id: Character ID
            current_game_time: Current game time to compare against
            session: Optional database session

        Returns:
            Number of cooldowns deleted
        """

        async def _delete(sess: AsyncSession) -> int:
            stmt = (
                select(CharacterCooldown)
                .where(CharacterCooldown.character_id == character_id)
                .where(CharacterCooldown.expires_at_game_time <= current_game_time)
            )
            result = await sess.execute(stmt)
            expired = list(result.scalars().all())
            count = len(expired)
            for cooldown in expired:
                await sess.delete(cooldown)
            await sess.commit()
            return count

        if session:
            return await _delete(session)
        async with self.postgres_manager.get_session() as sess:
            return await _delete(sess)

    async def delete_by_item_instance(
        self,
        character_id: UUID,
        item_instance_id: str,
        session: AsyncSession | None = None,
    ) -> int:
        """
        Delete all cooldowns for a specific item instance.

        Args:
            character_id: Character ID
            item_instance_id: Item instance ID
            session: Optional database session

        Returns:
            Number of cooldowns deleted
        """

        async def _delete(sess: AsyncSession) -> int:
            stmt = (
                select(CharacterCooldown)
                .where(CharacterCooldown.character_id == character_id)
                .where(CharacterCooldown.cooldown_type == "ITEM")
                .where(CharacterCooldown.cooldown_name == item_instance_id)
            )
            result = await sess.execute(stmt)
            cooldowns = list(result.scalars().all())
            count = len(cooldowns)
            for cooldown in cooldowns:
                await sess.delete(cooldown)
            await sess.commit()
            return count

        if session:
            return await _delete(session)
        async with self.postgres_manager.get_session() as sess:
            return await _delete(sess)

    async def delete_by_item_name(
        self,
        character_id: UUID,
        item_name: str,
        session: AsyncSession | None = None,
    ) -> int:
        """
        Delete all cooldowns for items with a specific name.

        Args:
            character_id: Character ID
            item_name: Item name
            session: Optional database session

        Returns:
            Number of cooldowns deleted
        """

        async def _delete(sess: AsyncSession) -> int:
            stmt = (
                select(CharacterCooldown)
                .where(CharacterCooldown.character_id == character_id)
                .where(CharacterCooldown.cooldown_type == "ITEM")
                # Match items by name (cooldown_name might be instance_id or item name)
            )
            result = await sess.execute(stmt)
            # Filter in Python since we need to check if cooldown_name matches item_name
            # This is a limitation - ideally we'd store item_name separately
            # For now, we'll match by exact name match
            cooldowns = [c for c in result.scalars().all() if c.cooldown_name == item_name]
            count = len(cooldowns)
            for cooldown in cooldowns:
                await sess.delete(cooldown)
            await sess.commit()
            return count

        if session:
            return await _delete(session)
        async with self.postgres_manager.get_session() as sess:
            return await _delete(sess)
