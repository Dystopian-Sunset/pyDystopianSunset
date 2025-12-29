import logging
import random
from typing import TYPE_CHECKING, Any
from uuid import UUID

import discord
from discord.ui import Button, View

if TYPE_CHECKING:
    from ds_common.models.game_settings import GameSettings

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.repository.character import CharacterRepository
from ds_common.repository.character_class import CharacterClassRepository
from ds_common.repository.item_template import ItemTemplateRepository
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.postgres_manager import PostgresManager


def generate_random_stats(
    primary_stats: list[str] | None = None,
    total_pool_min: int | None = None,
    total_pool_max: int | None = None,
    primary_weight: float | None = None,
    secondary_weight: float | None = None,
    luck_min: int | None = None,
    luck_max: int | None = None,
    stat_min: int | None = None,
    stat_max: int | None = None,
    allocation_variance: int | None = None,
    game_settings: "GameSettings | Any | None" = None,
) -> dict[str, int]:
    """
    Generate random stats for a character with weighted distribution favoring primary stats.

    Uses a point pool system with configurable parameters.
    All parameters can be overridden, but will default to game_settings (DB) values if not provided.

    Args:
        primary_stats: List of stat abbreviations that are primary for the class (e.g., ["STR", "DEX"])
        total_pool_min: Minimum total stat points (defaults to game_settings)
        total_pool_max: Maximum total stat points (defaults to game_settings)
        primary_weight: Weight multiplier for primary stats (defaults to game_settings)
        secondary_weight: Weight multiplier for secondary stats (defaults to game_settings)
        luck_min: Minimum luck value (defaults to game_settings)
        luck_max: Maximum luck value (defaults to game_settings)
        stat_min: Minimum value for any stat (defaults to game_settings)
        stat_max: Maximum value for any stat (defaults to game_settings)
        allocation_variance: Variance in point allocation (defaults to game_settings)
        game_settings: GameSettings instance (optional, will fallback to config if not provided)

    Returns:
        Dictionary of stat values
    """
    if primary_stats is None:
        primary_stats = []

    # Use game_settings defaults if not provided, fallback to config for backwards compatibility
    if game_settings:
        total_pool_min = (
            total_pool_min if total_pool_min is not None else game_settings.character_stats_pool_min
        )
        total_pool_max = (
            total_pool_max if total_pool_max is not None else game_settings.character_stats_pool_max
        )
        primary_weight = (
            primary_weight
            if primary_weight is not None
            else game_settings.character_stats_primary_weight
        )
        secondary_weight = (
            secondary_weight
            if secondary_weight is not None
            else game_settings.character_stats_secondary_weight
        )
        luck_min = luck_min if luck_min is not None else game_settings.character_stats_luck_min
        luck_max = luck_max if luck_max is not None else game_settings.character_stats_luck_max
        stat_min = stat_min if stat_min is not None else game_settings.character_stats_stat_min
        stat_max = stat_max if stat_max is not None else game_settings.character_stats_stat_max
        allocation_variance = (
            allocation_variance
            if allocation_variance is not None
            else game_settings.character_stats_allocation_variance
        )
    else:
        # Fallback to config for backwards compatibility (shouldn't happen in normal flow)
        from ds_common.config_bot import get_config

        config = get_config()
        total_pool_min = (
            total_pool_min if total_pool_min is not None else config.character_stats_pool_min
        )
        total_pool_max = (
            total_pool_max if total_pool_max is not None else config.character_stats_pool_max
        )
        primary_weight = (
            primary_weight if primary_weight is not None else config.character_stats_primary_weight
        )
        secondary_weight = (
            secondary_weight
            if secondary_weight is not None
            else config.character_stats_secondary_weight
        )
        luck_min = luck_min if luck_min is not None else config.character_stats_luck_min
        luck_max = luck_max if luck_max is not None else config.character_stats_luck_max
        stat_min = stat_min if stat_min is not None else config.character_stats_stat_min
        stat_max = stat_max if stat_max is not None else config.character_stats_stat_max
        allocation_variance = (
            allocation_variance
            if allocation_variance is not None
            else config.character_stats_allocation_variance
        )

    # All stat names
    all_stats = ["STR", "DEX", "INT", "PER", "CHA", "LUK"]

    # Determine total stat pool
    total_pool = random.randint(total_pool_min, total_pool_max)

    # Set minimum values (stat_min for all stats, Luck gets separate range)
    stats = dict.fromkeys(all_stats, stat_min)

    # Luck gets a separate allocation
    luck_points = random.randint(luck_min, luck_max)
    stats["LUK"] = luck_points
    remaining_pool = (
        total_pool - (len(all_stats) - 1) * stat_min - luck_points
    )  # Subtract base mins and luck

    # Create weighted distribution
    # Primary stats get primary_weight, others get secondary_weight
    weights = {}
    for stat in all_stats:
        if stat == "LUK":
            continue  # Already allocated
        if stat in primary_stats:
            weights[stat] = primary_weight
        else:
            weights[stat] = secondary_weight

    # Calculate total weight
    total_weight = sum(weights.values())

    # Distribute remaining points
    stats_to_allocate = [s for s in all_stats if s != "LUK"]
    random.shuffle(stats_to_allocate)  # Randomize order for variety

    for stat in stats_to_allocate:
        if remaining_pool <= 0:
            break

        # Calculate how many points this stat should get based on weight
        weight = weights[stat]
        proportion = weight / total_weight

        # Allocate points (with some randomness)
        base_allocation = int(remaining_pool * proportion)
        # Add variance (±allocation_variance points)
        variance = random.randint(-allocation_variance, allocation_variance)
        points = max(1, base_allocation + variance)  # At least 1 point

        # Don't exceed remaining pool or max stat value
        points = min(points, remaining_pool, stat_max - stats[stat])
        stats[stat] += points
        remaining_pool -= points

    # Distribute any remaining points randomly
    while remaining_pool > 0:
        stat = random.choice(stats_to_allocate)
        if stats[stat] < stat_max:
            add_points = min(1, remaining_pool, stat_max - stats[stat])
            stats[stat] += add_points
            remaining_pool -= add_points
        else:
            # All stats are maxed, break
            break

    # Ensure all stats are within valid range
    for stat in all_stats:
        stats[stat] = max(stat_min, min(stat_max, stats[stat]))

    return stats


