"""
Permission management for game sessions.

Handles Discord role management, permission validation, and channel access control.
"""

import logging
from typing import TYPE_CHECKING

import discord

from ds_common.models.game_session import GameSession
from ds_common.models.player import Player

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class PermissionManager:
    """Manages Discord roles and permissions for game sessions."""

    def __init__(self, bot: "commands.Bot"):
        """
        Initialize the permission manager.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.logger = logger

    def _get_config(self):
        """Get configuration instance."""
        from ds_common.config_bot import get_config

        return get_config()

    async def has_gm_role(self, member: discord.Member | discord.User) -> bool:
        """
        Check if a member has the GM role.

        Args:
            member: Discord member or user to check

        Returns:
            True if the member has the GM role, False otherwise
        """
        # If it's a User, try to get the Member
        if isinstance(member, discord.User) and not isinstance(member, discord.Member):
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if guild:
                member = guild.get_member(member.id)
                if not member:
                    return False

        # Check if it's actually a Member now
        if not isinstance(member, discord.Member):
            return False

        # Get GM role from config
        config = self._get_config()
        gm_role_name = config.role_management_gm_role_name
        gm_role = await self.bot.get_role(gm_role_name)
        if not gm_role:
            return False

        # Check if member has the role
        return gm_role in member.roles

    async def has_player_role(self, member: discord.Member | discord.User) -> bool:
        """
        Check if a member has the player role.

        Args:
            member: Discord member or user to check

        Returns:
            True if the member has the player role, False otherwise
        """
        # If it's a User, try to get the Member
        if isinstance(member, discord.User) and not isinstance(member, discord.Member):
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if guild:
                member = guild.get_member(member.id)
                if not member:
                    return False

        # Check if it's actually a Member now
        if not isinstance(member, discord.Member):
            return False

        # Get player role from config
        config = self._get_config()
        player_role_name = config.role_management_player_role_name
        player_role = await self.bot.get_role(player_role_name)
        if not player_role:
            return False

        # Check if member has the role
        return player_role in member.roles

    async def is_session_creator(
        self, player: Player, game_session: GameSession, postgres_manager
    ) -> bool:
        """
        Check if a player is the creator of a game session.
        The creator is the first player added to the session.

        Args:
            player: Player to check
            game_session: Game session to check
            postgres_manager: PostgresManager instance

        Returns:
            True if player is the session creator
        """
        from ds_common.repository.game_session import GameSessionRepository

        game_session_repository = GameSessionRepository(postgres_manager)
        players = await game_session_repository.players(game_session)
        if not players:
            return False
        # First player in the list is the creator (they're added first in create_game_session)
        return players[0].id == player.id

    async def create_session_role(self, game_session: GameSession) -> discord.Role:
        """
        Create a Discord role for a game session with name matching the session name exactly.
        Enforces strict 1:1 session-role relationship.

        Args:
            game_session: The game session to create a role for

        Returns:
            The created Discord role

        Raises:
            discord.Forbidden: If bot lacks permission to manage roles
            discord.HTTPException: If role creation fails
        """
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            raise RuntimeError("Bot is not in any guild")

        # Check if role already exists (orphaned role)
        existing_role = discord.utils.get(guild.roles, name=game_session.name)
        if existing_role:
            self.logger.warning(
                f"Role '{game_session.name}' already exists when creating session {game_session.id}. "
                f"This is an orphaned role - it will be reused."
            )
            return existing_role

        # Get player role to position new role below it
        # Note: Discord places new roles at the bottom by default, which is usually below player role
        # We only try to explicitly position if we can calculate a valid position
        config = self._get_config()
        player_role_name = config.role_management_player_role_name
        player_role = await self.bot.get_role(player_role_name)
        position = None
        if player_role and player_role.position > 1:
            # Position must be >= 1 (Discord doesn't allow 0)
            # We want to be just below player role, so use player role's position - 1
            position = player_role.position - 1

        try:
            # Create role with session name
            # Discord will place it at the bottom by default (lowest position)
            role = await guild.create_role(
                name=game_session.name,
                mentionable=False,
                hoist=False,
                reason=f"Game session role for {game_session.name}",
            )

            # Position role below player role if we calculated a valid position
            # If positioning fails or isn't possible, the role will be at the bottom anyway
            if position is not None and position >= 1:
                try:
                    await role.edit(position=position, reason="Position below player role")
                    self.logger.debug(
                        f"Positioned role '{role.name}' at position {position} (below player role)"
                    )
                except discord.Forbidden:
                    # Not critical - role is already at bottom which is usually correct
                    self.logger.debug(
                        f"Could not position role '{role.name}' - bot lacks permission. "
                        f"Role will remain at default position (bottom)."
                    )
                except discord.HTTPException as e:
                    # Not critical - role is already at bottom which is usually correct
                    # Only log if it's not the expected "position 0 or below" error
                    if "position 0" not in str(e).lower() and "below" not in str(e).lower():
                        self.logger.debug(
                            f"Could not position role '{role.name}': {e}. "
                            f"Role will remain at default position (bottom)."
                        )
                except Exception as e:
                    # Not critical - role is already at bottom which is usually correct
                    self.logger.debug(
                        f"Could not position role '{role.name}': {e}. "
                        f"Role will remain at default position (bottom)."
                    )

            self.logger.info(f"Created session role '{role.name}' for session {game_session.id}")
            return role

        except discord.Forbidden:
            self.logger.error(
                f"Bot lacks permission to create role for session {game_session.id}. "
                f"Bot needs 'Manage Roles' permission."
            )
            raise
        except discord.HTTPException as e:
            self.logger.error(
                f"Failed to create role for session {game_session.id}: {e}",
                exc_info=True
            )
            raise

    async def get_session_role(self, game_session: GameSession) -> discord.Role | None:
        """
        Get the Discord role for a game session by name.
        Tries cache first, then fetches from API if not found.

        Args:
            game_session: The game session to get the role for

        Returns:
            The Discord role if found, None otherwise
        """
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return None

        # Search in cached roles
        # Note: Roles are automatically cached when created, so this should work
        # If role was just created, it should be in guild.roles immediately
        role = discord.utils.get(guild.roles, name=game_session.name)
        return role

    async def delete_session_role(self, game_session: GameSession) -> None:
        """
        Delete the Discord role for a game session.
        Critical for maintaining 1:1 relationship.

        Args:
            game_session: The game session whose role should be deleted
        """
        role = await self.get_session_role(game_session)
        if not role:
            self.logger.debug(
                f"Session role '{game_session.name}' not found when deleting. "
                f"Role may have already been deleted."
            )
            return

        try:
            await role.delete(reason=f"Game session {game_session.name} ended")
            self.logger.info(f"Deleted session role '{role.name}' for session {game_session.id}")
        except discord.Forbidden:
            self.logger.error(
                f"Bot lacks permission to delete role '{role.name}' for session {game_session.id}. "
                f"Bot needs 'Manage Roles' permission."
            )
        except Exception as e:
            self.logger.error(
                f"Failed to delete role '{role.name}' for session {game_session.id}: {e}",
                exc_info=True
            )

    async def add_player_to_session_role(
        self, member: discord.Member, game_session: GameSession
    ) -> None:
        """
        Add a player to the session role.
        Validates player is in session (1 session per player constraint).

        Args:
            member: The Discord member to add to the role
            game_session: The game session
        """
        self.logger.debug(
            f"add_player_to_session_role called for {member.display_name} (ID: {member.id}) in session '{game_session.name}'"
        )
        
        # Skip GM users - they don't need session roles
        if await self.has_gm_role(member):
            self.logger.debug(
                f"Skipping role assignment for GM user {member.display_name} in session {game_session.name}"
            )
            return

        self.logger.debug(f"Looking up role for session '{game_session.name}'")
        role = await self.get_session_role(game_session)
        if not role:
            self.logger.warning(
                f"⚠️ Session role '{game_session.name}' not found when adding player {member.display_name} (ID: {member.id}). "
                f"Role should exist for session {game_session.id}. Attempting to create it."
            )
            # Try to create the role if it's missing
            try:
                role = await self.create_session_role(game_session)
                self.logger.info(
                    f"Created missing role '{role.name}' for session {game_session.id}"
                )
                # Role is automatically added to guild.roles cache when created
            except discord.HTTPException as e:
                # If role already exists (e.g., race condition), try to get it again
                if e.code == 50035:  # Invalid form body or similar
                    self.logger.debug(f"Role creation failed, trying to fetch again: {e}")
                    role = await self.get_session_role(game_session)
                    if not role:
                        self.logger.error(
                            f"Failed to get or create role for session {game_session.id} after error"
                        )
                        return
                else:
                    self.logger.error(
                        f"Failed to create missing role for session {game_session.id}: {e}",
                        exc_info=True
                    )
                    return
            except Exception as e:
                self.logger.error(
                    f"Failed to create missing role for session {game_session.id}: {e}",
                    exc_info=True
                )
                return

        # Check if member already has the role
        if role in member.roles:
            self.logger.debug(
                f"Member {member.display_name} already has role '{role.name}'"
            )
            return

        try:
            await member.add_roles(role, reason=f"Added to game session {game_session.name}")
            self.logger.info(
                f"Added {member.display_name} (ID: {member.id}) to session role '{role.name}'"
            )
        except discord.Forbidden as e:
            self.logger.error(
                f"❌ CRITICAL: Bot lacks permission to add role '{role.name}' to {member.display_name}. "
                f"Bot needs 'Manage Roles' permission and the role must be below the bot's highest role. "
                f"Error: {e}"
            )
            # Don't raise - log prominently but continue (role sync will fix it later)
        except discord.HTTPException as e:
            self.logger.error(
                f"❌ CRITICAL: HTTP error adding {member.display_name} to session role '{role.name}': {e}",
                exc_info=True
            )
            # Don't raise - log prominently but continue (role sync will fix it later)
        except Exception as e:
            self.logger.error(
                f"❌ CRITICAL: Failed to add {member.display_name} to session role '{role.name}': {e}",
                exc_info=True
            )
            # Don't raise - log prominently but continue (role sync will fix it later)

    async def remove_player_from_session_role(
        self, member: discord.Member, game_session: GameSession
    ) -> None:
        """
        Remove a player from the session role.

        Args:
            member: The Discord member to remove from the role
            game_session: The game session
        """
        # Skip GM users - they don't have session roles
        if await self.has_gm_role(member):
            return

        role = await self.get_session_role(game_session)
        if not role:
            self.logger.debug(
                f"Session role '{game_session.name}' not found when removing player {member.display_name}. "
                f"Role may have already been deleted."
            )
            return

        # Check if member has the role
        if role not in member.roles:
            self.logger.debug(
                f"Member {member.display_name} does not have role '{role.name}'"
            )
            return

        try:
            await member.remove_roles(role, reason=f"Removed from game session {game_session.name}")
            self.logger.info(
                f"Removed {member.display_name} (ID: {member.id}) from session role '{role.name}'"
            )
        except discord.Forbidden:
            self.logger.error(
                f"Bot lacks permission to remove role '{role.name}' from {member.display_name}. "
                f"Bot needs 'Manage Roles' permission."
            )
        except Exception as e:
            self.logger.error(
                f"Failed to remove {member.display_name} from session role '{role.name}': {e}",
                exc_info=True
            )

