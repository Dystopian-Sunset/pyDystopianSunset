import logging
from datetime import UTC, datetime

import discord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_session import GameSession
from ds_common.models.junction_tables import GameSessionCharacter, GameSessionPlayer
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_common.repository.character import CharacterRepository
from ds_discord_bot.extensions.utils.channels import clean_channel_name
from ds_discord_bot.postgres_manager import PostgresManager


class GameSessionRepository(BaseRepository[GameSession]):
    """
    Repository for GameSession model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, GameSession)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def from_channel(
        self, channel: discord.TextChannel | discord.VoiceChannel
    ) -> GameSession | None:
        """
        Get the game session from the channel.

        Args:
            channel: Discord channel

        Returns:
            GameSession instance or None
        """
        channel_name = clean_channel_name(channel.name)
        return await self.get_by_field("name", channel_name)

    async def update_last_active_at(
        self, channel: discord.TextChannel | discord.VoiceChannel
    ) -> None:
        """
        Update the last active timestamp for a game session.

        Args:
            channel: Discord channel
        """
        game_session = await self.from_channel(channel)
        if game_session:
            game_session.updated_at = datetime.now(UTC)
            await self.update(game_session)

    async def add_player(
        self, player: Player, game_session: GameSession, session: AsyncSession | None = None
    ) -> None:
        """
        Add a player to a game session.

        Args:
            player: Player instance
            game_session: GameSession instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            # Check if relationship already exists
            stmt = select(GameSessionPlayer).where(
                GameSessionPlayer.game_session_id == game_session.id,
                GameSessionPlayer.player_id == player.id,
            )
            result = await sess.execute(stmt)
            if result.scalar_one_or_none():
                return  # Already exists

            # Create junction table entry
            junction = GameSessionPlayer(game_session_id=game_session.id, player_id=player.id)
            sess.add(junction)
            await sess.commit()

        await self._with_session(_execute, session)
        self.logger.debug(f"Player {player.id} added to game session {game_session.id}")

    async def remove_player(
        self, player: Player, game_session: GameSession, session: AsyncSession | None = None
    ) -> None:
        """
        Remove a player from a game session.

        Args:
            player: Player instance
            game_session: GameSession instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            stmt = select(GameSessionPlayer).where(
                GameSessionPlayer.game_session_id == game_session.id,
                GameSessionPlayer.player_id == player.id,
            )
            result = await sess.execute(stmt)
            junction = result.scalar_one_or_none()
            if junction:
                await sess.delete(junction)
                await sess.commit()

        await self._with_session(_execute, session)

        # Check if session is empty and delete if so
        players = await self.players(game_session)
        if not players:
            await self.delete(game_session.id)
            self.logger.debug(f"Deleted empty game session {game_session.id}")

    async def add_character(
        self, character: Character, game_session: GameSession, session: AsyncSession | None = None
    ) -> None:
        """
        Add a character to a game session.

        Args:
            character: Character instance
            game_session: GameSession instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            # Check if relationship already exists
            stmt = select(GameSessionCharacter).where(
                GameSessionCharacter.game_session_id == game_session.id,
                GameSessionCharacter.character_id == character.id,
            )
            result = await sess.execute(stmt)
            if result.scalar_one_or_none():
                return  # Already exists

            # Create junction table entry
            junction = GameSessionCharacter(
                game_session_id=game_session.id, character_id=character.id
            )
            sess.add(junction)
            await sess.commit()

        await self._with_session(_execute, session)
        self.logger.debug(f"Character {character.id} added to game session {game_session.id}")

    async def remove_character(
        self, character: Character, game_session: GameSession, session: AsyncSession | None = None
    ) -> None:
        """
        Remove a character from a game session.

        Args:
            character: Character instance
            game_session: GameSession instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            stmt = select(GameSessionCharacter).where(
                GameSessionCharacter.game_session_id == game_session.id,
                GameSessionCharacter.character_id == character.id,
            )
            result = await sess.execute(stmt)
            junction = result.scalar_one_or_none()
            if junction:
                await sess.delete(junction)
                await sess.commit()

        await self._with_session(_execute, session)

    async def players(
        self, game_session: GameSession, session: AsyncSession | None = None
    ) -> list[Player]:
        """
        Get all players in the game session.

        Args:
            game_session: GameSession instance
            session: Optional database session

        Returns:
            List of Player instances
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(game_session, ["players"])
                return game_session.players or []
            fresh_session = await sess.get(GameSession, game_session.id)
            if not fresh_session:
                return []
            await sess.refresh(fresh_session, ["players"])
            return fresh_session.players or []

        return await self._with_session(_execute, session)

    async def characters(
        self, game_session: GameSession, session: AsyncSession | None = None
    ) -> list[tuple[Character, CharacterClass]]:
        """
        Get all characters in the game session with their classes.

        Args:
            game_session: GameSession instance
            session: Optional database session

        Returns:
            List of tuples (Character, CharacterClass)
        """

        async def _execute(sess: AsyncSession):
            await sess.refresh(game_session, ["characters"])
            characters = game_session.characters or []

            character_repository = CharacterRepository(self.postgres_manager)
            result = []
            for character in characters:
                character_class = await character_repository.get_character_class(
                    character, session=sess
                )
                if character_class:
                    result.append((character, character_class))

            return result

        async def _execute_with_fresh(sess: AsyncSession):
            fresh_session = await sess.get(GameSession, game_session.id)
            if not fresh_session:
                return []
            await sess.refresh(fresh_session, ["characters"])
            characters = fresh_session.characters or []

            character_repository = CharacterRepository(self.postgres_manager)
            result = []
            for character in characters:
                character_class = await character_repository.get_character_class(
                    character, session=sess
                )
                if character_class:
                    result.append((character, character_class))

            return result

        if session:
            return await _execute(session)
        return await self._with_session(_execute_with_fresh, session)
