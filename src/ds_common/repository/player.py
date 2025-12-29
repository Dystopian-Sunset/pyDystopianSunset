import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.character import Character
from ds_common.models.game_session import GameSession
from ds_common.models.junction_tables import PlayerCharacter
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class PlayerRepository(BaseRepository[Player]):
    """
    Repository for Player model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, Player)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_discord_id(
        self, discord_id: int, session: AsyncSession | None = None
    ) -> Player | None:
        """
        Get a player by Discord ID.

        Args:
            discord_id: Discord user ID
            session: Optional database session

        Returns:
            Player instance or None if not found
        """
        return await self.get_by_field("discord_id", discord_id, session=session, read_only=True)

    async def get_characters(
        self, player: Player, session: AsyncSession | None = None
    ) -> list[Character]:
        """
        Get all characters for a player.

        Args:
            player: Player instance
            session: Optional database session

        Returns:
            List of Character instances
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(player, ["characters"])
                return player.characters or []
            fresh_player = await sess.get(Player, player.id)
            if not fresh_player:
                return []
            await sess.refresh(fresh_player, ["characters"])
            return fresh_player.characters or []

        return await self._with_session(_execute, session, read_only=True)

    async def add_character(
        self, player: Player, character: Character, session: AsyncSession | None = None
    ) -> None:
        """
        Add a character to a player.

        Args:
            player: Player instance
            character: Character instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            # Check if relationship already exists
            stmt = select(PlayerCharacter).where(
                PlayerCharacter.player_id == player.id,
                PlayerCharacter.character_id == character.id,
            )
            result = await sess.execute(stmt)
            if result.scalar_one_or_none():
                return  # Already exists

            # Create junction table entry
            junction = PlayerCharacter(player_id=player.id, character_id=character.id)
            sess.add(junction)
            await sess.commit()

        await self._with_session(_execute, session)
        self.logger.debug(f"Character added: {character} to player: {player}")

    async def remove_character(
        self, player: Player, character: Character, session: AsyncSession | None = None
    ) -> None:
        """
        Remove a character from a player.

        Args:
            player: Player instance
            character: Character instance
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            stmt = select(PlayerCharacter).where(
                PlayerCharacter.player_id == player.id,
                PlayerCharacter.character_id == character.id,
            )
            result = await sess.execute(stmt)
            junction = result.scalar_one_or_none()
            if junction:
                await sess.delete(junction)
                await sess.commit()

        await self._with_session(_execute, session)
        self.logger.debug(f"Deleted character: {character} from player: {player}")

    async def get_active_character(
        self, player: Player, session: AsyncSession | None = None
    ) -> Character | None:
        """
        Get the active character for a player.

        Args:
            player: Player instance
            session: Optional database session

        Returns:
            Active Character instance or None
        """

        async def _execute(sess: AsyncSession):
            if session:
                # If session provided, refresh the passed player
                await sess.refresh(player, ["active_character"])
                return player.active_character
            # If no session, get fresh player instance
            fresh_player = await sess.get(Player, player.id)
            if not fresh_player:
                return None
            await sess.refresh(fresh_player, ["active_character"])
            return fresh_player.active_character

        return await self._with_session(_execute, session, read_only=True)

    async def set_active_character(
        self, player: Player, character: Character, session: AsyncSession | None = None
    ) -> None:
        """
        Set the active character for a player.

        Args:
            player: Player instance
            character: Character instance to set as active
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            if session:
                player.active_character_id = character.id
                sess.add(player)
            else:
                fresh_player = await sess.get(Player, player.id)
                if fresh_player:
                    fresh_player.active_character_id = character.id
                    sess.add(fresh_player)
            await sess.commit()

        await self._with_session(_execute, session)
        self.logger.debug(f"Active character set: {character} for player: {player}")

    async def get_game_session(
        self, player: Player, session: AsyncSession | None = None
    ) -> GameSession | None:
        """
        Get the game session the player is playing in.

        Args:
            player: Player instance
            session: Optional database session

        Returns:
            GameSession instance or None
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(player, ["game_sessions"])
                game_sessions = player.game_sessions or []
            else:
                fresh_player = await sess.get(Player, player.id)
                if not fresh_player:
                    return None
                await sess.refresh(fresh_player, ["game_sessions"])
                game_sessions = fresh_player.game_sessions or []
            return game_sessions[0] if game_sessions else None

        return await self._with_session(_execute, session, read_only=True)
