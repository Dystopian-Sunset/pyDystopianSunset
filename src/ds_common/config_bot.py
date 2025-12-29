"""
Bot configuration module for loading TOML-based configuration with environment variable overrides.

This module provides configuration for the Discord bot application. If other services
(e.g., backend API, web frontend) are added in the future, they should have their own
config modules (e.g., config_backend, config_web) to avoid naming conflicts.

Configuration is loaded in the following order (later values override earlier ones):
1. Default values (hardcoded in this module)
2. config.toml file (if it exists)
3. Environment variables (override TOML values)

⚠️  SECURITY NOTE:
Secrets (tokens, passwords, API keys) should be stored in environment variables (.env file)
rather than in config.toml, especially if config.toml is committed to version control.
Environment variables provide better security isolation and are easier to manage in production.
"""

import logging
import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python
    except ImportError:
        tomllib = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


class Config:
    """Application configuration with TOML and environment variable support."""

    def __init__(self, config_path: Path | str | None = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config.toml file. If None, looks for config.toml in:
                - Current working directory
                - Project root (parent of src/)
        """
        # Default configuration values
        self._config: dict[str, Any] = {
            "discord": {
                "token": "",
                "app_id": "",
                "app_public_key": "",
                "extensions": [],  # Empty list means load all
            },
            "postgres": {
                "host": "localhost",
                "port": 5432,
                "database": "game",
                "user": "postgres",
                "password": "postgres",
                "pool_size": 5,
                "max_overflow": 10,
                "echo": False,
                "read_replica": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 5432,
                    "database": "game",
                    "user": "postgres",
                    "password": "postgres",
                    "pool_size": 5,
                    "max_overflow": 10,
                },
            },
            "game": {
                "session_category_name": "Speakeasy",
                "session_join_channel_name": "Join-to-Play",
                "service_announcements_channel_name": "📟-service-announcements",
                "rules_channel_name": "📜-rules",
                "game_name": "Quillian Undercity",
                "game_subtitle": "Shadows of the Syndicate",
            },
            "role_management": {
                "player_role_name": "citizen",
                "player_role_message_ids": [
                    1454151158640939293,
                    1454151450425823263,
                ],
                "gm_role_name": "GM",
                "moderator_role_name": "moderator",
            },
            "ai": {
                "gm": {
                    "model_name": "gpt-oss:latest",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "",
                    "system_prompt_path": "",
                    # Prompt theme/path for modular prompts
                    # Can be a theme name (e.g., "dystopian_sunset") or full path
                    # If theme name, looks in extensions/prompts/{theme}/
                    # If full path, uses that path directly
                    "prompt_theme": "dystopian_sunset",
                },
                "embedding": {
                    "base_url": "",
                    "api_key": "",
                    "model": "nomic-embed-text",
                    "dimensions": 768,
                },
            },
            "redis": {
                "url": "redis://localhost:6379",
                "db_prompt_analyzer": 0,
                "db_memory": 1,
            },
            "prompt_analyzer": {
                "use_ai": True,
                "ai_threshold": 0.7,
                "ai_validate": True,
                "embedding_model": "text-embedding-3-small",
                "embedding_dimensions": 1536,
                "keywords_only": False,
                "ai_fallback_only": False,
            },
            "conversation_classifier": {
                "enabled": True,
                "use_ai": True,
                "ai_threshold": 0.7,
                "keywords_only": False,
                "skip_threshold": 0.8,
            },
            "memory": {
                "compression": {
                    "max_memories": 12,
                    "max_recent_memories": 8,
                    "importance_threshold": 0.3,
                    "recent_cutoff_minutes": 30,
                    "description_truncate_length": 400,
                },
                "environmental_items": {
                    "lookback_minutes": 30,
                },
            },
            "logging": {
                "level": "INFO",
            },
            "metrics": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8000,
            },
        }

        # Load TOML config if available
        if tomllib:
            config_file = self._find_config_file(config_path)
            if config_file and config_file.exists():
                try:
                    with open(config_file, "rb") as f:
                        toml_config = tomllib.load(f)
                        self._merge_config(self._config, toml_config)
                        logger.info(f"Loaded configuration from {config_file}")
                except Exception as e:
                    logger.warning(f"Failed to load config.toml: {e}")
        else:
            logger.warning(
                "tomllib not available. Install 'tomli' for TOML support: pip install tomli"
            )

        # Override with environment variables
        self._load_from_env()

    def _find_config_file(self, config_path: Path | str | None) -> Path | None:
        """Find config.toml file."""
        if config_path:
            return Path(config_path)

        # Look in current directory
        cwd_config = Path("config.toml")
        if cwd_config.exists():
            return cwd_config

        # Look in project root (parent of src/)
        current = Path(__file__).resolve()
        # Navigate from src/ds_common/config_bot.py to project root
        project_root = current.parent.parent.parent
        project_config = project_root / "config.toml"
        if project_config.exists():
            return project_config

        return None

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _get_env(self, new_name: str, old_name: str | None = None) -> str | None:
        """
        Get environment variable, checking new name first, then old name for backward compatibility.

        Args:
            new_name: New normalized environment variable name (DS_ prefix)
            old_name: Old environment variable name (for backward compatibility)

        Returns:
            Environment variable value or None
        """
        value = os.getenv(new_name)
        if value is not None:
            return value
        if old_name:
            value = os.getenv(old_name)
            if value is not None:
                logger.warning(
                    f"Environment variable {old_name} is deprecated. Please use {new_name} instead."
                )
                return value
        return None

    def _load_from_env(self) -> None:
        """Load configuration from environment variables (override TOML)."""
        # Discord
        if token := self._get_env("DS_DISCORD_TOKEN"):
            self._config["discord"]["token"] = token
        if app_id := self._get_env("DS_DISCORD_APP_ID"):
            self._config["discord"]["app_id"] = app_id
        if app_key := self._get_env("DS_DISCORD_APP_PUBLIC_KEY"):
            self._config["discord"]["app_public_key"] = app_key
        if extensions := self._get_env("DS_EXTENSIONS"):
            self._config["discord"]["extensions"] = [
                ext.strip().upper() for ext in extensions.split(",") if ext.strip()
            ]

        # PostgreSQL
        if host := self._get_env("DS_POSTGRES_HOST"):
            self._config["postgres"]["host"] = host
        if port := self._get_env("DS_POSTGRES_PORT"):
            self._config["postgres"]["port"] = int(port)
        if database := self._get_env("DS_POSTGRES_DATABASE"):
            self._config["postgres"]["database"] = database
        if user := self._get_env("DS_POSTGRES_USER"):
            self._config["postgres"]["user"] = user
        if password := self._get_env("DS_POSTGRES_PASSWORD"):
            self._config["postgres"]["password"] = password
        if pool_size := self._get_env("DS_POSTGRES_POOL_SIZE"):
            self._config["postgres"]["pool_size"] = int(pool_size)
        if max_overflow := self._get_env("DS_POSTGRES_MAX_OVERFLOW"):
            self._config["postgres"]["max_overflow"] = int(max_overflow)
        if echo := self._get_env("DS_POSTGRES_ECHO"):
            self._config["postgres"]["echo"] = echo.lower() == "true"

        # PostgreSQL Read Replica
        if enabled := self._get_env("DS_POSTGRES_READ_REPLICA_ENABLED"):
            self._config["postgres"]["read_replica"]["enabled"] = enabled.lower() == "true"
        if host := self._get_env("DS_POSTGRES_READ_REPLICA_HOST"):
            self._config["postgres"]["read_replica"]["host"] = host
        if port := self._get_env("DS_POSTGRES_READ_REPLICA_PORT"):
            self._config["postgres"]["read_replica"]["port"] = int(port)
        if database := self._get_env("DS_POSTGRES_READ_REPLICA_DATABASE"):
            self._config["postgres"]["read_replica"]["database"] = database
        if user := self._get_env("DS_POSTGRES_READ_REPLICA_USER"):
            self._config["postgres"]["read_replica"]["user"] = user
        if password := self._get_env("DS_POSTGRES_READ_REPLICA_PASSWORD"):
            self._config["postgres"]["read_replica"]["password"] = password
        if pool_size := self._get_env("DS_POSTGRES_READ_REPLICA_POOL_SIZE"):
            self._config["postgres"]["read_replica"]["pool_size"] = int(pool_size)
        if max_overflow := self._get_env("DS_POSTGRES_READ_REPLICA_MAX_OVERFLOW"):
            self._config["postgres"]["read_replica"]["max_overflow"] = int(max_overflow)

        # Game
        if category := self._get_env("DS_GAME_SESSION_CATEGORY_NAME", "GAME_SESSION_CATEGORY_NAME"):
            self._config["game"]["session_category_name"] = category
        if channel := self._get_env(
            "DS_GAME_SESSION_JOIN_CHANNEL_NAME", "GAME_SESSION_JOIN_CHANNEL_NAME"
        ):
            self._config["game"]["session_join_channel_name"] = channel
        if service_channel := self._get_env("DS_GAME_SERVICE_ANNOUNCEMENTS_CHANNEL_NAME"):
            self._config["game"]["service_announcements_channel_name"] = service_channel
        if rules_channel := self._get_env("DS_GAME_RULES_CHANNEL_NAME"):
            self._config["game"]["rules_channel_name"] = rules_channel
        if game_name := self._get_env("DS_GAME_NAME"):
            self._config["game"]["game_name"] = game_name
        if game_subtitle := self._get_env("DS_GAME_SUBTITLE"):
            self._config["game"]["game_subtitle"] = game_subtitle

        # Role Management
        if player_role_name := self._get_env("DS_ROLE_MANAGEMENT_PLAYER_ROLE_NAME"):
            self._config["role_management"]["player_role_name"] = player_role_name
        if player_message_ids := self._get_env("DS_ROLE_MANAGEMENT_PLAYER_ROLE_MESSAGE_IDS"):
            # Parse comma-separated list of message IDs
            self._config["role_management"]["player_role_message_ids"] = [
                int(msg_id.strip()) for msg_id in player_message_ids.split(",") if msg_id.strip()
            ]
        if gm_role_name := self._get_env("DS_ROLE_MANAGEMENT_GM_ROLE_NAME"):
            self._config["role_management"]["gm_role_name"] = gm_role_name
        if moderator_role_name := self._get_env("DS_ROLE_MANAGEMENT_MODERATOR_ROLE_NAME"):
            self._config["role_management"]["moderator_role_name"] = moderator_role_name

        # AI Game Master
        if model := self._get_env("DS_AI_GM_MODEL_NAME", "DB_GM_MODEL_NAME"):
            self._config["ai"]["gm"]["model_name"] = model
        if base_url := self._get_env("DS_AI_GM_BASE_URL", "DB_GM_BASE_URL"):
            self._config["ai"]["gm"]["base_url"] = base_url
        if api_key := self._get_env("DS_AI_GM_API_KEY", "OPENAI_API_KEY"):
            self._config["ai"]["gm"]["api_key"] = api_key
        if prompt_path := self._get_env("DS_AI_GM_SYSTEM_PROMPT_PATH", "DB_GM_SYSTEM_PROMPT_PATH"):
            self._config["ai"]["gm"]["system_prompt_path"] = prompt_path

        # Prompt theme/path
        if prompt_theme := self._get_env("DS_AI_GM_PROMPT_THEME"):
            self._config["ai"]["gm"]["prompt_theme"] = prompt_theme

        # AI Embedding
        if embedding_base_url := self._get_env("DS_AI_EMBEDDING_BASE_URL", "DB_EMBEDDING_BASE_URL"):
            self._config["ai"]["embedding"]["base_url"] = embedding_base_url
        if api_key := self._get_env("DS_AI_EMBEDDING_API_KEY", "OPENAI_API_KEY"):
            self._config["ai"]["embedding"]["api_key"] = api_key
        if embedding_model := self._get_env("DS_AI_EMBEDDING_MODEL"):
            self._config["ai"]["embedding"]["model"] = embedding_model
        if embedding_dimensions := self._get_env("DS_AI_EMBEDDING_DIMENSIONS"):
            self._config["ai"]["embedding"]["dimensions"] = int(embedding_dimensions)

        # Redis
        if redis_url := self._get_env("DS_REDIS_URL", "REDIS_URL"):
            self._config["redis"]["url"] = redis_url
        if db_prompt := self._get_env("DS_REDIS_DB_PROMPT_ANALYZER"):
            self._config["redis"]["db_prompt_analyzer"] = int(db_prompt)
        if db_memory := self._get_env("DS_REDIS_DB_MEMORY"):
            self._config["redis"]["db_memory"] = int(db_memory)

        # Prompt Analyzer
        if use_ai := self._get_env("DS_PROMPT_ANALYZER_USE_AI", "DB_PROMPT_ANALYZER_USE_AI"):
            self._config["prompt_analyzer"]["use_ai"] = use_ai.lower() == "true"
        if threshold := self._get_env(
            "DS_PROMPT_ANALYZER_AI_THRESHOLD", "DB_PROMPT_ANALYZER_AI_THRESHOLD"
        ):
            self._config["prompt_analyzer"]["ai_threshold"] = float(threshold)
        if validate := self._get_env(
            "DS_PROMPT_ANALYZER_AI_VALIDATE", "DB_PROMPT_ANALYZER_AI_VALIDATE"
        ):
            self._config["prompt_analyzer"]["ai_validate"] = validate.lower() == "true"
        if model := self._get_env(
            "DS_PROMPT_ANALYZER_EMBEDDING_MODEL", "DB_PROMPT_ANALYZER_EMBEDDING_MODEL"
        ):
            self._config["prompt_analyzer"]["embedding_model"] = model
        if dimensions := self._get_env(
            "DS_PROMPT_ANALYZER_EMBEDDING_DIMENSIONS", "DB_PROMPT_ANALYZER_EMBEDDING_DIMENSIONS"
        ):
            self._config["prompt_analyzer"]["embedding_dimensions"] = int(dimensions)
        if keywords_only := self._get_env(
            "DS_PROMPT_ANALYZER_KEYWORDS_ONLY", "DB_PROMPT_ANALYZER_KEYWORDS_ONLY"
        ):
            self._config["prompt_analyzer"]["keywords_only"] = keywords_only.lower() == "true"
        if fallback_only := self._get_env(
            "DS_PROMPT_ANALYZER_AI_FALLBACK_ONLY", "DB_PROMPT_ANALYZER_AI_FALLBACK_ONLY"
        ):
            self._config["prompt_analyzer"]["ai_fallback_only"] = fallback_only.lower() == "true"

        # Conversation Classifier
        if enabled := self._get_env("DS_CONVERSATION_CLASSIFIER_ENABLED"):
            self._config["conversation_classifier"]["enabled"] = enabled.lower() == "true"
        if use_ai := self._get_env("DS_CONVERSATION_CLASSIFIER_USE_AI"):
            self._config["conversation_classifier"]["use_ai"] = use_ai.lower() == "true"
        if threshold := self._get_env("DS_CONVERSATION_CLASSIFIER_AI_THRESHOLD"):
            self._config["conversation_classifier"]["ai_threshold"] = float(threshold)
        if keywords_only := self._get_env("DS_CONVERSATION_CLASSIFIER_KEYWORDS_ONLY"):
            self._config["conversation_classifier"]["keywords_only"] = (
                keywords_only.lower() == "true"
            )
        if skip_threshold := self._get_env("DS_CONVERSATION_CLASSIFIER_SKIP_THRESHOLD"):
            self._config["conversation_classifier"]["skip_threshold"] = float(skip_threshold)

        # Memory Compression
        if max_memories := self._get_env("DS_MEMORY_MAX_MEMORIES"):
            self._config["memory"]["compression"]["max_memories"] = int(max_memories)
        if max_recent := self._get_env("DS_MEMORY_MAX_RECENT_MEMORIES"):
            self._config["memory"]["compression"]["max_recent_memories"] = int(max_recent)
        if importance_threshold := self._get_env("DS_MEMORY_IMPORTANCE_THRESHOLD"):
            self._config["memory"]["compression"]["importance_threshold"] = float(
                importance_threshold
            )
        if recent_cutoff := self._get_env("DS_MEMORY_RECENT_CUTOFF_MINUTES"):
            self._config["memory"]["compression"]["recent_cutoff_minutes"] = int(recent_cutoff)
        if truncate_length := self._get_env("DS_MEMORY_DESCRIPTION_TRUNCATE_LENGTH"):
            self._config["memory"]["compression"]["description_truncate_length"] = int(
                truncate_length
            )
        if lookback_minutes := self._get_env("DS_MEMORY_ENVIRONMENTAL_ITEMS_LOOKBACK_MINUTES"):
            self._config["memory"]["environmental_items"]["lookback_minutes"] = int(
                lookback_minutes
            )

        # Logging
        if log_level := self._get_env("DS_LOG_LEVEL"):
            self._config["logging"]["level"] = log_level.upper()

        # Metrics
        if enabled := self._get_env("DS_METRICS_ENABLED"):
            self._config["metrics"]["enabled"] = enabled.lower() == "true"
        if host := self._get_env("DS_METRICS_HOST"):
            self._config["metrics"]["host"] = host
        if port := self._get_env("DS_METRICS_PORT"):
            self._config["metrics"]["port"] = int(port)

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get configuration value using dot-notation keys.

        Args:
            *keys: Nested keys, e.g., 'ai', 'gm', 'model_name'
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get('ai', 'gm', 'model_name')
            config.get('postgres', 'host')
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def discord_token(self) -> str:
        """Discord bot token."""
        return self.get("discord", "token", default="")

    @property
    def discord_app_id(self) -> str:
        """Discord application ID."""
        return self.get("discord", "app_id", default="")

    @property
    def discord_app_public_key(self) -> str:
        """Discord application public key."""
        return self.get("discord", "app_public_key", default="")

    @property
    def discord_extensions(self) -> list[str]:
        """List of extensions to load (empty = load all)."""
        return self.get("discord", "extensions", default=[])

    @property
    def postgres_host(self) -> str:
        """PostgreSQL host."""
        return self.get("postgres", "host", default="localhost")

    @property
    def postgres_port(self) -> int:
        """PostgreSQL port."""
        return self.get("postgres", "port", default=5432)

    @property
    def postgres_database(self) -> str:
        """PostgreSQL database name."""
        return self.get("postgres", "database", default="game")

    @property
    def postgres_user(self) -> str:
        """PostgreSQL user."""
        return self.get("postgres", "user", default="postgres")

    @property
    def postgres_password(self) -> str:
        """PostgreSQL password."""
        return self.get("postgres", "password", default="postgres")

    @property
    def postgres_pool_size(self) -> int:
        """PostgreSQL connection pool size."""
        return self.get("postgres", "pool_size", default=5)

    @property
    def postgres_max_overflow(self) -> int:
        """PostgreSQL max overflow connections."""
        return self.get("postgres", "max_overflow", default=10)

    @property
    def postgres_echo(self) -> bool:
        """Enable SQL query logging."""
        return self.get("postgres", "echo", default=False)

    @property
    def postgres_read_replica_enabled(self) -> bool:
        """Whether read replica is enabled."""
        return self.get("postgres", "read_replica", "enabled", default=False)

    @property
    def postgres_read_replica_host(self) -> str | None:
        """Read replica host."""
        if not self.postgres_read_replica_enabled:
            return None
        return self.get("postgres", "read_replica", "host", default=None)

    @property
    def postgres_read_replica_port(self) -> int | None:
        """Read replica port."""
        if not self.postgres_read_replica_enabled:
            return None
        return self.get("postgres", "read_replica", "port", default=None)

    @property
    def postgres_read_replica_database(self) -> str | None:
        """Read replica database name."""
        if not self.postgres_read_replica_enabled:
            return None
        return self.get("postgres", "read_replica", "database", default=None)

    @property
    def postgres_read_replica_user(self) -> str | None:
        """Read replica user."""
        if not self.postgres_read_replica_enabled:
            return None
        return self.get("postgres", "read_replica", "user", default=None)

    @property
    def postgres_read_replica_password(self) -> str | None:
        """Read replica password."""
        if not self.postgres_read_replica_enabled:
            return None
        return self.get("postgres", "read_replica", "password", default=None)

    @property
    def postgres_read_replica_pool_size(self) -> int:
        """Read replica connection pool size."""
        return self.get("postgres", "read_replica", "pool_size", default=5)

    @property
    def postgres_read_replica_max_overflow(self) -> int:
        """Read replica maximum overflow connections."""
        return self.get("postgres", "read_replica", "max_overflow", default=10)

    @property
    def game_session_category_name(self) -> str:
        """Game session category name."""
        return self.get("game", "session_category_name", default="Speakeasy")

    @property
    def game_session_join_channel_name(self) -> str:
        """Game session join channel name."""
        return self.get("game", "session_join_channel_name", default="Join-to-Play")

    @property
    def game_service_announcements_channel_name(self) -> str:
        """Service announcements channel name."""
        return self.get(
            "game", "service_announcements_channel_name", default="📟-service-announcements"
        )

    @property
    def game_rules_channel_name(self) -> str:
        """Rules channel name."""
        return self.get("game", "rules_channel_name", default="📜-rules")

    @property
    def game_name(self) -> str:
        """Game name (used in UI elements, prompts, etc.)."""
        return self.get("game", "game_name", default="Quillian Undercity")

    @property
    def game_subtitle(self) -> str:
        """Game subtitle (used in UI elements like footers)."""
        return self.get("game", "game_subtitle", default="Shadows of the Syndicate")

    @property
    def role_management_player_role_name(self) -> str:
        """Player role name (base role players receive after onboarding)."""
        return self.get("role_management", "player_role_name", default="citizen")

    @property
    def role_management_player_role_message_ids(self) -> list[int]:
        """List of message IDs that require reactions for player role."""
        return self.get("role_management", "player_role_message_ids", default=[])

    @property
    def role_management_gm_role_name(self) -> str:
        """GM role name."""
        return self.get("role_management", "gm_role_name", default="GM")

    @property
    def role_management_moderator_role_name(self) -> str:
        """Moderator role name."""
        return self.get("role_management", "moderator_role_name", default="moderator")

    @property
    def ai_gm_model_name(self) -> str:
        """AI Game Master model name."""
        return self.get("ai", "gm", "model_name", default="gpt-oss:latest")

    @property
    def ai_gm_base_url(self) -> str:
        """AI Game Master base URL."""
        return self.get("ai", "gm", "base_url", default="http://localhost:11434/v1")

    @property
    def ai_gm_api_key(self) -> str:
        """AI Game Master API key."""
        return self.get("ai", "gm", "api_key", default="")

    @property
    def ai_gm_system_prompt_path(self) -> str:
        """AI Game Master system prompt path."""
        return self.get("ai", "gm", "system_prompt_path", default="")

    @property
    def ai_gm_prompt_theme(self) -> str:
        """
        AI Game Master prompt theme/path.
        
        Can be a theme name (e.g., "dystopian_sunset") which will look in
        extensions/prompts/{theme}/, or a full path to a prompt directory.
        """
        return self.get("ai", "gm", "prompt_theme", default="dystopian_sunset")

    @property
    def ai_embedding_base_url(self) -> str:
        """AI embedding service base URL."""
        return self.get("ai", "embedding", "base_url", default="")

    @property
    def ai_embedding_api_key(self) -> str:
        """AI embedding service API key."""
        return self.get("ai", "embedding", "api_key", default="")

    @property
    def ai_embedding_model(self) -> str:
        """AI embedding service model name (for memory system)."""
        return self.get("ai", "embedding", "model", default="nomic-embed-text")

    @property
    def ai_embedding_dimensions(self) -> int:
        """AI embedding service dimensions (for memory system)."""
        return self.get("ai", "embedding", "dimensions", default=768)

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        return self.get("redis", "url", default="redis://localhost:6379")

    @property
    def redis_db_prompt_analyzer(self) -> int:
        """Redis database number for prompt analyzer embeddings."""
        return self.get("redis", "db_prompt_analyzer", default=0)

    @property
    def redis_db_memory(self) -> int:
        """Redis database number for memory system embeddings."""
        return self.get("redis", "db_memory", default=1)

    @property
    def prompt_analyzer_use_ai(self) -> bool:
        """Enable AI-based prompt analysis."""
        return self.get("prompt_analyzer", "use_ai", default=True)

    @property
    def prompt_analyzer_ai_threshold(self) -> float:
        """AI confidence threshold."""
        return self.get("prompt_analyzer", "ai_threshold", default=0.7)

    @property
    def prompt_analyzer_ai_validate(self) -> bool:
        """Use AI to validate keyword matches."""
        return self.get("prompt_analyzer", "ai_validate", default=True)

    @property
    def prompt_analyzer_embedding_model(self) -> str:
        """Embedding model name."""
        return self.get("prompt_analyzer", "embedding_model", default="text-embedding-3-small")

    @property
    def prompt_analyzer_embedding_dimensions(self) -> int:
        """Embedding dimensions."""
        return self.get("prompt_analyzer", "embedding_dimensions", default=1536)

    @property
    def prompt_analyzer_keywords_only(self) -> bool:
        """Use keywords only, disable AI."""
        return self.get("prompt_analyzer", "keywords_only", default=False)

    @property
    def prompt_analyzer_ai_fallback_only(self) -> bool:
        """Use AI only as fallback when keywords fail."""
        return self.get("prompt_analyzer", "ai_fallback_only", default=False)

    @property
    def log_level(self) -> str:
        """Logging level."""
        return self.get("logging", "level", default="INFO")

    @property
    def metrics_enabled(self) -> bool:
        """Whether metrics collection is enabled."""
        return self.get("metrics", "enabled", default=True)

    @property
    def metrics_host(self) -> str:
        """Metrics server host."""
        return self.get("metrics", "host", default="0.0.0.0")

    @property
    def metrics_port(self) -> int:
        """Metrics server port."""
        return self.get("metrics", "port", default=8000)

    # Note: Game mechanics settings (character stats, memory compression, etc.)
    # have been moved to the database (game_settings table) for real-time configuration.
    # These properties are kept for backwards compatibility fallback only.
    # New code should use bot.game_settings instead.

    @property
    def memory_max_memories(self) -> int:
        """DEPRECATED: Use bot.game_settings.memory_max_memories instead."""
        return self.get("memory", "compression", "max_memories", default=12)

    @property
    def memory_max_recent_memories(self) -> int:
        """DEPRECATED: Use bot.game_settings.memory_max_recent_memories instead."""
        return self.get("memory", "compression", "max_recent_memories", default=8)

    @property
    def memory_importance_threshold(self) -> float:
        """DEPRECATED: Use bot.game_settings.memory_importance_threshold instead."""
        return self.get("memory", "compression", "importance_threshold", default=0.3)

    @property
    def memory_recent_cutoff_minutes(self) -> int:
        """DEPRECATED: Use bot.game_settings.memory_recent_cutoff_minutes instead."""
        return self.get("memory", "compression", "recent_cutoff_minutes", default=30)

    @property
    def memory_description_truncate_length(self) -> int:
        """DEPRECATED: Use bot.game_settings.memory_description_truncate_length instead."""
        return self.get("memory", "compression", "description_truncate_length", default=400)

    @property
    def memory_environmental_items_lookback_minutes(self) -> int:
        """DEPRECATED: Use bot.game_settings.memory_environmental_items_lookback_minutes instead."""
        return self.get("memory", "environmental_items", "lookback_minutes", default=30)

    @property
    def character_stats_pool_min(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_pool_min instead."""
        return self.get("character", "stats", "pool_min", default=60)

    @property
    def character_stats_pool_max(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_pool_max instead."""
        return self.get("character", "stats", "pool_max", default=80)

    @property
    def character_stats_primary_weight(self) -> float:
        """DEPRECATED: Use bot.game_settings.character_stats_primary_weight instead."""
        return self.get("character", "stats", "primary_stat_weight", default=2.5)

    @property
    def character_stats_secondary_weight(self) -> float:
        """DEPRECATED: Use bot.game_settings.character_stats_secondary_weight instead."""
        return self.get("character", "stats", "secondary_stat_weight", default=1.0)

    @property
    def character_stats_luck_min(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_luck_min instead."""
        return self.get("character", "stats", "luck_min", default=1)

    @property
    def character_stats_luck_max(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_luck_max instead."""
        return self.get("character", "stats", "luck_max", default=10)

    @property
    def character_stats_stat_min(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_stat_min instead."""
        return self.get("character", "stats", "stat_min", default=1)

    @property
    def character_stats_stat_max(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_stat_max instead."""
        return self.get("character", "stats", "stat_max", default=20)

    @property
    def character_stats_allocation_variance(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_allocation_variance instead."""
        return self.get("character", "stats", "allocation_variance", default=2)

    @property
    def character_stats_max_rerolls(self) -> int:
        """DEPRECATED: Use bot.game_settings.character_stats_max_rerolls instead."""
        return self.get("character", "stats", "max_rerolls", default=5)


# Global config instance (initialized on first import)
_config_instance: Config | None = None


def get_config(config_path: Path | str | None = None) -> Config:
    """
    Get global configuration instance.

    Args:
        config_path: Optional path to config.toml file

    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reload_config(config_path: Path | str | None = None) -> Config:
    """
    Reload configuration (useful for testing or dynamic reloading).

    Args:
        config_path: Optional path to config.toml file

    Returns:
        New Config instance
    """
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance
