import logging

import discord
from discord import TextChannel, app_commands
from discord.ext import commands

from ds_common.repository.character import CharacterRepository
from ds_common.repository.character_class import CharacterClassRepository
from ds_common.repository.item_template import ItemTemplateRepository
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.extensions.views.character_class_selection import (
    CharacterClassSelectionView,
)
from ds_discord_bot.extensions.views.character_selection import CharacterSelectionView
from ds_discord_bot.extensions.views.character_widget import CharacterWidget
from ds_discord_bot.postgres_manager import PostgresManager


class Character(commands.Cog):
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.postgres_manager: PostgresManager = postgres_manager
        self.character_creation_channel: TextChannel | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        # self.character_creation_channel = await self.bot.get_channel(
        #     "🔥-character-foundry"
        # )

        if self.character_creation_channel:
            self.logger.info(
                f"Character creation channel loaded: {self.character_creation_channel.name} (ID: {self.character_creation_channel.id})"
            )
        else:
            self.logger.error("Character creation channel not found")

        self.logger.info("Character cog loaded")

    character = app_commands.Group(name="character", description="Character commands")

    @character.command(name="create", description="Create a new character to play as")
    @app_commands.describe(quick="Quick create mode")
    async def create_character(self, interaction: discord.Interaction, quick: bool = False):
        await interaction.response.defer(ephemeral=True, thinking=True)

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        if not interaction.user.dm_channel:
            await interaction.user.create_dm()

        characters = await player_repository.get_characters(player)
        max_characters = self.bot.game_settings.max_characters_per_player
        if len(characters) >= max_characters:
            character_list = "\n".join(f"• {c.name}" for c in characters)
            await interaction.response.send_message(
                f"❌ **Character Limit Reached**\n\n"
                f"You have reached the maximum number of characters ({max_characters}).\n\n"
                f"**Your characters:**\n{character_list}\n\n"
                f"To create a new character, delete an existing one first using `/character delete <name>`.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🎭 Character Creation - Step 1 of 4",
            description=(
                "**Welcome to Character Creation!**\n\n"
                "1️⃣ **Select a Class** - Choose from available character classes\n"
                "2️⃣ **Select Gender** - Choose your character's gender (affects pronouns used)\n"
                "3️⃣ **Enter Name** - You'll be prompted for your character's name\n"
                "4️⃣ **Confirm** - Review and confirm your character details\n\n"
                "Your character's class determines their core stats and starting equipment. "
                "As you progress, you'll be able to upgrade your character's stats and abilities."
            ),
            color=discord.Color.orange(),
        )
        embed.set_footer(text="💡 Tip: Use /character classes to see detailed class information")

        # Show class selection first
        character_class_repo = CharacterClassRepository(self.postgres_manager)
        character_classes = await character_class_repo.get_all()

        if not character_classes:
            await interaction.followup.send(
                "❌ **No character classes available**\n\n"
                "Character classes haven't been set up yet. Please contact an administrator to configure character classes.",
                ephemeral=True,
            )
            return

        view = CharacterClassSelectionView(
            postgres_manager=self.postgres_manager,
            character_classes=character_classes,
            character_creation_channel=self.character_creation_channel,
            game_settings=self.bot.game_settings,
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @character.command(name="delete", description="Delete a character")
    @app_commands.describe(name="Character name")
    async def delete_character(self, interaction: discord.Interaction, name: str):
        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        character_repository = CharacterRepository(self.postgres_manager)
        characters = await player_repository.get_characters(player)

        if not characters:
            await interaction.response.send_message(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
        else:
            game_session = await character_repository.get_game_session(characters[0])
            if game_session:
                await interaction.response.send_message(
                    "You are currently in a game session. Please leave it with `/game end` before deleting a character.",
                    ephemeral=True,
                )
                return

            # Find matching character
            matching_character = None
            for character in characters:
                if character.name.lower() == name.lower():
                    matching_character = character
                    break

            if not matching_character:
                await interaction.response.send_message(
                    f"Character {name} not found.", ephemeral=True
                )
                return

            # Show confirmation modal
            from ds_discord_bot.extensions.dialogs.character_deletion_modal import (
                CharacterDeletionModal,
            )

            modal = CharacterDeletionModal(
                postgres_manager=self.postgres_manager,
                character_name=matching_character.name,
            )
            await interaction.response.send_modal(modal)

            await interaction.response.send_message(f"Character {name} not found.", ephemeral=True)

    @character.command(name="list", description="List all your characters")
    async def list_characters(self, interaction: discord.Interaction):
        self.logger.info("Character list: %s", interaction.user)

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        character_repository = CharacterRepository(self.postgres_manager)
        characters = await player_repository.get_characters(player)
        if not characters:
            await interaction.response.send_message(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
        else:
            active_character = await player_repository.get_active_character(player)

            embeds = []
            for character in characters:
                character_class = await character_repository.get_character_class(character)
                embeds.append(
                    CharacterWidget(
                        character=character,
                        character_class=character_class,
                        is_active=character.id == active_character.id,
                    )
                )

            await interaction.response.send_message(
                embeds=embeds,
                ephemeral=True,
            )

    @character.command(name="use", description="Select a character to use as your active character")
    @app_commands.describe(name="Character name")
    async def use_character(self, interaction: discord.Interaction, name: str | None = None):
        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        session = await player_repository.get_game_session(player)
        if session:
            await interaction.response.send_message(
                "You are already in a game session. Please leave it with `/game leave` before switching characters.",
                ephemeral=True,
            )
            return

        max_characters = self.bot.game_settings.max_characters_per_player
        if max_characters == 1:
            await interaction.response.send_message(
                "You can only have one character, it will be used automatically.",
                ephemeral=True,
            )

            characters = await player_repository.get_characters(player)
            await player_repository.set_active_character(player, characters[0])
            return

        if name is None:
            characters = await player_repository.get_characters(player)
            active_character = await player_repository.get_active_character(player)

            if not characters:
                await interaction.response.send_message(
                    "You have no characters. Create one with `/character create`",
                    ephemeral=True,
                )
                return
            if len(characters) == 1:
                await player_repository.set_active_character(player, characters[0])
                await interaction.response.send_message(
                    f"You are now playing as {characters[0].name}", ephemeral=True
                )
                return

            character_repository = CharacterRepository(self.postgres_manager)
            view = CharacterSelectionView(
                postgres_manager=self.postgres_manager,
                characters=[
                    (
                        character,
                        await character_repository.get_character_class(character),
                    )
                    for character in characters
                ],
                active_character=active_character,
                interaction=interaction,
            )

            await interaction.response.send_message(
                "Select a character to use",
                view=view,
                ephemeral=True,
            )
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)

            characters = await player_repository.get_characters(player)
            for character in characters:
                if character.name.lower() == name.lower():
                    await player_repository.set_active_character(player, character)
                    await interaction.followup.send(
                        f"Character {name} selected, you are now playing as {name}",
                        ephemeral=True,
                    )
                    return

            await interaction.followup.send(
                f"Character {name} not found.",
                ephemeral=True,
            )

    @character.command(name="current", description="Get the current character")
    async def current_character(self, interaction: discord.Interaction):
        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        active_character = await player_repository.get_active_character(player)
        if active_character:
            character_repository = CharacterRepository(self.postgres_manager)
            character_class = await character_repository.get_character_class(active_character)
            await interaction.response.send_message(
                "You are currently playing as",
                embed=CharacterWidget(
                    character=active_character,
                    character_class=character_class,
                    is_active=True,
                ),
                ephemeral=True,
            )
        else:
            characters = await player_repository.get_characters(player)
            if not characters:
                await interaction.response.send_message(
                    "You have no characters. Create one with `/character create`",
                    ephemeral=True,
                )
            else:
                await player_repository.set_active_character(player, characters[0])
                await interaction.response.send_message(
                    f"You are now playing as {characters[0].name}", ephemeral=True
                )

    @character.command(name="equipment", description="View your character's equipped items")
    async def view_equipment(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        active_character = await player_repository.get_active_character(player)
        if not active_character:
            await interaction.followup.send(
                "You have no active character. Use `/character use` to select one.",
                ephemeral=True,
            )
            return

        character_repository = CharacterRepository(self.postgres_manager)
        equipped = await character_repository.get_equipped_items(active_character)

        if not equipped:
            await interaction.followup.send(
                f"{active_character.name} has no items equipped.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{active_character.name}'s Equipment",
            color=discord.Color.blue(),
        )

        for slot, item in equipped.items():
            item_name = item.get("name", "Unknown Item")
            embed.add_field(name=slot.replace("_", " ").title(), value=item_name, inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @character.command(name="inventory", description="View your character's inventory")
    async def view_inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        active_character = await player_repository.get_active_character(player)
        if not active_character:
            await interaction.followup.send(
                "You have no active character. Use `/character use` to select one.",
                ephemeral=True,
            )
            return

        inventory = active_character.inventory or []

        if not inventory:
            await interaction.followup.send(
                f"{active_character.name}'s inventory is empty.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{active_character.name}'s Inventory",
            color=discord.Color.green(),
        )

        inventory_text = ""
        for item in inventory:
            if isinstance(item, dict):
                name = item.get("name", "Unknown Item")
                quantity = item.get("quantity", 1)
                equipped = item.get("equipped", False)
                status = " (Equipped)" if equipped else ""
                inventory_text += f"• {name} x{quantity}{status}\n"

        if inventory_text:
            embed.description = inventory_text[:2000]  # Discord embed limit
        else:
            embed.description = "Inventory is empty"

        await interaction.followup.send(embed=embed, ephemeral=True)

    @character.command(
        name="classes", description="View all available character classes and their details"
    )
    async def list_classes(self, interaction: discord.Interaction):
        """Show detailed information about all character classes."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        character_class_repo = CharacterClassRepository(self.postgres_manager)
        template_repo = ItemTemplateRepository(self.postgres_manager)

        character_classes = await character_class_repo.get_all()

        if not character_classes:
            await interaction.followup.send(
                "❌ No character classes are available. Please contact an administrator.",
                ephemeral=True,
            )
            return

        embeds = []
        for character_class in character_classes:
            # Get class stats
            stats = await character_class_repo.get_stats(character_class)
            stat_names = [stat.abbr for stat in stats]

            # Get starting equipment
            from sqlmodel import select

            from ds_common.models.junction_tables import CharacterClassStartingEquipment

            equipment_list = []
            async with self.postgres_manager.get_session() as sess:
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
                title=f"{character_class.emoji} {character_class.name}",
                description=character_class.description,
                color=discord.Color.blue(),
            )

            if stat_names:
                embed.add_field(
                    name="Primary Stats",
                    value=", ".join(stat_names),
                    inline=True,
                )

            if equipment_list:
                embed.add_field(
                    name="Starting Equipment",
                    value="\n".join(equipment_list) or "None",
                    inline=False,
                )

            embed.set_footer(text="Use /character create to start creating a character")
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds, ephemeral=True)

    @character.command(name="reset", description="Reset your character's stats and level")
    async def reset_character(self, interaction: discord.Interaction):
        """Reset character stats and level back to starting values."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        active_character = await player_repository.get_active_character(player)
        if not active_character:
            await interaction.followup.send(
                "You have no active character. Use `/character use` to select one.",
                ephemeral=True,
            )
            return

        # Check if character is in a game session - BLOCK if active
        character_repository = CharacterRepository(self.postgres_manager)
        game_session = await character_repository.get_game_session(active_character)
        if game_session:
            await interaction.followup.send(
                "❌ **Cannot Reset Character**\n\n"
                "You cannot reset a character while in an active game session. "
                "Please end your current game session with `/game end` first, "
                "then you can reset your character.",
                ephemeral=True,
            )
            return

        # Show confirmation dialog
        from ds_discord_bot.extensions.views.character_reset_confirmation import (
            CharacterResetConfirmationView,
        )

        embed = discord.Embed(
            title="🔄 Character Reset",
            description=(
                f"**Warning: This will reset {active_character.name}**\n\n"
                "This action will:\n"
                "• Reset stats to new random values (based on your class)\n"
                "• Reset level to 1\n"
                "• Reset experience to 0\n"
                "• Reset credits to 100 quill\n"
                "• Reset renown and shadow level to 0\n"
                "• Reset inventory and equipment to starting equipment\n"
                "• **Keep** your character name, gender, and class\n\n"
                "**This action cannot be undone.**\n\n"
                "Are you sure you want to proceed?"
            ),
            color=discord.Color.orange(),
        )

        view = CharacterResetConfirmationView(
            postgres_manager=self.postgres_manager,
            character=active_character,
            game_settings=self.bot.game_settings,
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @character.command(name="help", description="Get help with character commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.character.commands:
            help_text += "\n\n"

            for command in self.character.commands:
                if command.name == "help":
                    continue

                help_text += f"`/{command.parent.name} {command.name}` - {command.description}\n"

        embed = discord.Embed(
            title="Character command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading character cog...")
    await bot.add_cog(Character(bot=bot, postgres_manager=bot.postgres_manager))
