import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.player import Player
from ds_common.models.rules_reaction import PlayerRulesReaction
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class RulesReactionRepository:
    """
    Repository for managing rules message reactions and tracking player eligibility.

    Message IDs are configured via TOML config, not stored in the database.
    """

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres_manager = postgres_manager
        self.logger: logging.Logger = logging.getLogger(__name__)
        self._player_reaction_repo = BaseRepository(postgres_manager, PlayerRulesReaction)

    async def add_player_reaction(
        self,
        player: Player,
        message_id: int,
        session: AsyncSession | None = None,
    ) -> PlayerRulesReaction:
        """
        Record that a player has reacted to a rules message.

        Args:
            player: Player who reacted
            message_id: Discord message ID that was reacted to
            session: Optional database session

        Returns:
            PlayerRulesReaction instance
        """

        async def _execute(sess: AsyncSession):
            # Check if reaction already exists
            stmt = select(PlayerRulesReaction).where(
                PlayerRulesReaction.player_id == player.id,
                PlayerRulesReaction.message_id == message_id,
            )
            result = await sess.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update reacted_at timestamp
                from datetime import UTC, datetime

                existing.reacted_at = datetime.now(UTC)
                return await self._player_reaction_repo.update(existing, session=sess)

            # Create new reaction
            reaction = PlayerRulesReaction(
                player_id=player.id,
                message_id=message_id,
            )
            return await self._player_reaction_repo.create(reaction, session=sess)

        return await self._player_reaction_repo._with_session(_execute, session)

    async def remove_player_reaction(
        self,
        player: Player,
        message_id: int,
        session: AsyncSession | None = None,
    ) -> None:
        """
        Remove a player's reaction to a rules message.

        Args:
            player: Player who removed the reaction
            message_id: Discord message ID that was unreacted
            session: Optional database session
        """

        async def _execute(sess: AsyncSession):
            stmt = select(PlayerRulesReaction).where(
                PlayerRulesReaction.player_id == player.id,
                PlayerRulesReaction.message_id == message_id,
            )
            result = await sess.execute(stmt)
            reaction = result.scalar_one_or_none()

            if reaction:
                await sess.delete(reaction)
                await sess.commit()
                self.logger.debug(f"Removed reaction: player {player.id} to message {message_id}")

        await self._player_reaction_repo._with_session(_execute, session)

    async def get_player_reactions(
        self, player: Player, session: AsyncSession | None = None
    ) -> list[PlayerRulesReaction]:
        """
        Get all reactions for a player.

        Args:
            player: Player to get reactions for
            session: Optional database session

        Returns:
            List of PlayerRulesReaction instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(PlayerRulesReaction).where(PlayerRulesReaction.player_id == player.id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._player_reaction_repo._with_session(_execute, session, read_only=True)

    async def has_reacted_to_all_required_messages(
        self, player: Player, required_message_ids: list[int], session: AsyncSession | None = None
    ) -> bool:
        """
        Check if a player has reacted to all required rules messages.

        Args:
            player: Player to check
            required_message_ids: List of required Discord message IDs (from config)
            session: Optional database session

        Returns:
            True if player has reacted to all required messages, False otherwise
        """
        if not required_message_ids:
            # No required messages configured
            return False

        # Get player's reactions
        player_reactions = await self.get_player_reactions(player, session=session)

        # Check if player has reacted to all required messages
        reacted_message_ids = {r.message_id for r in player_reactions}
        required_message_ids_set = set(required_message_ids)

        return reacted_message_ids >= required_message_ids_set