def format_stat_distribution(stats: dict[str, int]) -> str:
    """Format stats for display in embed."""
    stat_order = ["STR", "DEX", "INT", "PER", "CHA", "LUK"]
    stat_emojis = {
        "STR": "💪",
        "DEX": "🤸‍♀️",
        "INT": "🧠",
        "PER": "👁️",
        "CHA": "💬",
        "LUK": "🍀",
    }

    lines = []
    for stat in stat_order:
        value = stats.get(stat, 0)
        emoji = stat_emojis.get(stat, "•")
        lines.append(f"{emoji} **{stat}**: {value}")

    total = sum(stats.values())
    lines.append(f"\n**Total**: {total}/120")

    return "\n".join(lines)


class CharacterConfirmationView(View):
    """View for confirming character creation with summary."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        character_name: str,
        character_class_id: UUID,
        character_creation_channel: discord.TextChannel | None = None,
        initial_stats: dict[str, int] | None = None,
        game_settings: "GameSettings | Any | None" = None,
        selected_gender: str | None = None,
    ):
        super().__init__(timeout=300)
        self.postgres_manager = postgres_manager
        self.character_name = character_name
        self.character_class_id = character_class_id
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings
        self.logger: logging.Logger = logging.getLogger(__name__)

        # Initialize stats (should always be provided, but fallback to unweighted if not)
        if initial_stats is None:
            # Fallback: generate unweighted stats (shouldn't happen in normal flow)
            self.logger.warning("No initial stats provided, generating unweighted stats")
            initial_stats = generate_random_stats(game_settings=game_settings)
        self.stats = initial_stats
        self.reroll_count = 0

        # Set gender from selection (already selected in step 1)
        self.gender = selected_gender

        # Gender is already selected, so we don't need the dropdown anymore
        # But we'll keep it hidden/disabled for reference if needed

        # Load max rerolls from game_settings (DB) or fallback to config
        if game_settings:
            self.max_rerolls = game_settings.character_stats_max_rerolls
        else:
            from ds_common.config_bot import get_config

            config = get_config()
            self.max_rerolls = config.character_stats_max_rerolls

        self.message: discord.Message | None = None

        # Update re-roll button label after all children are added
        # This will be called after the view is fully initialized
        self._update_reroll_button_label()

    def _update_reroll_button_label(self):
        """Update the re-roll button label based on remaining rerolls."""
        # Find the reroll button by checking for the emoji
        for item in self.children:
            if isinstance(item, Button) and hasattr(item, "emoji") and item.emoji:
                # Check if it's the reroll button (has dice emoji)
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
        character_class_repo = CharacterClassRepository(self.postgres_manager)
        character_class = await character_class_repo.get_by_id(self.character_class_id)

        if not character_class:
            # Fallback to unweighted if class not found
            self.logger.warning("Character class not found, generating unweighted stats")
            return generate_random_stats(game_settings=self.game_settings)

        # Get primary stats for this class
        primary_stats_list = await character_class_repo.get_stats(character_class)
        primary_stats = [stat.abbr for stat in primary_stats_list]

        return generate_random_stats(primary_stats=primary_stats, game_settings=self.game_settings)

    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed with current stats."""
        character_class_repo = CharacterClassRepository(self.postgres_manager)
        character_class = await character_class_repo.get_by_id(self.character_class_id)

        if not character_class:
            await interaction.response.send_message("❌ Character class not found.", ephemeral=True)
            return

        embed = await create_character_confirmation_embed(
            postgres_manager=self.postgres_manager,
            character_name=self.character_name,
            character_class=character_class,
            stats=self.stats,
            gender=self.gender,
            reroll_count=self.reroll_count,
            max_rerolls=self.max_rerolls,
        )

        # Update the message
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Re-roll Stats", style=discord.ButtonStyle.secondary, row=1, emoji="🎲"
    )
    async def reroll_stats(self, interaction: discord.Interaction, button: Button):
        """Re-roll character stats."""
        if self.reroll_count >= self.max_rerolls:
            await interaction.response.send_message(
                f"❌ You've used all {self.max_rerolls} re-rolls. Please confirm or cancel.",
                ephemeral=True,
            )
            return

        # Generate new stats with class weighting
        self.stats = await self._generate_stats_with_class_weighting()
        self.reroll_count += 1

        # Update button label
        self._update_reroll_button_label()

        # Update embed
        await self.update_embed(interaction)

    @discord.ui.button(label="Confirm Creation", style=discord.ButtonStyle.success, row=0)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        """Confirm and create the character."""
        # Gender should already be set from step 1, but check just in case
        if not self.gender:
            await interaction.response.send_message(
                "❌ Gender not set. Please start character creation again.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        character = None
        character_repo = CharacterRepository(self.postgres_manager)
        character_class_repo = CharacterClassRepository(self.postgres_manager)
        player_repo = PlayerRepository(self.postgres_manager)

        try:
            # Double-check name availability
            existing_character = await character_repo.get_by_field(
                "name", self.character_name, case_sensitive=False
            )
            if existing_character:
                await interaction.followup.send(
                    f"❌ Character '{self.character_name}' already exists. Please choose a different name.",
                    ephemeral=True,
                )
                return

            character_class = await character_class_repo.get_by_id(self.character_class_id)

            # Create character with the stored stats (not newly generated)
            # IMPORTANT: We generate a character first, then immediately override the stats
            character = Character.generate_character(name=self.character_name)
            # Override the randomly generated stats with our stored stats
            character.stats = self.stats.copy()
            # Set gender
            character.gender = self.gender

            player = await player_repo.get_by_discord_id(interaction.user.id)
            if not player:
                from ds_common.models.player import Player

                player = Player.from_member(interaction.user)
                await player_repo.upsert(player)

            # Save character with the correct stats
            await character_repo.upsert(character)
            # Refresh to ensure we have the saved version
            character = await character_repo.get_by_id(character.id)
            if not character:
                raise ValueError("Character not found after creation")

            # Ensure stats are set (they should be, but double-check)
            character.stats = self.stats.copy()
            await character_repo.set_character_class(character, character_class)

            # Load starting equipment templates for class
            import uuid

            from sqlmodel import select

            from ds_common.models.junction_tables import CharacterClassStartingEquipment

            template_repo = ItemTemplateRepository(self.postgres_manager)

            # Get starting equipment for this class
            async with self.postgres_manager.get_session() as sess:
                stmt = select(CharacterClassStartingEquipment).where(
                    CharacterClassStartingEquipment.character_class_id == character_class.id
                )
                result = await sess.execute(stmt)
                starting_equipment = result.scalars().all()

            # Create item instances and auto-equip
            inventory = character.inventory or []
            equipped_items = character.equipped_items or {}

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
            # Ensure stats are still set before updating (critical: stats must be set before resource calculation)
            character.stats = self.stats.copy()
            await character_repo.update(character)

            # Refresh character from database to ensure we have the latest data with all updates
            character = await character_repo.get_by_id(character.id)
            if not character:
                raise ValueError("Character not found after creation")

            # CRITICAL: Ensure stats are set before initializing resources
            # This ensures the resource calculation uses the correct stats
            character.stats = self.stats.copy()

            # Initialize combat resources after equipment is equipped (includes equipment bonuses)
            # This function calculates resources based on character.stats, so stats must be set above
            character = await character_repo.initialize_combat_resources(character)
            await player_repo.add_character(player, character)

            if await player_repo.get_active_character(player) is None:
                await player_repo.set_active_character(player, character)

            # Create success embed
            from ds_discord_bot.extensions.views.character_widget import CharacterWidget

            character_class = await character_repo.get_character_class(character)
            embed = CharacterWidget(
                character=character,
                character_class=character_class,
                is_active=True,
            )
            embed.title = "✅ Character Created Successfully!"
            embed.description = f"Welcome, {character.name}! Your journey begins now."

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )

            if self.character_creation_channel:
                await self.character_creation_channel.send(
                    f"A new {character_class.name}, {character.name}, has joined the world!"
                )
                self.logger.debug(
                    "Sent character creation announcement to %s",
                    self.character_creation_channel,
                )
            else:
                self.logger.debug("Character creation channel not set, cannot send announcement")

        except Exception as e:
            # Log the error
            self.logger.error(f"Error in character creation: {e}", exc_info=True)

            # Send error message to user
            await interaction.followup.send(
                "❌ An error occurred while creating your character. Please try again later.",
                ephemeral=True,
            )

            # Remove the character if it was created
            if character:
                await character_repo.delete(character.id)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=0)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        """Cancel character creation."""
        await interaction.response.send_message("Character creation cancelled.", ephemeral=True)


