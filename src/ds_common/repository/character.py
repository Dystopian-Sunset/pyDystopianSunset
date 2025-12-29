import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.combat import (
    calculate_max_armor,
    calculate_max_health,
    calculate_max_stamina,
    calculate_max_tech_power,
    catch_up_restoration,
)
from ds_common.combat.experience_service import (
    add_experience as add_exp,
)
from ds_common.combat.experience_service import (
    apply_level_up,
)
from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterRepository(BaseRepository[Character]):
    """
    Repository for Character model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, Character)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def update(
        self, model: Character, session: AsyncSession | None = None, silent: bool = False
    ) -> Character:
        """
        Update a character, with option to skip debug logging.

        Args:
            model: Character instance to update
            session: Optional database session
            silent: If True, skip debug logging (for updates that don't change meaningful data)

        Returns:
            Updated Character instance
        """
        if silent:
            # Temporarily disable the base repository's logger to suppress debug messages
            base_logger = logging.getLogger("ds_common.repository.base_repository")
            original_level = base_logger.level
            base_logger.setLevel(logging.WARNING)
            try:
                result = await super().update(model, session=session)
            finally:
                base_logger.setLevel(original_level)
            return result
        result = await super().update(model, session=session)
        return result

    async def get_character_class(
        self, character: Character, session: AsyncSession | None = None
    ) -> CharacterClass | None:
        """
        Get the character class for a character.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            CharacterClass instance or None
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(character, ["character_class"])
                return character.character_class
            fresh_character = await sess.get(Character, character.id)
            if not fresh_character:
                return None
            await sess.refresh(fresh_character, ["character_class"])
            return fresh_character.character_class

        return await self._with_session(_execute, session, read_only=True)

    async def set_character_class(
        self,
        character: Character,
        character_class: CharacterClass,
        session: AsyncSession | None = None,
    ) -> None:
        """
        Set the character class for a character.

        Args:
            character: Character instance
            character_class: CharacterClass instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            if session:
                character.character_class_id = character_class.id
                sess.add(character)
            else:
                fresh_character = await sess.get(Character, character.id)
                if fresh_character:
                    fresh_character.character_class_id = character_class.id
                    sess.add(fresh_character)
            await sess.commit()

        await self._with_session(_execute, session, read_only=False)
        self.logger.debug(f"Character class set: {character_class}")

    async def get_player(
        self, character: Character, session: AsyncSession | None = None
    ) -> Player | None:
        """
        Get the player who owns this character.

        Note: Returns the first player if character belongs to multiple players.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            Player instance or None
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(character, ["players"])
                players = character.players or []
                return players[0] if players else None
            fresh_character = await sess.get(Character, character.id)
            if not fresh_character:
                return None
            await sess.refresh(fresh_character, ["players"])
            players = fresh_character.players or []
            return players[0] if players else None

        return await self._with_session(_execute, session, read_only=True)

    async def get_game_session(
        self, character: Character, session: AsyncSession | None = None
    ) -> GameSession | None:
        """
        Get the game session this character is playing in.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            GameSession instance or None
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(character, ["game_sessions"])
                game_sessions = character.game_sessions or []
            else:
                fresh_character = await sess.get(Character, character.id)
                if not fresh_character:
                    return None
                await sess.refresh(fresh_character, ["game_sessions"])
                game_sessions = fresh_character.game_sessions or []
            return game_sessions[0] if game_sessions else None

        return await self._with_session(_execute, session, read_only=True)

    async def initialize_combat_resources(
        self, character: Character, session: AsyncSession | None = None
    ) -> Character:
        """
        Calculate and set max resources on character creation/level up.
        Includes equipment bonuses if items are equipped.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            Updated Character instance
        """
        from ds_common.equipment.effect_calculator import (
            _get_equipped_item_templates,
            calculate_resource_bonuses,
        )

        character_class = await self.get_character_class(character, session=session)

        # Get equipped item templates
        equipped_templates = await _get_equipped_item_templates(character, self.postgres_manager)

        # Calculate equipment resource bonuses
        equipment_resource_bonuses = calculate_resource_bonuses(character, equipped_templates)

        # Calculate max resources with equipment bonuses
        character.max_health = calculate_max_health(
            character, character_class, equipment_resource_bonuses
        )
        character.max_stamina = calculate_max_stamina(
            character, character_class, equipment_resource_bonuses
        )
        character.max_tech_power = calculate_max_tech_power(
            character, character_class, equipment_resource_bonuses
        )
        character.max_armor = calculate_max_armor(
            character, character_class, equipment_resource_bonuses
        )

        # Set current resources to max if not already set
        if character.current_health == 0.0:
            character.current_health = character.max_health
        if character.current_stamina == 0.0:
            character.current_stamina = character.max_stamina
        if character.current_tech_power == 0.0:
            character.current_tech_power = character.max_tech_power
        if character.current_armor == 0.0:
            character.current_armor = character.max_armor

        # Set last_resource_update if not set
        if not character.last_resource_update:
            character.last_resource_update = datetime.now(UTC)

        return await self.update(character, session=session)

    async def update_combat_resources(
        self, character: Character, updates: dict, session: AsyncSession | None = None
    ) -> Character:
        """
        Update combat resources safely.

        Args:
            character: Character instance
            updates: Dictionary with resource updates (e.g., {"current_health": 50.0})
            session: Optional database session

        Returns:
            Updated Character instance
        """
        for key, value in updates.items():
            if hasattr(character, key):
                setattr(character, key, value)

        return await self.update(character, session=session)

    async def catch_up_restoration_on_session_start(
        self, character: Character, session: AsyncSession | None = None
    ) -> Character:
        """
        Calculate and apply restoration when player joins session.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            Updated Character instance
        """
        if not character.last_resource_update:
            character.last_resource_update = datetime.now(UTC)
            return await self.update(character, session=session)

        # Check if character is already at full resources
        is_at_full_resources = (
            character.current_health >= character.max_health
            and character.current_stamina >= character.max_stamina
            and character.current_tech_power >= character.max_tech_power
            and character.current_armor >= character.max_armor
        )

        # Calculate actual elapsed time since last update
        # IMPORTANT: We use the actual elapsed time, not an assumed interval
        # This ensures accurate restoration even with timing variance
        now = datetime.now(UTC)
        elapsed_seconds = (now - character.last_resource_update).total_seconds()

        # If character is at full resources, skip restoration calculation entirely
        # (restoration can only increase resources, so if already at max, nothing will change)
        if is_at_full_resources:
            # No need to update - character is already at full resources
            # Skip database write to avoid unnecessary updates and log messages
            return character

        # Store original resource values to check if anything changed
        original_health = character.current_health
        original_stamina = character.current_stamina
        original_tech_power = character.current_tech_power
        original_armor = character.current_armor

        # Apply catch-up restoration using actual elapsed time
        # The catch_up_restoration function calculates the actual time difference and uses it
        result = catch_up_restoration(character, character.last_resource_update)

        # Check if any resources were actually restored (use small tolerance for floating point)
        # Only consider it changed if the difference is meaningful (> 0.01)
        tolerance = 0.01
        resources_changed = (
            abs(character.current_health - original_health) > tolerance
            or abs(character.current_stamina - original_stamina) > tolerance
            or abs(character.current_tech_power - original_tech_power) > tolerance
            or abs(character.current_armor - original_armor) > tolerance
        )

        # Only update database if resources actually changed
        # This avoids unnecessary database writes when character is at full health/stats
        if resources_changed:
            # Update last_resource_update to now
            character.last_resource_update = datetime.now(UTC)
            return await self.update(character, session=session)
        # Nothing changed - skip database write entirely to avoid unnecessary updates
        # We don't update last_resource_update either since nothing changed.
        # This prevents log spam when characters are at full health/stats.
        # The next time this is called, it will recalculate, but if still at full,
        # it will skip again.
        return character

    async def get_equipped_items(
        self, character: Character, session: AsyncSession | None = None
    ) -> dict[str, dict]:
        """
        Get all equipped items for a character.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            Dictionary mapping slot names to item dicts
        """
        if not character.equipped_items:
            return {}

        equipped = {}
        inventory = character.inventory or []

        for slot, instance_id in character.equipped_items.items():
            if instance_id:
                # Find item in inventory by instance_id
                for item in inventory:
                    if isinstance(item, dict) and item.get("instance_id") == instance_id:
                        equipped[slot] = item
                        break

        return equipped

    async def equip_item(
        self,
        character: Character,
        item_instance_id: str,
        slot: str,
        session: AsyncSession | None = None,
    ) -> Character:
        """
        Equip an item from inventory to a slot.

        Args:
            character: Character instance
            item_instance_id: UUID string of the item instance
            slot: Equipment slot name
            session: Optional database session

        Returns:
            Updated Character instance
        """

        from ds_common.equipment.validation import validate_item_slot_compatibility
        from ds_common.repository.item_template import ItemTemplateRepository

        inventory = character.inventory or []
        equipped_items = character.equipped_items or {}

        # Find item in inventory
        item = None
        item_index = None
        for idx, inv_item in enumerate(inventory):
            if isinstance(inv_item, dict) and inv_item.get("instance_id") == item_instance_id:
                item = inv_item
                item_index = idx
                break

        if not item:
            raise ValueError(f"Item {item_instance_id} not found in inventory")

        # Get item template if available
        item_template_id = item.get("item_template_id")
        if item_template_id:
            template_repo = ItemTemplateRepository(self.postgres_manager)
            template = await template_repo.get_by_id(item_template_id)
            if template:
                # Validate slot compatibility
                if not validate_item_slot_compatibility(template, slot):
                    raise ValueError(f"Item {template.name} cannot be equipped to slot {slot}")

        # Unequip existing item in slot if any
        existing_instance_id = equipped_items.get(slot)
        if existing_instance_id:
            await self.unequip_item(character, slot, session=session)
            # Refresh character after unequip
            character = await self.get_by_id(character.id, session=session)
            if not character:
                raise ValueError("Character not found after unequip")
            inventory = character.inventory or []
            equipped_items = character.equipped_items or {}
            # Re-find item after refresh
            for idx, inv_item in enumerate(inventory):
                if isinstance(inv_item, dict) and inv_item.get("instance_id") == item_instance_id:
                    item = inv_item
                    item_index = idx
                    break

        # Update item in inventory
        item["equipped"] = True
        item["equipment_slot"] = slot
        inventory[item_index] = item

        # Update equipped_items dict
        equipped_items[slot] = item_instance_id

        character.inventory = inventory
        character.equipped_items = equipped_items

        # Recalculate resources with new equipment
        character = await self.recalculate_resources_with_equipment(character, session=session)

        return character

    async def unequip_item(
        self,
        character: Character,
        slot: str,
        session: AsyncSession | None = None,
    ) -> Character:
        """
        Unequip an item from a slot.

        Args:
            character: Character instance
            slot: Equipment slot name
            session: Optional database session

        Returns:
            Updated Character instance
        """
        equipped_items = character.equipped_items or {}
        instance_id = equipped_items.get(slot)

        if not instance_id:
            # Nothing equipped in this slot
            return character

        inventory = character.inventory or []

        # Find and update item in inventory
        for idx, item in enumerate(inventory):
            if isinstance(item, dict) and item.get("instance_id") == instance_id:
                item["equipped"] = False
                item["equipment_slot"] = None
                inventory[idx] = item
                break

        # Remove from equipped_items
        del equipped_items[slot]

        character.inventory = inventory
        character.equipped_items = equipped_items

        # Recalculate resources without this equipment
        character = await self.recalculate_resources_with_equipment(character, session=session)

        return character

    async def recalculate_resources_with_equipment(
        self, character: Character, session: AsyncSession | None = None
    ) -> Character:
        """
        Recalculate max resources including equipment bonuses.

        Args:
            character: Character instance
            session: Optional database session

        Returns:
            Updated Character instance with recalculated resources
        """
        from ds_common.equipment.effect_calculator import (
            _get_equipped_item_templates,
            calculate_resource_bonuses,
        )

        character_class = await self.get_character_class(character, session=session)

        # Get equipped item templates
        equipped_templates = await _get_equipped_item_templates(character, self.postgres_manager)

        # Calculate equipment resource bonuses
        equipment_resource_bonuses = calculate_resource_bonuses(character, equipped_templates)

        # Recalculate max resources with equipment bonuses
        character.max_health = calculate_max_health(
            character, character_class, equipment_resource_bonuses
        )
        character.max_stamina = calculate_max_stamina(
            character, character_class, equipment_resource_bonuses
        )
        character.max_tech_power = calculate_max_tech_power(
            character, character_class, equipment_resource_bonuses
        )
        character.max_armor = calculate_max_armor(
            character, character_class, equipment_resource_bonuses
        )

        # Cap current resources at new max values
        character.current_health = min(character.current_health, character.max_health)
        character.current_stamina = min(character.current_stamina, character.max_stamina)
        character.current_tech_power = min(character.current_tech_power, character.max_tech_power)
        character.current_armor = min(character.current_armor, character.max_armor)

        return await self.update(character, session=session)

    async def add_experience(
        self, character: Character, exp_amount: int, session: AsyncSession | None = None
    ) -> tuple[Character, bool]:
        """
        Add experience to a character and check for level ups.

        Args:
            character: Character to add experience to
            exp_amount: Amount of experience to add
            session: Optional database session

        Returns:
            Tuple of (updated_character, leveled_up)
            - updated_character: Character with updated exp (and level if leveled up)
            - leveled_up: True if character leveled up, False otherwise
        """
        character, leveled_up = add_exp(character, exp_amount)

        # If leveled up, apply level up benefits
        if leveled_up:
            character = apply_level_up(character)
            # Recalculate resources with new stats
            character = await self.initialize_combat_resources(character, session=session)
            # Restore current resources to max after level up
            character.current_health = character.max_health
            character.current_stamina = character.max_stamina
            character.current_tech_power = character.max_tech_power
            character.current_armor = character.max_armor

        character = await self.update(character, session=session)
        return character, leveled_up

    async def level_up(
        self, character: Character, session: AsyncSession | None = None
    ) -> Character:
        """
        Apply level up benefits to a character.

        This method applies stat increases and recalculates resources.
        Note: This is typically called automatically by add_experience,
        but can be called manually if needed.

        Args:
            character: Character that leveled up
            session: Optional database session

        Returns:
            Updated Character instance with level up benefits applied
        """
        character = apply_level_up(character)

        # Recalculate resources with new stats
        character = await self.initialize_combat_resources(character, session=session)

        # Restore current resources to max
        character.current_health = character.max_health
        character.current_stamina = character.max_stamina
        character.current_tech_power = character.max_tech_power
        character.current_armor = character.max_armor

        return await self.update(character, session=session)
