import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

import discord
from discord.ui import Button, View

if TYPE_CHECKING:
    from ds_common.models.game_settings import GameSettings

from ds_common.models.character import Character
from ds_common.repository.character import CharacterRepository
from ds_common.repository.character_class import CharacterClassRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterResetConfirmationView(View):
    """View for confirming character reset."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        character: Character,
        game_settings: "GameSettings | Any | None" = None,
    ):
        super().__init__(timeout=300)
        self.postgres_manager = postgres_manager
        self.character = character
        self.game_settings = game_settings
        self.logger: logging.Logger = logging.getLogger(__name__)

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger, row=0)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        """Confirm character reset and proceed to stats reroll."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Check if character is in a game session
        character_repo = CharacterRepository(self.postgres_manager)
        game_session = await character_repo.get_game_session(self.character)
        if game_session:
            await interaction.followup.send(
                "❌ You cannot reset a character while in a game session. "
                "Please leave the session with `/game end` first.",
                ephemeral=True,
            )
            return

        # Get character class
        character_repo = CharacterRepository(self.postgres_manager)
        character_class = await character_repo.get_character_class(self.character)
        if not character_class:
            await interaction.followup.send(
                "❌ Character class not found. Cannot reset character.",
                ephemeral=True,
            )
            return

        # Generate initial stats for reset
        from ds_discord_bot.extensions.views.character_confirmation import (
            create_character_confirmation_embed,
            generate_random_stats,
        )

        character_class_repo = CharacterClassRepository(self.postgres_manager)
        primary_stats_list = await character_class_repo.get_stats(character_class)
        primary_stats = [stat.abbr for stat in primary_stats_list]
        initial_stats = generate_random_stats(
            primary_stats=primary_stats, game_settings=self.game_settings
        )

        # Create reset confirmation view (reuse CharacterConfirmationView but in reset mode)
        reset_view = CharacterResetStatsView(
            postgres_manager=self.postgres_manager,
            character=self.character,
            character_class_id=character_class.id,
            initial_stats=initial_stats,
            game_settings=self.game_settings,
        )

        embed = await create_character_confirmation_embed(
            postgres_manager=self.postgres_manager,
            character_name=self.character.name,
            character_class=character_class,
            stats=initial_stats,
            gender=self.character.gender,
            reroll_count=0,
            max_rerolls=self.game_settings.character_stats_max_rerolls if self.game_settings else 3,
        )
        embed.title = "🔄 Character Reset - Step 1 of 2"
        embed.description = (
            "**Character Reset**\n\n"
            "You are about to reset your character's stats. This will:\n"
            "• Generate new random stats based on your character class\n"
            "• Reset your character to level 1\n"
            "• Reset experience to 0\n"
            "• Reset credits to starting amount (100 quill)\n"
            "• Keep your character name, gender, and class\n"
            "• Keep your inventory and equipment\n\n"
            "**This action cannot be undone.**\n\n"
            "Review your new stats below. You can re-roll them if you're not satisfied."
        )

        await interaction.followup.send(embed=embed, view=reset_view, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=0)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        """Cancel character reset."""
        await interaction.response.send_message("Character reset cancelled.", ephemeral=True)


