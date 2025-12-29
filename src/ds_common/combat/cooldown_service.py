"""
Cooldown service for managing character cooldowns using game time.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from ds_common.memory.game_time_service import GameTimeService
from ds_common.models.character import Character
from ds_common.models.character_cooldown import CharacterCooldown
from ds_common.repository.character_cooldown import CharacterCooldownRepository
from ds_discord_bot.postgres_manager import PostgresManager

CooldownTypeLiteral = Literal["SKILL", "ABILITY", "ITEM"]


class CooldownService:
    """
    Service for managing character cooldowns using game time.
    """

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres_manager = postgres_manager
        self.repository = CharacterCooldownRepository(postgres_manager)
        self.game_time_service = GameTimeService(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def _get_current_game_datetime(self) -> datetime:
        """
        Get current real datetime for cooldown comparison.

        Cooldowns expire based on real time (since game time advances in real time).
        We use the current real datetime as the base for calculating expiry.

        Returns:
            Current real datetime (UTC)
        """
        # Use current real time as base - cooldowns expire in real time
        # based on game time multiplier
        return datetime.now(UTC)

    async def check_cooldown(
        self,
        character: Character,
        cooldown_type: CooldownTypeLiteral,
        cooldown_name: str,
    ) -> bool:
        """
        Check if a cooldown is currently active (not expired).

        Args:
            character: Character to check
            cooldown_type: Type of cooldown (SKILL, ABILITY, ITEM)
            cooldown_name: Name of the cooldown (skill name, ability name, or item instance ID)

        Returns:
            True if cooldown is active (not expired), False otherwise
        """
        current_game_time = await self._get_current_game_datetime()
        cooldown = await self.repository.get_by_type_and_name(
            character.id, cooldown_type, cooldown_name
        )

        if not cooldown:
            return False  # No cooldown exists, so it's not active

        # Check if cooldown has expired
        return cooldown.expires_at_game_time > current_game_time

    async def start_cooldown(
        self,
        character: Character,
        cooldown_type: CooldownTypeLiteral,
        cooldown_name: str,
        duration_game_hours: float,
    ) -> CharacterCooldown:
        """
        Start a cooldown for a character.

        If a cooldown already exists, it will be replaced with the new one.

        Args:
            character: Character to start cooldown for
            cooldown_type: Type of cooldown (SKILL, ABILITY, ITEM)
            cooldown_name: Name of the cooldown (skill name, ability name, or item instance ID)
            duration_game_hours: Duration of cooldown in game hours

        Returns:
            Created CharacterCooldown instance
        """
        current_game_time = await self._get_current_game_datetime()

        # Calculate expiry time
        # We need to convert game hours to real time
        # Get game time multiplier from settings to convert game hours to real time
        from ds_common.repository.game_settings import GameSettingsRepository

        settings_repo = GameSettingsRepository(self.postgres_manager)
        settings = await settings_repo.get_settings()
        time_multiplier = settings.game_time_multiplier  # game hours per real minute

        # Convert game hours to real minutes, then to timedelta
        real_minutes = duration_game_hours / time_multiplier
        real_duration = timedelta(minutes=real_minutes)

        # Expiry time is current game time + duration
        expires_at = current_game_time + real_duration

        # Check if cooldown already exists
        existing = await self.repository.get_by_type_and_name(
            character.id, cooldown_type, cooldown_name
        )

        if existing:
            # Update existing cooldown
            existing.expires_at_game_time = expires_at
            existing.duration_game_hours = duration_game_hours
            existing.updated_at = datetime.now(UTC)
            return await self.repository.update(existing)
        # Create new cooldown
        cooldown = CharacterCooldown(
            character_id=character.id,
            cooldown_type=cooldown_type,
            cooldown_name=cooldown_name,
            expires_at_game_time=expires_at,
            duration_game_hours=duration_game_hours,
        )
        return await self.repository.create(cooldown)

    async def get_active_cooldowns(self, character: Character) -> list[CharacterCooldown]:
        """
        Get all active (non-expired) cooldowns for a character.

        Args:
            character: Character to get cooldowns for

        Returns:
            List of active CharacterCooldown instances
        """
        current_game_time = await self._get_current_game_datetime()
        return await self.repository.get_active(character.id, current_game_time)

    async def get_cooldown_remaining(
        self,
        character: Character,
        cooldown_type: CooldownTypeLiteral,
        cooldown_name: str,
    ) -> float | None:
        """
        Get remaining cooldown time in game hours.

        Args:
            character: Character to check
            cooldown_type: Type of cooldown
            cooldown_name: Name of the cooldown

        Returns:
            Remaining cooldown time in game hours, or None if no active cooldown
        """
        current_game_time = await self._get_current_game_datetime()
        cooldown = await self.repository.get_by_type_and_name(
            character.id, cooldown_type, cooldown_name
        )

        if not cooldown:
            return None

        if cooldown.expires_at_game_time <= current_game_time:
            return None  # Cooldown has expired

        # Calculate remaining time in real time
        remaining_real = cooldown.expires_at_game_time - current_game_time
        remaining_real_hours = remaining_real.total_seconds() / 3600.0

        # Convert to game hours
        from ds_common.repository.game_settings import GameSettingsRepository

        settings_repo = GameSettingsRepository(self.postgres_manager)
        settings = await settings_repo.get_settings()
        time_multiplier = settings.game_time_multiplier  # game hours per real minute
        # Real hours to real minutes, then to game hours
        remaining_game_hours = remaining_real_hours * 60.0 * time_multiplier

        return remaining_game_hours

    async def cleanup_expired_cooldowns(self, character: Character) -> int:
        """
        Remove all expired cooldowns for a character.

        Args:
            character: Character to clean up cooldowns for

        Returns:
            Number of cooldowns removed
        """
        current_game_time = await self._get_current_game_datetime()
        return await self.repository.delete_expired(character.id, current_game_time)

    async def remove_item_cooldowns(self, character: Character, item_instance_id: str) -> int:
        """
        Remove all cooldowns for a specific item instance.

        Args:
            character: Character to remove cooldowns for
            item_instance_id: Item instance ID

        Returns:
            Number of cooldowns removed
        """
        return await self.repository.delete_by_item_instance(character.id, item_instance_id)

    async def remove_item_cooldowns_by_name(self, character: Character, item_name: str) -> int:
        """
        Remove all cooldowns for items with a specific name.

        Args:
            character: Character to remove cooldowns for
            item_name: Item name

        Returns:
            Number of cooldowns removed
        """
        return await self.repository.delete_by_item_name(character.id, item_name)

    async def cleanup_orphaned_cooldowns(self, character: Character) -> int:
        """
        Remove cooldowns for items that no longer exist in inventory.

        Args:
            character: Character to clean up cooldowns for

        Returns:
            Number of orphaned cooldowns removed
        """
        # Get all item cooldowns
        current_game_time = await self._get_current_game_datetime()
        all_cooldowns = await self.repository.get_active(character.id, current_game_time)
        item_cooldowns = [c for c in all_cooldowns if c.cooldown_type == "ITEM"]

        # Get inventory item instance IDs and names
        inventory = character.inventory if character.inventory else []
        inventory_instance_ids = set()
        inventory_names = set()

        for item in inventory:
            if isinstance(item, dict):
                instance_id = item.get("instance_id")
                name = item.get("name")
                if instance_id:
                    inventory_instance_ids.add(instance_id)
                if name:
                    inventory_names.add(name)

        # Find orphaned cooldowns
        orphaned = []
        for cooldown in item_cooldowns:
            # Check if cooldown_name matches any inventory instance_id or name
            if (
                cooldown.cooldown_name not in inventory_instance_ids
                and cooldown.cooldown_name not in inventory_names
            ):
                orphaned.append(cooldown)

        # Delete orphaned cooldowns
        count = 0
        for cooldown in orphaned:
            await self.repository.delete(cooldown)
            count += 1

        return count
