"""Prometheus metrics service for collecting and exposing bot metrics."""

import contextlib
import logging
import time
from contextlib import asynccontextmanager

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)


class MetricsService:
    """Centralized metrics service for Prometheus collection."""

    def __init__(self):
        """Initialize metrics service with all metric definitions."""
        self.registry = REGISTRY

        # Bot Health Metrics
        self.bot_uptime_seconds = Gauge(
            "ds_bot_uptime_seconds",
            "Bot uptime in seconds",
        )
        self.bot_ready = Gauge(
            "ds_bot_ready",
            "Bot ready state (1 = ready, 0 = not ready)",
        )
        self.bot_shard_id = Gauge(
            "ds_bot_shard_id",
            "Bot shard ID",
        )
        self.bot_shard_count = Gauge(
            "ds_bot_shard_count",
            "Total number of shards",
        )
        self.bot_guild_count = Gauge(
            "ds_bot_guild_count",
            "Number of guilds the bot is in",
        )
        self.bot_user_count = Gauge(
            "ds_bot_user_count",
            "Number of users the bot can see",
        )

        # Command Metrics
        self.commands_total = Counter(
            "ds_bot_commands_total",
            "Total number of commands executed",
            ["command", "status"],
        )
        self.command_duration_seconds = Histogram(
            "ds_bot_command_duration_seconds",
            "Command execution duration in seconds",
            ["command"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        # Database Metrics
        self.database_queries_total = Counter(
            "ds_bot_database_queries_total",
            "Total number of database queries",
            ["operation", "status"],
        )
        self.database_query_duration_seconds = Histogram(
            "ds_bot_database_query_duration_seconds",
            "Database query duration in seconds",
            ["operation"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self.database_pool_size = Gauge(
            "ds_bot_database_pool_size",
            "Database connection pool size",
            ["pool_type"],
        )
        self.database_pool_active = Gauge(
            "ds_bot_database_pool_active",
            "Active database connections in pool",
            ["pool_type"],
        )

        # AI Operations Metrics
        self.ai_agent_runs_total = Counter(
            "ds_bot_ai_agent_runs_total",
            "Total number of AI agent runs",
            ["agent_type", "status"],
        )
        self.ai_agent_duration_seconds = Histogram(
            "ds_bot_ai_agent_duration_seconds",
            "AI agent execution duration in seconds",
            ["agent_type"],
            buckets=(1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )
        self.ai_embedding_generations_total = Counter(
            "ds_bot_ai_embedding_generations_total",
            "Total number of embedding generations",
            ["model", "status"],
        )
        self.ai_embedding_duration_seconds = Histogram(
            "ds_bot_ai_embedding_duration_seconds",
            "Embedding generation duration in seconds",
            ["model"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # Memory System Metrics
        self.memory_captures_total = Counter(
            "ds_bot_memory_captures_total",
            "Total number of memory captures",
            ["memory_type"],
        )
        self.memory_compressions_total = Counter(
            "ds_bot_memory_compressions_total",
            "Total number of memory compressions",
            ["status"],
        )
        self.memory_retrievals_total = Counter(
            "ds_bot_memory_retrievals_total",
            "Total number of memory retrievals",
        )
        self.memory_episode_promotions_total = Counter(
            "ds_bot_memory_episode_promotions_total",
            "Total number of episode memory promotions",
        )
        self.memory_duration_seconds = Histogram(
            "ds_bot_memory_duration_seconds",
            "Memory operation duration in seconds",
            ["operation"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        )

        # Game Events Metrics
        self.game_sessions_total = Counter(
            "ds_bot_game_sessions_total",
            "Total number of game sessions",
            ["action"],
        )
        self.game_sessions_active = Gauge(
            "ds_bot_game_sessions_active",
            "Number of active game sessions",
        )
        self.game_encounters_total = Counter(
            "ds_bot_game_encounters_total",
            "Total number of encounters",
            ["encounter_type", "status"],
        )
        self.game_character_actions_total = Counter(
            "ds_bot_game_character_actions_total",
            "Total number of character actions",
            ["action_type"],
        )

        # World State Metrics
        self.world_state_changes_total = Counter(
            "ds_bot_world_state_changes_total",
            "Total number of world state changes",
            ["asset_type", "action"],
        )

        # Background Tasks Metrics
        self.background_tasks_total = Counter(
            "ds_bot_background_tasks_total",
            "Total number of background task executions",
            ["task_type", "status"],
        )
        self.background_task_duration_seconds = Histogram(
            "ds_bot_background_task_duration_seconds",
            "Background task execution duration in seconds",
            ["task_type"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        # Discord Events Metrics
        self.discord_messages_total = Counter(
            "ds_bot_discord_messages_total",
            "Total number of Discord messages received",
        )
        self.discord_reactions_total = Counter(
            "ds_bot_discord_reactions_total",
            "Total number of Discord reactions",
        )
        self.discord_member_joins_total = Counter(
            "ds_bot_discord_member_joins_total",
            "Total number of member joins",
        )
        self.discord_member_leaves_total = Counter(
            "ds_bot_discord_member_leaves_total",
            "Total number of member leaves",
        )

        # Bot Info
        self.bot_info = Info(
            "ds_bot_info",
            "Bot information",
        )

        self._start_time = time.time()

    def update_uptime(self) -> None:
        """Update bot uptime metric."""
        uptime = time.time() - self._start_time
        self.bot_uptime_seconds.set(uptime)

    def set_bot_ready(self, ready: bool) -> None:
        """Set bot ready state."""
        self.bot_ready.set(1 if ready else 0)

    def set_shard_info(self, shard_id: int | None, shard_count: int | None) -> None:
        """Set shard information."""
        if shard_id is not None:
            self.bot_shard_id.set(shard_id)
        if shard_count is not None:
            self.bot_shard_count.set(shard_count)

    def set_guild_count(self, count: int) -> None:
        """Set guild count."""
        self.bot_guild_count.set(count)

    def set_user_count(self, count: int) -> None:
        """Set user count."""
        self.bot_user_count.set(count)

    def record_command(self, command: str, duration: float, status: str = "success") -> None:
        """Record command execution."""
        self.commands_total.labels(command=command, status=status).inc()
        self.command_duration_seconds.labels(command=command).observe(duration)

    def record_database_query(
        self,
        operation: str,
        duration: float,
        status: str = "success",
    ) -> None:
        """Record database query."""
        self.database_queries_total.labels(operation=operation, status=status).inc()
        self.database_query_duration_seconds.labels(operation=operation).observe(duration)

    def set_database_pool_metrics(
        self,
        pool_type: str,
        pool_size: int,
        active: int,
    ) -> None:
        """Set database pool metrics."""
        self.database_pool_size.labels(pool_type=pool_type).set(pool_size)
        self.database_pool_active.labels(pool_type=pool_type).set(active)

    def record_ai_agent_run(
        self,
        agent_type: str,
        duration: float,
        status: str = "success",
    ) -> None:
        """Record AI agent run."""
        self.ai_agent_runs_total.labels(agent_type=agent_type, status=status).inc()
        self.ai_agent_duration_seconds.labels(agent_type=agent_type).observe(duration)

    def record_embedding_generation(
        self,
        model: str,
        duration: float,
        status: str = "success",
    ) -> None:
        """Record embedding generation."""
        self.ai_embedding_generations_total.labels(model=model, status=status).inc()
        self.ai_embedding_duration_seconds.labels(model=model).observe(duration)

    def record_memory_capture(self, memory_type: str) -> None:
        """Record memory capture."""
        self.memory_captures_total.labels(memory_type=memory_type).inc()

    def record_memory_compression(self, status: str = "success") -> None:
        """Record memory compression."""
        self.memory_compressions_total.labels(status=status).inc()

    def record_memory_retrieval(self) -> None:
        """Record memory retrieval."""
        self.memory_retrievals_total.inc()

    def record_memory_episode_promotion(self) -> None:
        """Record episode memory promotion."""
        self.memory_episode_promotions_total.inc()

    def record_memory_operation(self, operation: str, duration: float) -> None:
        """Record memory operation duration."""
        self.memory_duration_seconds.labels(operation=operation).observe(duration)

    def record_game_session(self, action: str) -> None:
        """Record game session event."""
        self.game_sessions_total.labels(action=action).inc()

    def set_active_game_sessions(self, count: int) -> None:
        """Set active game sessions count."""
        self.game_sessions_active.set(count)

    def record_encounter(
        self,
        encounter_type: str,
        status: str = "success",
    ) -> None:
        """Record encounter event."""
        self.game_encounters_total.labels(encounter_type=encounter_type, status=status).inc()

    def record_character_action(self, action_type: str) -> None:
        """Record character action."""
        self.game_character_actions_total.labels(action_type=action_type).inc()

    def record_world_state_change(self, asset_type: str, action: str = "created") -> None:
        """Record world state change (NPC, quest, location, etc.)."""
        self.world_state_changes_total.labels(asset_type=asset_type, action=action).inc()

    def record_background_task(
        self,
        task_type: str,
        duration: float,
        status: str = "success",
    ) -> None:
        """Record background task execution."""
        self.background_tasks_total.labels(task_type=task_type, status=status).inc()
        self.background_task_duration_seconds.labels(task_type=task_type).observe(duration)

    def record_discord_message(self) -> None:
        """Record Discord message."""
        self.discord_messages_total.inc()

    def record_discord_reaction(self) -> None:
        """Record Discord reaction."""
        self.discord_reactions_total.inc()

    def record_member_join(self) -> None:
        """Record member join."""
        self.discord_member_joins_total.inc()

    def record_member_leave(self) -> None:
        """Record member leave."""
        self.discord_member_leaves_total.inc()

    def set_bot_info(self, **kwargs: str) -> None:
        """Set bot information labels."""
        self.bot_info.info(kwargs)

    @contextlib.contextmanager
    def time_operation(self, metric: Histogram, labels: dict[str, str] | None = None):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if labels:
                metric.labels(**labels).observe(duration)
            else:
                metric.observe(duration)

    @asynccontextmanager
    async def time_async_operation(
        self,
        metric: Histogram,
        labels: dict[str, str] | None = None,
    ):
        """Async context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if labels:
                metric.labels(**labels).observe(duration)
            else:
                metric.observe(duration)

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output."""
        return generate_latest(self.registry)


# Global metrics service instance
_metrics_service: MetricsService | None = None


def get_metrics_service() -> MetricsService:
    """Get global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
