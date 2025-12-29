import logging
from typing import override

from discord import Interaction, ui

from ds_discord_bot.postgres_manager import PostgresManager


class CharacterDeletionModal(ui.Modal, title="Confirm Character Deletion"):
    """Modal for confirming character deletion by typing DELETE."""

    confirmation_text = ui.TextInput(
        label="Type DELETE to confirm",
        placeholder="DELETE",
        min_length=6,
        max_length=6,
        required=True,
    )

    def __init__(
        self,
        postgres_manager: PostgresManager,
        character_name: str,
    ):
        super().__init__()
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.character_name = character_name

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        """Handle modal submission."""
        if self.confirmation_text.value.upper() != "DELETE":
            await interaction.response.send_message(
                f"❌ Confirmation failed. You must type 'DELETE' exactly to confirm deletion of '{self.character_name}'.",
                ephemeral=True,
            )
            return

        # Defer to allow time for deletion
        await interaction.response.defer(ephemeral=True)

        # Perform deletion
        from ds_common.repository.character import CharacterRepository

        character_repo = CharacterRepository(self.postgres_manager)
        character = await character_repo.get_by_field(
            "name", self.character_name, case_sensitive=False
        )

        if not character:
            await interaction.followup.send(
                f"❌ Character '{self.character_name}' not found.",
                ephemeral=True,
            )
            return

        try:
            await character_repo.delete(character.id)
            await interaction.followup.send(
                f"✅ Character '{self.character_name}' has been permanently deleted.",
                ephemeral=True,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to delete character {self.character_name}: {e}", exc_info=True
            )
            await interaction.followup.send(
                f"❌ Failed to delete character '{self.character_name}'. Please try again later.",
                ephemeral=True,
            )
