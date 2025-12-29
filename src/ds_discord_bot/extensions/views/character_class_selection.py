import logging
from typing import Any
from uuid import UUID

import discord
from discord.ui import Button, Select, View

from ds_common.models.character_class import CharacterClass
from ds_common.repository.character_class import CharacterClassRepository
from ds_common.repository.item_template import ItemTemplateRepository
from ds_common.strings import ellipsize
from ds_discord_bot.postgres_manager import PostgresManager


class ClassPreviewButton(Button):
    """Button to preview a character class details."""

    def __init__(
        self,
        character_class: CharacterClass,
        postgres_manager: PostgresManager,
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: Any | None = None,
        row: int = 0,
    ):
        self.character_class = character_class
        self.postgres_manager = postgres_manager
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings
        self.logger: logging.Logger = logging.getLogger(__name__)
        super().__init__(
            label=f"Preview {character_class.name}",
            emoji=character_class.emoji,
            style=discord.ButtonStyle.secondary,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        character_class_repo = CharacterClassRepository(self.postgres_manager)
        template_repo = ItemTemplateRepository(self.postgres_manager)

        # Get class stats
        stats = await character_class_repo.get_stats(self.character_class)
        stat_names = [stat.abbr for stat in stats]

        # Get starting equipment
        from sqlmodel import select

        from ds_common.models.junction_tables import CharacterClassStartingEquipment

        equipment_list = []
        async with self.postgres_manager.get_session() as sess:
            stmt = select(CharacterClassStartingEquipment).where(
                CharacterClassStartingEquipment.character_class_id == self.character_class.id
            )
            result = await sess.execute(stmt)
            starting_equipment = result.scalars().all()

            for eq in starting_equipment:
                template = await template_repo.get_by_id(eq.item_template_id)
                if template:
                    slot_name = eq.equipment_slot.replace("_", " ").title()
                    equipment_list.append(f"• {template.name} ({slot_name})")

        # Create preview embed
        embed = discord.Embed(
            title=f"{self.character_class.emoji} {self.character_class.name}",
            description=self.character_class.description,
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

        embed.set_footer(text="Click 'Select This Class' below to choose this class")

        # Create view with select button
        view = ClassSelectionView(
            postgres_manager=self.postgres_manager,
            character_class_id=self.character_class.id,
            character_creation_channel=self.character_creation_channel,
            game_settings=self.game_settings,
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class ClassSelectionView(View):
    """View with button to select a class after preview."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        character_class_id: UUID,
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: Any | None = None,
    ):
        super().__init__(timeout=300)
        self.postgres_manager = postgres_manager
        self.character_class_id = character_class_id
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings

    @discord.ui.button(label="Select This Class", style=discord.ButtonStyle.primary)
    async def select_class(self, interaction: discord.Interaction, button: Button):
        # After class selection, show gender selection
        await interaction.response.defer(ephemeral=True)

        from ds_discord_bot.extensions.views.character_gender_selection import (
            CharacterGenderSelectionView,
        )

        embed = discord.Embed(
            title="🎭 Character Creation - Step 2 of 4",
            description=(
                "**Class Selected!**\n\n"
                "**Next Step:** Select Gender\n\n"
                "Choose your character's gender. This will determine which pronouns the Game Master uses when referring to your character."
            ),
            color=discord.Color.orange(),
        )

        view = CharacterGenderSelectionView(
            postgres_manager=self.postgres_manager,
            character_creation_channel=self.character_creation_channel,
            game_settings=self.game_settings,
            selected_class_id=self.character_class_id,  # Pass class to gender selection
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class CharacterClassSelection(Select):
    def __init__(
        self,
        postgres_manager: PostgresManager,
        character_classes: list[CharacterClass],
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: Any | None = None,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.postgres_manager: PostgresManager = postgres_manager
        self.character_creation_channel: discord.TextChannel | None = character_creation_channel
        self.game_settings = game_settings

        options = [
            discord.SelectOption(
                label=character_class.name,
                description=ellipsize(character_class.description),
                emoji=character_class.emoji,
                value=str(character_class.id),
            )
            for character_class in character_classes
        ]

        if not options:
            raise ValueError(
                "Cannot create CharacterClassSelection with empty character_classes list. "
                "At least one character class must exist in the database."
            )

        super().__init__(placeholder="Select a character class", options=options)

    async def callback(self, interaction: discord.Interaction):
        character_class_id = UUID(self.values[0])
        # After class selection, show gender selection
        await interaction.response.defer(ephemeral=True)

        from ds_discord_bot.extensions.views.character_gender_selection import (
            CharacterGenderSelectionView,
        )

        embed = discord.Embed(
            title="🎭 Character Creation - Step 2 of 4",
            description=(
                "**Class Selected!**\n\n"
                "**Next Step:** Select Gender\n\n"
                "Choose your character's gender. This will determine which pronouns the Game Master uses when referring to your character."
            ),
            color=discord.Color.orange(),
        )

        view = CharacterGenderSelectionView(
            postgres_manager=self.postgres_manager,
            character_creation_channel=self.character_creation_channel,
            game_settings=self.game_settings,
            selected_class_id=character_class_id,  # Pass class to gender selection
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class CharacterClassSelectionView(View):
    def __init__(
        self,
        postgres_manager: PostgresManager,
        character_classes: list[CharacterClass],
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: Any | None = None,
    ):
        super().__init__(timeout=300)  # 5 minutes
        self.postgres_manager = postgres_manager
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings

        # Add dropdown for quick selection
        self.add_item(
            CharacterClassSelection(
                postgres_manager=postgres_manager,
                character_classes=character_classes,
                character_creation_channel=character_creation_channel,
                game_settings=game_settings,
            )
        )

        # Add preview buttons for each class (max 5 buttons per row, 5 rows = 25 classes max)
        # Discord allows max 25 components total, so we'll use buttons for first 20 classes
        # and dropdown for the rest
        max_buttons = min(20, len(character_classes))
        for i, character_class in enumerate(character_classes[:max_buttons]):
            row = i // 5  # 5 buttons per row
            self.add_item(
                ClassPreviewButton(
                    character_class=character_class,
                    postgres_manager=postgres_manager,
                    character_creation_channel=character_creation_channel,
                    game_settings=game_settings,
                    row=row + 1,  # +1 because dropdown is on row 0
                )
            )
