import logging
from uuid import UUID

import discord
from discord import app_commands
from discord.ext import commands

from ds_common.memory.unwind_service import UnwindService
from ds_common.repository.memory_settings import MemorySettingsRepository
from ds_common.repository.memory_snapshot import MemorySnapshotRepository
from ds_discord_bot.postgres_manager import PostgresManager


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.postgres_manager: PostgresManager = postgres_manager

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Admin cog loaded")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors gracefully, especially for DMs."""
        # Only handle errors for our sync-commands command
        if ctx.command and ctx.command.name == "sync-commands":
            # Check if it's a DM error
            if isinstance(error, commands.CommandError) and "DMs" in str(error):
                try:
                    await ctx.send(
                        "❌ This command can only be used in a server channel, not in DMs. "
                        "Admin commands require server permissions."
                    )
                except discord.HTTPException:
                    pass  # Can't send message (e.g., blocked bot)
                # Stop error propagation
                return
            # For MissingPermissions in DMs, also handle gracefully
            if isinstance(error, commands.MissingPermissions):
                if isinstance(ctx.channel, discord.DMChannel):
                    try:
                        await ctx.send(
                            "❌ This command can only be used in a server channel, not in DMs. "
                            "Admin commands require server permissions."
                        )
                    except discord.HTTPException:
                        pass
                    return
            # For other errors, let them propagate

    @staticmethod
    def _check_admin_not_dm(ctx: commands.Context) -> bool:
        """Check that command is not used in DMs and user has admin permissions."""
        if isinstance(ctx.channel, discord.DMChannel):
            # This will be caught by the error handler
            raise commands.CommandError(
                "This command can only be used in a server channel, not in DMs."
            )
        # Check admin permissions
        if not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(["administrator"])
        return True

    admin = app_commands.Group(name="admin", description="Admin commands")

    @commands.command(name="sync-commands", description="Sync commands")
    @app_commands.checks.has_permissions(administrator=True)
    @commands.check(_check_admin_not_dm)
    async def text_sync_commands(self, ctx: commands.Context):
        """
        Non slash command variant to force sync commands
        """
        # Check if this is a DM - admin commands don't work in DMs
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in a server channel, not in DMs.")
            return

        try:
            await self.bot.tree.sync()
            await ctx.send("✅ Synced commands...")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
            await ctx.send(f"❌ Failed to sync commands: {e}")

    @admin.command(name="sync-commands", description="Sync commands")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        """
        Slash command variant to force sync commands
        """
        # Check if this is a DM - admin commands don't work in DMs
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message(
                "❌ This command can only be used in a server channel, not in DMs.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.bot.tree.sync()
            await interaction.followup.send("✅ Synced commands...")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
            await interaction.followup.send(f"❌ Failed to sync commands: {e}")

    @admin.command(name="help", description="Get help with admin commands")
    @app_commands.checks.has_permissions(administrator=True)
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.admin.commands:
            help_text += "\n\n"

            for command in self.admin.commands:
                if command.name == "help":
                    continue

                help_text += f"`/{command.parent.name} {command.name}` - {command.description}\n"

        embed = discord.Embed(
            title="Admin command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # Memory system admin commands
    memory = app_commands.Group(name="memory", description="Memory system admin commands")
    snapshots = app_commands.Group(
        name="snapshots", description="Snapshot management", parent=memory
    )
    settings_group = app_commands.Group(
        name="settings", description="Memory settings", parent=memory
    )

    @snapshots.command(name="list", description="List all snapshots")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        unwound_only="Show unwound only",
        recent="Show recent (last 10)",
        world_memory_id="Filter by memory ID",
    )
    async def list_snapshots(
        self,
        interaction: discord.Interaction,
        unwound_only: bool = False,
        recent: bool = False,
        world_memory_id: str | None = None,
    ):
        """List all snapshots with optional filtering."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            snapshot_repo = MemorySnapshotRepository(self.postgres_manager)

            if recent:
                snapshots = await snapshot_repo.get_all_snapshots(unwound=None, limit=10)
            elif unwound_only:
                snapshots = await snapshot_repo.get_unwound_snapshots()
            elif world_memory_id:
                snapshots = await snapshot_repo.get_snapshots_for_world_memory(
                    UUID(world_memory_id)
                )
            else:
                snapshots = await snapshot_repo.get_all_snapshots()

            if not snapshots:
                await interaction.followup.send("No snapshots found.", ephemeral=True)
                return

            # Create embed with pagination
            embed = discord.Embed(
                title="Memory Snapshots",
                description=f"Found {len(snapshots)} snapshot(s)",
                color=discord.Color.blue(),
            )

            for i, snapshot in enumerate(snapshots[:10], 1):  # Show first 10
                status = "Unwound" if snapshot.unwound_at else "Active"
                embed.add_field(
                    name=f"{i}. {snapshot.created_reason[:50]}",
                    value=f"ID: `{snapshot.id}`\nType: {snapshot.snapshot_type}\nStatus: {status}\nCreated: {snapshot.created_at.strftime('%Y-%m-%d %H:%M')}",
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to list snapshots: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @snapshots.command(name="view", description="View detailed snapshot information")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(snapshot_id="Snapshot ID to view")
    async def view_snapshot(self, interaction: discord.Interaction, snapshot_id: str):
        """View detailed snapshot information."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            snapshot_repo = MemorySnapshotRepository(self.postgres_manager)
            snapshot = await snapshot_repo.get_by_id(UUID(snapshot_id))

            if not snapshot:
                await interaction.followup.send("Snapshot not found.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"Snapshot: {snapshot.created_reason[:100]}",
                color=discord.Color.blue(),
            )

            embed.add_field(name="ID", value=str(snapshot.id), inline=False)
            embed.add_field(name="Type", value=snapshot.snapshot_type, inline=True)
            embed.add_field(
                name="Created", value=snapshot.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True
            )
            embed.add_field(name="Can Unwind", value=str(snapshot.can_unwind), inline=True)

            if snapshot.unwound_at:
                embed.add_field(
                    name="Unwound At",
                    value=snapshot.unwound_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True,
                )
                embed.add_field(
                    name="Unwound By",
                    value=f"<@{snapshot.unwound_by}>" if snapshot.unwound_by else "Unknown",
                    inline=True,
                )

            if snapshot.world_memory_id:
                embed.add_field(
                    name="World Memory ID", value=str(snapshot.world_memory_id), inline=False
                )

            if snapshot.episode_id:
                embed.add_field(name="Episode ID", value=str(snapshot.episode_id), inline=False)

            snapshot_data = snapshot.snapshot_data
            world_memories_count = len(snapshot_data.get("world_memories", []))
            embed.add_field(
                name="World Memories in Snapshot", value=str(world_memories_count), inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to view snapshot: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @snapshots.command(name="rollback", description="Rollback a snapshot (restore world state)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(snapshot_id="Snapshot ID to rollback")
    async def rollback_snapshot(self, interaction: discord.Interaction, snapshot_id: str):
        """Rollback a snapshot to restore world state."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            unwind_service = UnwindService(self.postgres_manager)

            # Get preview first
            preview = await unwind_service.get_unwind_preview(UUID(snapshot_id))

            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Snapshot Rollback",
                description="This will restore the world state from the snapshot. This action cannot be undone!",
                color=discord.Color.red(),
            )

            embed.add_field(name="Snapshot ID", value=preview["snapshot_id"], inline=False)
            embed.add_field(
                name="Memories to Restore", value=str(preview["memories_to_restore"]), inline=True
            )
            embed.add_field(
                name="Memories to Remove", value=str(preview["memories_to_remove"]), inline=True
            )
            embed.add_field(name="Reason", value=preview["snapshot_reason"][:200], inline=False)

            # Create confirmation button
            view = discord.ui.View(timeout=60.0)

            async def confirm_callback(button_interaction: discord.Interaction):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message(
                        "This is not your confirmation.", ephemeral=True
                    )
                    return

                await button_interaction.response.defer(ephemeral=True, thinking=True)

                try:
                    result = await unwind_service.unwind_snapshot(
                        UUID(snapshot_id), interaction.user.id
                    )

                    success_embed = discord.Embed(
                        title="✅ Snapshot Rollback Complete",
                        description=f"Restored {result['restored_memories']} memories, removed {result['removed_memories']} memories.",
                        color=discord.Color.green(),
                    )

                    await button_interaction.followup.send(embed=success_embed, ephemeral=True)
                except Exception as e:
                    self.logger.error(f"Failed to rollback snapshot: {e}")
                    await button_interaction.followup.send(f"Error: {e!s}", ephemeral=True)

            async def cancel_callback(button_interaction: discord.Interaction):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message(
                        "This is not your confirmation.", ephemeral=True
                    )
                    return

                await button_interaction.response.send_message(
                    "Rollback cancelled.", ephemeral=True
                )
                view.stop()

            confirm_button = discord.ui.Button(
                label="Confirm Rollback", style=discord.ButtonStyle.danger
            )
            confirm_button.callback = confirm_callback
            view.add_item(confirm_button)

            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to rollback snapshot: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @settings_group.command(name="view", description="View current memory settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_settings(self, interaction: discord.Interaction):
        """View current memory system settings."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            settings_repo = MemorySettingsRepository(self.postgres_manager)
            settings = await settings_repo.get_settings()

            embed = discord.Embed(
                title="Memory System Settings",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Session Memory Expiration",
                value=f"{settings.session_memory_expiration_hours} hours",
                inline=True,
            )
            embed.add_field(
                name="Episode Memory Expiration",
                value=f"{settings.episode_memory_expiration_hours} hours",
                inline=True,
            )
            embed.add_field(
                name="Snapshot Retention",
                value=f"{settings.snapshot_retention_days} days",
                inline=True,
            )
            embed.add_field(
                name="Auto Cleanup",
                value="Enabled" if settings.auto_cleanup_enabled else "Disabled",
                inline=True,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to view settings: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @settings_group.command(name="update", description="Update memory settings")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        session_expiration="Session expiration (hrs)",
        episode_expiration="Episode expiration (hrs)",
        snapshot_retention="Snapshot retention (days)",
        auto_cleanup="Enable auto cleanup",
    )
    async def update_settings(
        self,
        interaction: discord.Interaction,
        session_expiration: int | None = None,
        episode_expiration: int | None = None,
        snapshot_retention: int | None = None,
        auto_cleanup: bool | None = None,
    ):
        """Update memory system settings."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            settings_repo = MemorySettingsRepository(self.postgres_manager)
            settings = await settings_repo.get_settings()

            if session_expiration is not None:
                if session_expiration < 1:
                    await interaction.followup.send(
                        "Session expiration must be at least 1 hour.", ephemeral=True
                    )
                    return
                settings.session_memory_expiration_hours = session_expiration

            if episode_expiration is not None:
                if episode_expiration < 1:
                    await interaction.followup.send(
                        "Episode expiration must be at least 1 hour.", ephemeral=True
                    )
                    return
                settings.episode_memory_expiration_hours = episode_expiration

            if snapshot_retention is not None:
                if snapshot_retention < 1:
                    await interaction.followup.send(
                        "Snapshot retention must be at least 1 day.", ephemeral=True
                    )
                    return
                settings.snapshot_retention_days = snapshot_retention

            if auto_cleanup is not None:
                settings.auto_cleanup_enabled = auto_cleanup

            await settings_repo.update_settings(settings)

            embed = discord.Embed(
                title="✅ Settings Updated",
                description="Memory system settings have been updated.",
                color=discord.Color.green(),
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to update settings: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @memory.command(name="health", description="Check memory system health")
    @app_commands.checks.has_permissions(administrator=True)
    async def memory_health(self, interaction: discord.Interaction):
        """Check the health and status of the memory system."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from datetime import UTC, datetime

            from ds_common.repository.episode_memory import EpisodeMemoryRepository
            from ds_common.repository.session_memory import SessionMemoryRepository
            from ds_common.repository.world_memory import WorldMemoryRepository

            session_repo = SessionMemoryRepository(self.postgres_manager)
            episode_repo = EpisodeMemoryRepository(self.postgres_manager)
            world_repo = WorldMemoryRepository(self.postgres_manager)
            settings_repo = MemorySettingsRepository(self.postgres_manager)

            # Get counts
            all_session_memories = await session_repo.get_all()
            unprocessed_memories = [m for m in all_session_memories if not m.processed]
            expired_session_memories = [
                m for m in all_session_memories if m.expires_at and m.expires_at < datetime.now(UTC)
            ]

            all_episodes = await episode_repo.get_all()
            unpromoted_episodes = [e for e in all_episodes if not e.promoted_to_world]
            expired_episodes = await episode_repo.get_expired()

            all_world_memories = await world_repo.get_all()

            settings = await settings_repo.get_settings()

            # Build embed
            embed = discord.Embed(
                title="Memory System Health",
                color=discord.Color.blue(),
            )

            # Session Memory Stats
            embed.add_field(
                name="Session Memories",
                value=(
                    f"Total: {len(all_session_memories)}\n"
                    f"Unprocessed: {len(unprocessed_memories)}\n"
                    f"Expired: {len(expired_session_memories)}"
                ),
                inline=True,
            )

            # Episode Memory Stats
            embed.add_field(
                name="Episode Memories",
                value=(
                    f"Total: {len(all_episodes)}\n"
                    f"Unpromoted: {len(unpromoted_episodes)}\n"
                    f"Expired: {len(expired_episodes)}"
                ),
                inline=True,
            )

            # World Memory Stats
            embed.add_field(
                name="World Memories",
                value=f"Total: {len(all_world_memories)}",
                inline=True,
            )

            # Settings Status
            embed.add_field(
                name="Settings",
                value=(
                    f"Session Expiration: {settings.session_memory_expiration_hours}h\n"
                    f"Episode Expiration: {settings.episode_memory_expiration_hours}h\n"
                    f"Auto Cleanup: {'✅ Enabled' if settings.auto_cleanup_enabled else '❌ Disabled'}"
                ),
                inline=False,
            )

            # Health Warnings
            warnings = []
            if len(unprocessed_memories) > 1000:
                warnings.append("⚠️ High number of unprocessed session memories")
            if len(expired_session_memories) > 500:
                warnings.append("⚠️ Many expired session memories (cleanup may be needed)")
            if len(expired_episodes) > 100:
                warnings.append("⚠️ Many expired episodes (cleanup may be needed)")
            if not settings.auto_cleanup_enabled:
                warnings.append("⚠️ Auto cleanup is disabled")

            if warnings:
                embed.add_field(
                    name="⚠️ Warnings",
                    value="\n".join(warnings),
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to check memory health: {e}", exc_info=True)
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    # World management admin commands
    world = app_commands.Group(name="world", description="World management commands")
    time_group = app_commands.Group(name="time", description="Game time management", parent=world)
    event_group = app_commands.Group(
        name="event", description="World event management", parent=world
    )
    calendar_group = app_commands.Group(
        name="calendar", description="Calendar event management", parent=world
    )
    item_group = app_commands.Group(name="item", description="World item management", parent=world)
    region_group = app_commands.Group(name="region", description="Region management", parent=world)
    seed_group = app_commands.Group(name="seed", description="World seeding commands", parent=world)

    @time_group.command(name="current", description="Show current game time")
    @app_commands.checks.has_permissions(administrator=True)
    async def time_current(self, interaction: discord.Interaction):
        """Show current game time, season, and day/night status."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            game_time = await game_time_service.get_current_game_time()
            time_of_day = await game_time_service.get_time_of_day()

            embed = discord.Embed(
                title="Current Game Time",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Game Date",
                value=f"Year {game_time.game_year}, Day {game_time.game_day}",
                inline=True,
            )
            embed.add_field(
                name="Time",
                value=f"{game_time.game_hour:02d}:{game_time.game_minute:02d}",
                inline=True,
            )
            embed.add_field(
                name="Season",
                value=game_time.season or "UNKNOWN",
                inline=True,
            )
            embed.add_field(
                name="Day/Night",
                value="🌅 Daytime" if game_time.is_daytime else "🌙 Nighttime",
                inline=True,
            )
            embed.add_field(
                name="Time of Day",
                value=time_of_day.title(),
                inline=True,
            )
            embed.add_field(
                name="Day of Week",
                value=game_time.day_of_week or "UNKNOWN",
                inline=True,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to get game time: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @time_group.command(name="advance", description="Advance game time")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(hours="Hours to advance")
    async def time_advance(self, interaction: discord.Interaction, hours: float = 1.0):
        """Advance game time by specified hours."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            real_minutes = hours / 60.0  # Convert game hours to real minutes
            updated = await game_time_service.advance_game_time(real_minutes)

            embed = discord.Embed(
                title="✅ Game Time Advanced",
                description=f"Advanced by {hours} game hour(s)",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="New Time",
                value=f"Year {updated.game_year}, Day {updated.game_day}, {updated.game_hour:02d}:{updated.game_minute:02d}",
                inline=False,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to advance game time: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @event_group.command(name="list", description="List all world events")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(status="Filter by status")
    async def event_list(self, interaction: discord.Interaction, status: str | None = None):
        """List all world events, optionally filtered by status."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.repository.world_event import WorldEventRepository

            event_repo = WorldEventRepository(self.postgres_manager)

            if status:
                events = await event_repo.get_by_status(status)
            else:
                events = await event_repo.get_all()

            if not events:
                await interaction.followup.send("No events found.", ephemeral=True)
                return

            embed = discord.Embed(
                title="World Events",
                color=discord.Color.blue(),
            )

            for event in events[:10]:  # Limit to 10
                embed.add_field(
                    name=f"{event.title} ({event.status})",
                    value=event.description or "No description",
                    inline=False,
                )

            if len(events) > 10:
                embed.set_footer(text=f"Showing 10 of {len(events)} events")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to list events: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @calendar_group.command(name="current", description="Show current game date and active events")
    @app_commands.checks.has_permissions(administrator=True)
    async def calendar_current(self, interaction: discord.Interaction):
        """Show current game date and active calendar events."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.memory.calendar_service import CalendarService
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            calendar_service = CalendarService(self.postgres_manager, game_time_service)

            current_date = await calendar_service.get_current_game_date()
            active_events = await calendar_service.get_active_events()

            embed = discord.Embed(
                title="Current Game Date",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Date",
                value=f"Year {current_date['year']}, Day {current_date['day']}, Hour {current_date['hour']}",
                inline=False,
            )
            embed.add_field(
                name="Season",
                value=current_date["season"],
                inline=True,
            )
            embed.add_field(
                name="Day of Week",
                value=current_date["day_of_week"],
                inline=True,
            )

            if active_events:
                events_text = "\n".join([f"• {e.name}" for e in active_events[:5]])
                embed.add_field(
                    name="Active Events",
                    value=events_text or "None",
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to get calendar: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @item_group.command(name="list", description="List world items")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(status="Filter by status")
    async def item_list(self, interaction: discord.Interaction, status: str | None = None):
        """List all world items, optionally filtered by status."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.repository.world_item import WorldItemRepository

            item_repo = WorldItemRepository(self.postgres_manager)

            if status:
                items = await item_repo.get_by_status(status)
            else:
                items = await item_repo.get_all()

            if not items:
                await interaction.followup.send("No items found.", ephemeral=True)
                return

            embed = discord.Embed(
                title="World Items",
                color=discord.Color.blue(),
            )

            for item in items[:10]:  # Limit to 10
                embed.add_field(
                    name=f"{item.name} ({item.status})",
                    value=item.description or "No description",
                    inline=False,
                )

            if len(items) > 10:
                embed.set_footer(text=f"Showing 10 of {len(items)} items")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to list items: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @region_group.command(name="list", description="List world regions")
    @app_commands.checks.has_permissions(administrator=True)
    async def region_list(self, interaction: discord.Interaction):
        """List all world regions."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.repository.world_region import WorldRegionRepository

            region_repo = WorldRegionRepository(self.postgres_manager)
            regions = await region_repo.get_all()

            if not regions:
                await interaction.followup.send("No regions found.", ephemeral=True)
                return

            embed = discord.Embed(
                title="World Regions",
                color=discord.Color.blue(),
            )

            for region in regions[:10]:  # Limit to 10
                embed.add_field(
                    name=f"{region.name} ({region.region_type})",
                    value=region.description or "No description",
                    inline=False,
                )

            if len(regions) > 10:
                embed.set_footer(text=f"Showing 10 of {len(regions)} regions")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to list regions: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @seed_group.command(name="all", description="Seed all world data")
    @app_commands.checks.has_permissions(administrator=True)
    async def seed_all(self, interaction: discord.Interaction):
        """Seed all world data (regions, calendar events, baseline memories)."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.world_seed_data import seed_all_world_data

            await seed_all_world_data(self.postgres_manager)

            embed = discord.Embed(
                title="✅ World Data Seeded",
                description="All world data has been seeded successfully.",
                color=discord.Color.green(),
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to seed world data: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    # World validation admin commands
    validation_group = app_commands.Group(
        name="validation", description="World validation commands", parent=world
    )

    @validation_group.command(name="validate-action", description="Test action validation")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Action text to validate",
        location="Location (optional)",
    )
    async def validate_action(
        self, interaction: discord.Interaction, action: str, location: str | None = None
    ):
        """Test action validation against world consistency rules."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.memory.validators.world_consistency_validator import (
                WorldConsistencyValidator,
            )

            validator = WorldConsistencyValidator(self.postgres_manager)
            is_valid, error_msg = await validator.validate_action(action, location)

            embed = discord.Embed(
                title="Action Validation Result",
                color=discord.Color.green() if is_valid else discord.Color.red(),
            )

            embed.add_field(name="Action", value=action[:500], inline=False)
            if location:
                embed.add_field(name="Location", value=location, inline=True)
            embed.add_field(name="Valid", value="✅ Yes" if is_valid else "❌ No", inline=True)

            if error_msg:
                embed.add_field(name="Error", value=error_msg, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to validate action: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @validation_group.command(name="add-fact", description="Add a new location fact")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        location_name="Location name",
        fact="Fact text to add",
        location_type="Location type",
    )
    async def add_fact(
        self,
        interaction: discord.Interaction,
        location_name: str,
        fact: str,
        location_type: str = "CUSTOM",
    ):
        """Add a new fact to a location."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from datetime import UTC, datetime

            from ds_common.models.location_fact import LocationFact
            from ds_common.repository.location_fact import LocationFactRepository

            fact_repo = LocationFactRepository(self.postgres_manager)
            existing = await fact_repo.get_by_location_name(location_name, case_sensitive=False)

            if existing:
                # Add fact to existing location
                if not existing.facts:
                    existing.facts = []
                existing.facts.append(fact)
                existing.updated_at = datetime.now(UTC)
                await fact_repo.update(existing)

                embed = discord.Embed(
                    title="✅ Fact Added",
                    description=f"Added fact to existing location: {location_name}",
                    color=discord.Color.green(),
                )
            else:
                # Create new location fact
                new_fact = LocationFact(
                    location_name=location_name,
                    location_type=location_type,
                    facts=[fact],
                    connections={},
                    travel_requirements={},
                    physical_properties={},
                    constraints={},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                await fact_repo.create(new_fact)

                embed = discord.Embed(
                    title="✅ Location Fact Created",
                    description=f"Created new location fact for: {location_name}",
                    color=discord.Color.green(),
                )

            embed.add_field(name="Location", value=location_name, inline=True)
            embed.add_field(name="Fact", value=fact[:500], inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to add fact: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)

    @validation_group.command(name="get-facts", description="Get facts for a location")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(location_name="Location name")
    async def get_facts(self, interaction: discord.Interaction, location_name: str):
        """Get all facts for a location."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            from ds_common.memory.validators.world_consistency_validator import (
                WorldConsistencyValidator,
            )

            validator = WorldConsistencyValidator(self.postgres_manager)
            facts = await validator.get_location_facts(location_name)

            embed = discord.Embed(
                title=f"Location Facts: {location_name}",
                color=discord.Color.blue(),
            )

            if facts:
                facts_text = "\n".join([f"• {fact}" for fact in facts])
                embed.add_field(name="Facts", value=facts_text[:1000], inline=False)
            else:
                embed.add_field(
                    name="Facts", value="No facts found for this location.", inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Failed to get facts: {e}")
            await interaction.followup.send(f"Error: {e!s}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading admin cog...")
    await bot.add_cog(Admin(bot=bot, postgres_manager=bot.postgres_manager))
