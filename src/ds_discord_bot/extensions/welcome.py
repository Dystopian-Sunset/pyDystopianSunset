import logging
from datetime import UTC, datetime

import discord
from discord import Member, User
from discord.ext import commands

# Import all models to ensure they are registered with SQLModel metadata
# This must happen before any database operations
import ds_common.models  # noqa: F401
from ds_common.models.player import Player
from ds_common.repository.character import CharacterRepository
from ds_common.repository.game_session import GameSessionRepository
from ds_common.repository.player import PlayerRepository
from ds_common.repository.rules_reaction import RulesReactionRepository
from ds_discord_bot.postgres_manager import PostgresManager


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.postgres_manager: PostgresManager = postgres_manager
        self.rules_reaction_repo = RulesReactionRepository(postgres_manager)

    def _get_config(self):
        """Get configuration instance."""
        from ds_common.config_bot import get_config

        return get_config()

    @property
    def required_message_ids(self) -> list[int]:
        """Get required message IDs from config."""
        config = self._get_config()
        return config.role_management_player_role_message_ids

    @property
    def player_role_name(self) -> str:
        """Get player role name from config."""
        config = self._get_config()
        return config.role_management_player_role_name

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Welcome cog loaded")
        # Log configured message IDs
        self.logger.info(
            f"Player role configuration: role='{self.player_role_name}', "
            f"required message IDs: {self.required_message_ids}"
        )
        await self.verify_rules_messages()
        await self.check_existing_reactions()
        await self.sync_users()
        await self.verify_existing_members()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member | User):
        self.logger.info("Member joined: %s", member)
        await self.sync_user(member)
        # Don't auto-assign role - wait for reactions
        await self.update_player_role(member)

        from ds_discord_bot.extensions.utils.channels import send_dm

        config = self._get_config()
        game_name = config.game_name

        try:
            await send_dm(
                self.bot,
                member,
                f"Welcome to the {game_name}!\n\nI will be your assistant. Type `/help` for detailed help.",
            )
        except Exception as e:
            self.logger.warning(f"Failed to send welcome DM to {member.display_name}: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member | User):
        self.logger.info("Member left: %s", member)

        player_repo = PlayerRepository(self.postgres_manager)
        player = await player_repo.get_by_discord_id(member.id)
        character_repo = CharacterRepository(self.postgres_manager)
        game_session_repo = GameSessionRepository(self.postgres_manager)
        if player:
            game_session = await player_repo.get_game_session(player)

            if game_session:
                await game_session_repo.remove_player(player, game_session)
                self.logger.debug(
                    "Removed player %s from game session %s",
                    player,
                    game_session,
                )

            characters = await player_repo.get_characters(player)
            for character in characters:
                await character_repo.delete(character.id)
                self.logger.debug("Deleted character %s", character)

            player.is_active = False
            player.last_active_at = datetime.now(UTC)
            await player_repo.upsert(player)
            self.logger.debug("Deactivated player %s", player)

        if self.bot.channel_bot_logs:
            await self.bot.channel_bot_logs.send(
                f"Member left: {member}, they had {len(characters)} characters. Player data has been deactivated. Hasta la vista, baby."
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction additions to rules messages using raw events (works even if message not in cache)."""
        # Log ALL reaction events to verify they're being received
        self.logger.info(
            f"Raw reaction event received: User ID {payload.user_id} reacted with {payload.emoji} "
            f"to message ID {payload.message_id} in channel {payload.channel_id}"
        )

        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            self.logger.debug("Ignoring bot's own reaction")
            return

        # Get the user (might be None if not in cache)
        user = self.bot.get_user(payload.user_id)
        if user and user.bot:
            self.logger.debug(f"Ignoring bot reaction from {user}")
            return

        message_id = payload.message_id
        self.logger.info(f"Processing reaction to message ID: {message_id}")

        # Check if this is a reaction to a required rules message
        if message_id not in self.required_message_ids:
            self.logger.debug(
                f"Message {message_id} is not a tracked rules message. "
                f"Tracked message IDs: {self.required_message_ids}"
            )
            return

        self.logger.info(
            f"✓ Detected reaction to required rules message {message_id} by user ID {payload.user_id}"
        )

        # Get the guild and member
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            self.logger.warning(f"Could not find guild {payload.guild_id}")
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                self.logger.warning(f"User {payload.user_id} not found in guild")
                return
            except Exception as e:
                self.logger.error(f"Error fetching member {payload.user_id}: {e}")
                return

        # Get or create player
        player_repo = PlayerRepository(self.postgres_manager)
        player = await player_repo.get_by_discord_id(member.id)

        if not player:
            self.logger.info(f"Player not found for {member}, syncing user...")
            await self.sync_user(member)
            player = await player_repo.get_by_discord_id(member.id)

        if not player:
            self.logger.error(f"Could not create/find player for user {member.id}")
            return

        self.logger.info(f"Found player: {player.display_name} (ID: {player.id})")

        # Record the reaction (this will create or update the reaction record)
        reaction_record = await self.rules_reaction_repo.add_player_reaction(player, message_id)
        self.logger.info(
            f"✓ Recorded reaction: Player {player.display_name} reacted to rules message {message_id} "
            f"at {reaction_record.reacted_at}"
        )

        # Check current reaction status
        player_reactions = await self.rules_reaction_repo.get_player_reactions(player)
        reacted_message_ids = {r.message_id for r in player_reactions}
        required_count = len(self.required_message_ids)
        reacted_count = len(
            [mid for mid in self.required_message_ids if mid in reacted_message_ids]
        )

        self.logger.info(
            f"Player {player.display_name} has {reacted_count}/{required_count} required reactions"
        )

        # Check if they should get the player role
        is_eligible = await self.check_player_role_eligibility(player)
        self.logger.info(
            f"Player {player.display_name} eligibility check: {is_eligible} "
            f"(has {reacted_count} reactions, needs {required_count})"
        )

        await self.update_player_role(member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle reaction removals from rules messages using raw events (works even if message not in cache)."""
        self.logger.info(
            f"Raw reaction removal event received: User ID {payload.user_id} removed {payload.emoji} "
            f"from message ID {payload.message_id} in channel {payload.channel_id}"
        )

        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            self.logger.debug("Ignoring bot's own reaction removal")
            return

        message_id = payload.message_id
        self.logger.info(f"Processing reaction removal from message ID: {message_id}")

        # Check if this is a reaction to a required rules message
        if message_id not in self.required_message_ids:
            self.logger.debug(
                f"Message {message_id} is not a tracked rules message. "
                f"Tracked message IDs: {self.required_message_ids}"
            )
            return

        self.logger.info(
            f"✓ Detected reaction removal from required rules message {message_id} by user ID {payload.user_id}"
        )

        # Get the guild and member
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            self.logger.warning(f"Could not find guild {payload.guild_id}")
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                self.logger.warning(f"User {payload.user_id} not found in guild")
                return
            except Exception as e:
                self.logger.error(f"Error fetching member {payload.user_id}: {e}")
                return

        # Get player
        player_repo = PlayerRepository(self.postgres_manager)
        player = await player_repo.get_by_discord_id(member.id)

        if not player:
            self.logger.warning(f"Could not find player for user {member.id}")
            return

        # Remove the reaction
        await self.rules_reaction_repo.remove_player_reaction(player, message_id)
        self.logger.info(
            f"✓ Removed reaction: Player {player.display_name} removed reaction from rules message {message_id}"
        )

        # Check current reaction status
        player_reactions = await self.rules_reaction_repo.get_player_reactions(player)
        reacted_message_ids = {r.message_id for r in player_reactions}
        required_count = len(self.required_message_ids)
        reacted_count = len(
            [mid for mid in self.required_message_ids if mid in reacted_message_ids]
        )

        self.logger.info(
            f"Player {player.display_name} now has {reacted_count}/{required_count} required reactions"
        )

        # Check if they should lose the player role
        await self.update_player_role(member)

    async def sync_users(self):
        self.logger.info("Syncing users...")
        bot_users = 0
        for user in self.bot.users:
            if not user.bot:
                await self.sync_user(user)
                # Don't auto-assign role - check eligibility instead
                await self.update_player_role(user)
            else:
                bot_users += 1

        self.logger.info(f"Synced {len(self.bot.users) - bot_users} users. {bot_users} bots.")

    async def sync_user(self, user: Member | User, is_active: bool = True):
        player_repo = PlayerRepository(self.postgres_manager)
        player = await player_repo.get_by_discord_id(user.id)

        if not player:
            player = Player.from_member(user, is_active)
            self.logger.debug(f"Created player {player}")
        else:
            self.logger.debug(f"Found existing player {player}")

        player.is_active = is_active
        player.last_active_at = datetime.now(UTC)
        player = await player_repo.upsert(player)

        self.logger.debug(f"Synced player {player}")

        if player.is_banned:
            await user.ban()

        self.logger.info(f"Synced user {user}:{user.id}")

    async def verify_rules_messages(self):
        """
        Verify that the configured rules messages exist in Discord.
        """
        if not self.required_message_ids:
            self.logger.warning("No citizen role message IDs configured in config.toml")
            return

        self.logger.info(f"Verifying {len(self.required_message_ids)} configured rules messages...")

        # Verify messages exist in Discord
        if self.bot.channel_rules:
            for message_id in self.required_message_ids:
                try:
                    message = await self.bot.channel_rules.fetch_message(message_id)
                    self.logger.info(
                        f"✓ Verified rules message exists: {message_id} "
                        f"(author: {message.author}, channel: {self.bot.channel_rules.name})"
                    )
                except discord.NotFound:
                    self.logger.error(
                        f"✗ Rules message {message_id} not found in rules channel '{self.bot.channel_rules.name}'. "
                        f"Please verify the message ID is correct in config.toml"
                    )
                except discord.Forbidden:
                    self.logger.error(
                        f"✗ Bot does not have permission to read message {message_id} in rules channel."
                    )
                except Exception as e:
                    self.logger.error(f"✗ Error verifying rules message {message_id}: {e}")
        else:
            self.logger.warning("Rules channel not found. Cannot verify message existence.")

        self.logger.info(
            f"Rules message verification complete. {len(self.required_message_ids)} message IDs configured."
        )

    async def check_existing_reactions(self):
        """
        Check for existing reactions on rules messages and sync them to the database.
        This catches reactions that were added before the bot came online.
        """
        if not self.bot.channel_rules:
            self.logger.warning("Rules channel not found. Cannot check existing reactions.")
            return

        if not self.required_message_ids:
            self.logger.warning(
                "No required message IDs configured. Skipping existing reactions check."
            )
            return

        self.logger.info(
            f"Checking existing reactions on {len(self.required_message_ids)} rules messages..."
        )
        player_repo = PlayerRepository(self.postgres_manager)
        synced_count = 0

        for message_id in self.required_message_ids:
            try:
                message = await self.bot.channel_rules.fetch_message(message_id)
                self.logger.debug(f"Checking reactions on message {message_id}")

                # Check all reactions on this message
                for reaction in message.reactions:
                    async for user in reaction.users():
                        if user.bot:
                            continue

                        # Get or create player
                        player = await player_repo.get_by_discord_id(user.id)
                        if not player:
                            if isinstance(user, Member):
                                await self.sync_user(user)
                                player = await player_repo.get_by_discord_id(user.id)
                            else:
                                continue

                        if not player:
                            continue

                        # Check if we already have this reaction recorded
                        existing_reactions = await self.rules_reaction_repo.get_player_reactions(
                            player
                        )
                        has_this_reaction = any(
                            r.message_id == message_id for r in existing_reactions
                        )

                        if not has_this_reaction:
                            await self.rules_reaction_repo.add_player_reaction(player, message_id)
                            self.logger.info(
                                f"✓ Synced existing reaction: {user.display_name} reacted to message {message_id}"
                            )
                            synced_count += 1

                            # Check role eligibility after syncing
                            await self.update_player_role(user)

            except discord.NotFound:
                self.logger.warning(f"Message {message_id} not found in rules channel")
            except discord.Forbidden:
                self.logger.error(f"Bot does not have permission to read message {message_id}")
            except Exception as e:
                self.logger.error(
                    f"Error checking reactions on message {message_id}: {e}", exc_info=True
                )

        self.logger.info(f"Existing reactions check complete. Synced {synced_count} reactions.")

    async def check_player_role_eligibility(self, player: Player) -> bool:
        """
        Check if a player has reacted to all required rules messages.

        Args:
            player: Player to check

        Returns:
            True if player is eligible for player role, False otherwise
        """
        return await self.rules_reaction_repo.has_reacted_to_all_required_messages(
            player, self.required_message_ids
        )

    async def update_player_role(self, member: Member | User):
        """
        Grant or remove the player role based on reaction eligibility.

        Args:
            member: Discord member to update
        """
        guild = self.bot.guilds[0]

        if isinstance(member, User) and not isinstance(member, Member):
            user_id = member.id
            member = guild.get_member(user_id)
            if member is None:
                # If not cached, fetch from API
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    self.logger.warning(f"User {user_id} not found in guild.")
                    return

        if not isinstance(member, Member):
            return

        player_role = discord.utils.get(guild.roles, name=self.player_role_name)
        if not player_role:
            self.logger.warning(f"Player role '{self.player_role_name}' not found in guild.")
            return

        # Get player
        player_repo = PlayerRepository(self.postgres_manager)
        player = await player_repo.get_by_discord_id(member.id)

        if not player:
            return

        # Check eligibility
        is_eligible = await self.check_player_role_eligibility(player)

        # Get detailed reaction status for logging
        player_reactions = await self.rules_reaction_repo.get_player_reactions(player)
        reacted_message_ids = {r.message_id for r in player_reactions}
        required_message_ids_set = set(self.required_message_ids)
        reacted_count = len(
            [mid for mid in self.required_message_ids if mid in reacted_message_ids]
        )
        required_count = len(self.required_message_ids)

        self.logger.info(
            f"Role update check for {member.display_name}: "
            f"eligible={is_eligible}, has_role={player_role in member.roles}, "
            f"reacted_to={reacted_count}/{required_count} messages"
        )

        has_role = player_role in member.roles

        if is_eligible and not has_role:
            # Grant role
            await member.add_roles(player_role)
            self.logger.info(
                f"✓ Granted player role to {member.display_name} "
                f"(reacted to {reacted_count}/{required_count} required messages)"
            )
        elif not is_eligible and has_role:
            # Remove role
            await member.remove_roles(player_role)
            self.logger.info(
                f"✗ Removed player role from {member.display_name} "
                f"(only reacted to {reacted_count}/{required_count} required messages)"
            )
        elif is_eligible and has_role:
            self.logger.debug(
                f"Player {member.display_name} already has player role and is eligible"
            )
        else:
            self.logger.debug(
                f"Player {member.display_name} does not have player role and is not eligible"
            )

    async def verify_existing_members(self):
        """
        Verify all existing members with the player role meet the requirements.
        Remove the role from those who don't.
        """
        self.logger.info("Verifying existing members with player role...")

        guild = self.bot.guilds[0]
        player_role = discord.utils.get(guild.roles, name=self.player_role_name)

        if not player_role:
            self.logger.warning(
                f"Player role '{self.player_role_name}' not found. Skipping verification."
            )
            return

        player_repo = PlayerRepository(self.postgres_manager)
        verified_count = 0
        removed_count = 0

        for member in guild.members:
            if player_role in member.roles:
                player = await player_repo.get_by_discord_id(member.id)
                if player:
                    is_eligible = await self.check_player_role_eligibility(player)
                    if not is_eligible:
                        await member.remove_roles(player_role)
                        self.logger.info(
                            f"Removed player role from {member.display_name} (does not meet requirements)"
                        )
                        removed_count += 1
                    else:
                        verified_count += 1

        self.logger.info(
            f"Verification complete. Verified: {verified_count}, Removed: {removed_count}"
        )

    async def assign_player_role(self, member: Member | User):
        """
        Legacy method - now redirects to update_player_role for consistency.
        """
        await self.update_player_role(member)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading welcome cog...")
    await bot.add_cog(Welcome(bot=bot, postgres_manager=bot.postgres_manager))