async def create_character_confirmation_embed(
    postgres_manager: PostgresManager,
    character_name: str,
    character_class: CharacterClass,
    stats: dict[str, int],
    gender: str | None = None,
    reroll_count: int = 0,
    max_rerolls: int = 3,
) -> discord.Embed:
    """Create an embed showing character creation summary for confirmation."""
    character_class_repo = CharacterClassRepository(postgres_manager)
    template_repo = ItemTemplateRepository(postgres_manager)

    # Get class stats
    class_stats = await character_class_repo.get_stats(character_class)
    stat_names = [stat.abbr for stat in class_stats]

    # Get starting equipment
    from sqlmodel import select

    from ds_common.models.junction_tables import CharacterClassStartingEquipment

    equipment_list = []
    async with postgres_manager.get_session() as sess:
        stmt = select(CharacterClassStartingEquipment).where(
            CharacterClassStartingEquipment.character_class_id == character_class.id
        )
        result = await sess.execute(stmt)
        starting_equipment = result.scalars().all()

        for eq in starting_equipment:
            template = await template_repo.get_by_id(eq.item_template_id)
            if template:
                slot_name = eq.equipment_slot.replace("_", " ").title()
                equipment_list.append(f"• {template.name} ({slot_name})")

    embed = discord.Embed(
        title="📋 Character Creation Summary - Step 4 of 4",
        description="Please review your character details before confirming:",
        color=discord.Color.gold(),
    )

    embed.add_field(name="Character Name", value=character_name, inline=False)
    embed.add_field(
        name="Class",
        value=f"{character_class.emoji} {character_class.name}",
        inline=True,
    )
    if gender:
        embed.add_field(
            name="Gender",
            value=gender,
            inline=True,
        )

    if stat_names:
        embed.add_field(
            name="Primary Stats",
            value=", ".join(stat_names),
            inline=True,
        )

    # Add stat distribution
    stat_distribution = format_stat_distribution(stats)
    embed.add_field(
        name="📊 Stat Distribution",
        value=stat_distribution,
        inline=False,
    )

    if equipment_list:
        embed.add_field(
            name="Starting Equipment",
            value="\n".join(equipment_list) or "None",
            inline=False,
        )

    embed.add_field(
        name="Starting Resources",
        value="• Level: 1\n• Credits: 100 quill",
        inline=False,
    )

    # Add re-roll info to footer
    reroll_info = f"Re-rolls used: {reroll_count}/{max_rerolls}"
    embed.set_footer(text=f"Click 'Confirm Creation' to create your character • {reroll_info}")

    return embed
