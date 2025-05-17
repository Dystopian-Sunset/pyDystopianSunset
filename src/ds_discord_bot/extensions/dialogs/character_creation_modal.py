from datetime import datetime, timezone
from typing import override

from discord import Interaction, ui
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.player import Player


class CharacterCreationModal(ui.Modal, title="Character Creation"):
    character_name = ui.TextInput(
        label="Character Name", placeholder="Enter your character's name"
    )

    def __init__(self, db: AsyncSurreal, character_class_id: int | str | RecordID):
        super().__init__()

        self.db = db
        self.character_class_id = character_class_id

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        character_class = await CharacterClass.from_db(
            db=self.db, id=self.character_class_id
        )
        character = Character(
            name=self.character_name.value,
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
        )

        print(character)
        print(character_class)

        player = Player.from_member(interaction.user)

        print(player)

        await character.insert(self.db)

        print("Inserted character")

        await character.set_class(self.db, character_class)
        await player.relate_character(self.db, character)

        if await player.get_active_character(self.db) is None:
            await player.set_active_character(self.db, character)