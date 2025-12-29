"""
Session management for game sessions.

Handles game session lifecycle, player management, and database operations.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord

from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.name_generator import NameGenerator
from ds_common.repository.game_session import GameSessionRepository
from ds_common.repository.player import PlayerRepository

if TYPE_CHECKING:
    from discord.ext import commands

    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages game session lifecycle and player management."""

    def __init__(
        self,
        bot: "commands.Bot",
        postgres_manager: "PostgresManager",
        permission_manager,
    ):
        """
        Initialize the session manager.

        Args:
            bot: The Discord bot instance
            postgres_manager: PostgresManager instance
            permission_manager: PermissionManager instance
        """
        self.bot = bot
        self.postgres_manager = postgres_manager
        self.permission_manager = permission_manager
        self.logger = logger

    async def is_session_creator(
        self, player: Player, game_session: GameSession
    ) -> bool:
        """
        Check if a player is the creator of a game session.
        The creator is the first player added to the session.

        Args:
            player: Player to check
            game_session: Game session to check

        Returns:
            True if player is the session creator
        """
        game_session_repository = GameSessionRepository(self.postgres_manager)
        players = await game_session_repository.players(game_session)
        if not players:
            return False
        # First player in the list is the creator (they're added first in create_game_session)
        return players[0].id == player.id

    async def delete_game_session(self, game_session: GameSession) -> None:
        """
        Safely delete a game session and all related data.

        Deletes in the correct order to avoid foreign key constraint violations:
        1. Session memory records
        2. GM history records
        3. Junction table entries (players, characters)
        4. Game session itself

        Args:
            game_session: GameSession instance to delete
        """
        from sqlmodel import select

        from ds_common.models.game_master import GMHistory
        from ds_common.models.junction_tables import (
            GameSessionCharacter,
            GameSessionPlayer,
        )
        from ds_common.models.session_memory import SessionMemory
        from ds_common.repository.character import CharacterRepository

        async with self.postgres_manager.get_session() as sess:
            # 0. Clean up quest items from characters before deleting quest relationships
            from ds_common.repository.quest import QuestRepository

            quest_repo = QuestRepository(self.postgres_manager)
            character_quests = await quest_repo.get_quests_by_session(game_session.id)

            character_repo = CharacterRepository(self.postgres_manager)
            for char_quest in character_quests:
                if char_quest.items_given:
                    # Get character and remove quest items
                    character = await character_repo.get_by_id(char_quest.character_id)
                    if character and character.inventory:
                        inventory = character.inventory
                        updated_inventory = []
                        items_removed = []

                        for inv_item in inventory:
                            item_removed = False
                            for quest_item in char_quest.items_given:
                                # Match by instance_id (preferred) or name
                                if inv_item.get("instance_id") == quest_item.get("instance_id"):
                                    items_removed.append(
                                        {
                                            "name": inv_item.get("name"),
                                            "quantity": inv_item.get("quantity", 0),
                                        }
                                    )
                                    item_removed = True
                                    break
                                if inv_item.get("name") == quest_item.get("name"):
                                    # Reduce quantity
                                    current_qty = inv_item.get("quantity", 0)
                                    remove_qty = quest_item.get("quantity", 0)
                                    new_qty = current_qty - remove_qty

                                    if new_qty > 0:
                                        inv_item["quantity"] = new_qty
                                        updated_inventory.append(inv_item)
                                    items_removed.append(
                                        {
                                            "name": inv_item.get("name"),
                                            "quantity": min(current_qty, remove_qty),
                                        }
                                    )
                                    item_removed = True
                                    break

                            if not item_removed:
                                updated_inventory.append(inv_item)

                        character.inventory = updated_inventory
                        await character_repo.update(character)
                        self.logger.info(
                            f"Cleaned up {len(items_removed)} quest items from character {character.id} "
                            f"when session {game_session.id} ended: {[item['name'] for item in items_removed]}"
                        )

            # 1. Delete session memory records
            stmt = select(SessionMemory).where(SessionMemory.session_id == game_session.id)
            result = await sess.execute(stmt)
            for memory in result.scalars().all():
                await sess.delete(memory)

            # 2. Delete GM history records
            stmt = select(GMHistory).where(GMHistory.game_session_id == game_session.id)
            result = await sess.execute(stmt)
            for history in result.scalars().all():
                await sess.delete(history)

            # 3. Delete junction table entries
            # Delete CharacterQuest entries (quest items already cleaned up above)
            for char_quest in character_quests:
                await sess.delete(char_quest)

            # Delete GameSessionCharacter entries
            stmt = select(GameSessionCharacter).where(
                GameSessionCharacter.game_session_id == game_session.id
            )
            result = await sess.execute(stmt)
            for junction in result.scalars().all():
                await sess.delete(junction)

            # Delete GameSessionPlayer entries
            stmt = select(GameSessionPlayer).where(
                GameSessionPlayer.game_session_id == game_session.id
            )
            result = await sess.execute(stmt)
            for junction in result.scalars().all():
                await sess.delete(junction)

            await sess.commit()

        # 4. Now delete the game session itself
        game_session_repository = GameSessionRepository(self.postgres_manager)
        await game_session_repository.delete(game_session.id)

        # 5. Delete the session role (strict 1:1 relationship)
        await self.permission_manager.delete_session_role(game_session)

    async def generate_unique_session_name(self) -> str:
        """
        Generate a unique game session name.

        Returns:
            A unique session name
        """
        game_session_repository = GameSessionRepository(self.postgres_manager)
        channel_name = NameGenerator.generate_cyberpunk_channel_name()

        counter = 1
        while await game_session_repository.get_by_field("name", channel_name):
            self.logger.debug(
                f"Duplicate game session name found, generating new name ({counter}/3)"
            )
            channel_name = NameGenerator.generate_cyberpunk_channel_name()

            counter += 1

            if counter > 3:
                self.logger.warning("Failed to generate unique game session name after 3 attempts")
                raise RuntimeError("Failed to generate unique game session name after 3 attempts")

        return channel_name

    async def create_session_in_db(
        self,
        name: str,
        creator: Player,
        creator_character,
        open_to_all: bool = False,
    ) -> GameSession:
        """
        Create a game session in the database.

        Args:
            name: Session name
            creator: The player creating the session
            creator_character: The creator's active character
            open_to_all: Whether the session is open to all players

        Returns:
            The created GameSession
        """
        game_session = GameSession(
            name=name,
            channel_id=None,
            is_open=open_to_all,
            created_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
        )

        game_session_repository = GameSessionRepository(self.postgres_manager)
        await game_session_repository.upsert(game_session)
        await game_session_repository.add_player(creator, game_session)
        await game_session_repository.add_character(creator_character, game_session)

        return game_session

    async def check_user_already_in_session(
        self, user: discord.User, guild: discord.Guild
    ) -> tuple[Player | None, GameSession | None]:
        """
        Check if a user is already in a game session.

        Args:
            user: Discord user to check
            guild: Discord guild

        Returns:
            Tuple of (Player, GameSession) if found, (None, None) otherwise
        """
        player_repository = PlayerRepository(self.postgres_manager)
        member = guild.get_member(user.id)
        if not member:
            return None, None

        # Skip GM users - they're already in every game session
        if await self.permission_manager.has_gm_role(member):
            return None, None

        target_player = await player_repository.get_by_discord_id(user.id)
        if not target_player:
            return None, None

        target_session = await player_repository.get_game_session(target_player)
        return target_player, target_session