class CharacterResetStatsView(View):
    """View for resetting character stats (reuses CharacterConfirmationView logic)."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        character: Character,
        character_class_id: UUID,
        initial_stats: dict[str, int],
        game_settings: "GameSettings | Any | None" = None,
    ):
        super().__init__(timeout=300)
        self.postgres_manager = postgres_manager
        self.character = character
        self.character_class_id = character_class_id
        self.game_settings = game_settings
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.stats = initial_stats
        self.reroll_count = 0

        # Load max rerolls from game_settings (DB) or fallback to config
        if game_settings:
            self.max_rerolls = game_settings.character_stats_max_rerolls
        else:
            from ds_common.config_bot import get_config

            config = get_config()
            self.max_rerolls = config.character_stats_max_rerolls

        self.message: discord.Message | None = None
        self._update_reroll_button_label()

    def _update_reroll_button_label(self):
        """Update the re-roll button label based on remaining rerolls."""
        for item in self.children:
            if isinstance(item, Button) and hasattr(item, "emoji") and item.emoji:
                emoji_str = str(item.emoji) if hasattr(item.emoji, "__str__") else None
                if emoji_str == "🎲" or (hasattr(item.emoji, "name") and item.emoji.name == "🎲"):
                    remaining = self.max_rerolls - self.reroll_count
                    if remaining > 0:
                        item.label = f"Re-roll Stats ({remaining} left)"
                    else:
                        item.label = "Re-roll Stats (No rerolls left)"
                        item.disabled = True
                    break

    async def _generate_stats_with_class_weighting(self) -> dict[str, int]:
        """Generate stats weighted by character class primary stats."""
        from ds_discord_bot.extensions.views.character_confirmation import (
            generate_random_stats,
        )

        character_class_repo = CharacterClassRepository(self.postgres_manager)
        character_class = await character_class_repo.get_by_id(self.character_class_id)

        if not character_class:
            return generate_random_stats(game_settings=self.game_settings)

        primary_stats_list = await character_class_repo.get_stats(character_class)
        primary_stats = [stat.abbr for stat in primary_stats_list]

        return generate_random_stats(primary_stats=primary_stats, game_settings=self.game_settings)

    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed with current stats."""
        from ds_discord_bot.extensions.views.character_confirmation import (
            create_character_confirmation_embed,
        )

        character_repo = CharacterRepository(self.postgres_manager)
        character_class = await character_repo.get_character_class(self.character)

        if not character_class:
            await interaction.response.send_message("❌ Character class not found.", ephemeral=True)
            return

        embed = await create_character_confirmation_embed(
            postgres_manager=self.postgres_manager,
            character_name=self.character.name,
            character_class=character_class,
            stats=self.stats,
            gender=self.character.gender,
            reroll_count=self.reroll_count,
            max_rerolls=self.max_rerolls,
        )
        embed.title = "🔄 Character Reset - Step 1 of 2"

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Re-roll Stats",
        style=discord.ButtonStyle.secondary,
        row=1,
        emoji="🎲",
    )
    async def reroll_stats(self, interaction: discord.Interaction, button: Button):
        """Re-roll character stats."""
        if self.reroll_count >= self.max_rerolls:
            await interaction.response.send_message(
                f"❌ You've used all {self.max_rerolls} re-rolls. Please confirm or cancel.",
                ephemeral=True,
            )
            return

        self.stats = await self._generate_stats_with_class_weighting()
        self.reroll_count += 1
        self._update_reroll_button_label()
        await self.update_embed(interaction)

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.success, row=0)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        """Confirm and reset the character."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        character_repo = CharacterRepository(self.postgres_manager)
        character_class_repo = CharacterClassRepository(self.postgres_manager)

        try:
            # Get fresh character data
            character = await character_repo.get_by_id(self.character.id)
            if not character:
                await interaction.followup.send(
                    "❌ Character not found. Reset cancelled.",
                    ephemeral=True,
                )
                return

            # Check if character is in a game session (double-check)
            game_session = await character_repo.get_game_session(character)
            if game_session:
                await interaction.followup.send(
                    "❌ You cannot reset a character while in a game session. "
                    "Please leave the session with `/game end` first.",
                    ephemeral=True,
                )
                return

            # Reset character stats and level
            character.stats = self.stats.copy()
            character.level = 1
            character.exp = 0
            character.credits = 100  # Reset to starting credits
            character.renown = 0  # Reset renown
            character.shadow_level = 0  # Reset shadow level

            # Reset inventory and equipment to starting equipment
            import uuid

            from sqlmodel import select

            from ds_common.models.junction_tables import CharacterClassStartingEquipment
            from ds_common.repository.item_template import ItemTemplateRepository

            # Get character class
            character_class = await character_repo.get_character_class(character)

            if character_class:
                template_repo = ItemTemplateRepository(self.postgres_manager)

                # Get starting equipment for this class
                async with self.postgres_manager.get_session() as sess:
                    stmt = select(CharacterClassStartingEquipment).where(
                        CharacterClassStartingEquipment.character_class_id == character_class.id
                    )
                    result = await sess.execute(stmt)
                    starting_equipment = result.scalars().all()

                # Create new inventory with starting equipment
                inventory = []
                equipped_items = {}

                for starting_eq in starting_equipment:
                    template = await template_repo.get_by_id(starting_eq.item_template_id)
                    if not template:
                        continue

                    # Create item instance
                    for _ in range(starting_eq.quantity):
                        instance_id = str(uuid.uuid4())
                        item_instance = {
                            "instance_id": instance_id,
                            "item_template_id": str(template.id),
                            "name": template.name,
                            "quantity": 1,
                            "equipped": True,
                            "equipment_slot": starting_eq.equipment_slot,
                        }
                        inventory.append(item_instance)

                        # Update equipped_items dict
                        equipped_items[starting_eq.equipment_slot] = instance_id

                character.inventory = inventory
                character.equipped_items = equipped_items
            else:
                # If no character class, clear inventory
                character.inventory = []
                character.equipped_items = {}

            # Update character
            await character_repo.update(character)

            # Refresh to get latest data
            character = await character_repo.get_by_id(character.id)
            if not character:
                raise ValueError("Character not found after reset")

            # Reinitialize combat resources with new stats
            character = await character_repo.initialize_combat_resources(character)

            # Create success embed
            from ds_discord_bot.extensions.views.character_widget import CharacterWidget

            character_class = await character_repo.get_character_class(character)
            embed = CharacterWidget(
                character=character,
                character_class=character_class,
                is_active=True,
            )
            embed.title = "✅ Character Reset Successfully!"
            embed.description = (
                f"{character.name} has been reset to level 1 with new stats. "
                "Inventory and equipment have been reset to starting equipment."
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error in character reset: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while resetting your character. Please try again later.",
                ephemeral=True,
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=0)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        """Cancel character reset."""
        await interaction.response.send_message("Character reset cancelled.", ephemeral=True)
