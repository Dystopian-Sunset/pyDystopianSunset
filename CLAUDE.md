# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Quillian Undercity: Shadows of the Syndicate** is a narrative-driven roguelike text adventure Discord bot built with Python 3.13, discord.py, PostgreSQL+pgvector, and pydantic-ai. The bot features an AI-powered Game Master, dynamic world generation, three-tier memory architecture, and persistent multiplayer game sessions.

## Common Development Commands

**IMPORTANT: Always use `uv` to run Python commands!** The project uses `uv` for dependency management, and raw `python`/`python3` commands will fail because dependencies (discord.py, etc.) are not installed in the system Python environment. Always use:
- `uv run python ...` for running Python scripts
- `uv run pytest ...` for running tests
- `uv run mypy ...` for type checking
- Or use the `make` commands which handle this automatically

### Running the Bot
```bash
make run              # Run bot normally
make run-dev          # Run with auto-reload (requires watchfiles)
uv run python -m ds_discord_bot  # Direct invocation
```

### Code Quality
```bash
make format           # Format code with ruff
make lint             # Lint code with ruff
make lint-fix         # Lint and auto-fix issues
make typecheck        # Type check with mypy
make test             # Run tests with pytest
make test-cov         # Run tests with coverage report
make check-all        # Run format-check, lint, typecheck, and test
make fix-all          # Format and fix all linting issues
```

### Database Operations
```bash
make migrate                          # Apply pending migrations
make migrate-create MSG="description" # Create new migration
make migrate-downgrade                # Rollback last migration
make migrate-current                  # Show current revision
make migrate-history                  # Show migration history
make seed                            # Seed game data (classes, stats, etc.)
make seed-world                      # Seed world data (regions, factions, lore)
make seed-all                        # Seed both game and world data
make db-reset                        # Full reset: drop DB, recreate, migrate, seed
```

### Docker Services
```bash
make services-up      # Start PostgreSQL, Valkey, Prometheus, Grafana
make services-down    # Stop services
make services-logs    # View service logs
```

### Dependencies
```bash
make install          # Install dependencies
make install-dev      # Install with dev tools
uv add <package>      # Add runtime dependency
uv add --dev <package> # Add dev dependency
uv sync               # Sync dependencies from lock file
```

## Architecture

### Project Structure

```
src/
├── ds_common/              # Shared models, repositories, and business logic
│   ├── models/             # SQLModel database models (inherit from BaseSQLModel)
│   ├── repository/         # Data access layer (inherit from BaseRepository[T])
│   ├── combat/             # Combat system (cooldowns, XP, loot, damage, restoration)
│   ├── equipment/          # Equipment system (item management)
│   ├── memory/             # Three-tier memory system (session→episode→world)
│   │   ├── agents/         # AI agents for memory processing
│   │   └── validators/     # World consistency and geography validation
│   ├── world_generation/   # Dynamic world generation (POIs, edges, themes)
│   └── metrics/            # Prometheus metrics service
└── ds_discord_bot/         # Discord bot service
    ├── extensions/         # Discord cogs (admin, character, game, player, etc.)
    │   ├── views/          # Discord UI components (buttons, select menus)
    │   ├── dialogs/        # Discord modals (forms)
    │   ├── prompts/        # AI system prompts (modular, contextual)
    │   └── utils/          # Bot-specific utilities
    ├── bot.py              # Main DSBot class (AutoShardedBot)
    └── postgres_manager.py # Database connection manager
```

### Core Architectural Patterns

**Repository Pattern**: All database access goes through repositories inheriting from `BaseRepository[T]`. Repositories accept optional `session` parameters for transaction control and use `_with_session()` helper for session management.

**Three-Tier Memory System**:
- **Session Memory**: Raw events during gameplay (1-4 hours, stored in DB with embeddings)
- **Episode Memory**: AI-condensed narrative summaries (24-72 hours retention)
- **World Memory**: Permanent historical records with semantic search via pgvector

**AI Game Master**: Uses pydantic-ai with modular, contextual prompts. An AI prompt analyzer determines which prompt modules to load based on message intent (combat, travel, inventory, etc.). The GM has 20+ tools for world interaction (NPCs, quests, locations, inventory, cooldowns, etc.).

**Location Graph System**: Dynamically generated world with `LocationNode` (places) and `LocationEdge` (connections). Supports dynamic POI generation, travel validation, and geographic facts.

**Combat System**: Handles encounter rewards, experience distribution, loot generation, damage calculation, restoration, and character cooldowns.

**Discord Extensions**: Modular cogs for different features (character creation, game sessions, admin tools, etc.). All extensions receive `bot` and `postgres_manager` in `__init__`.

### Key Database Models

All models inherit from `BaseSQLModel` (UUID primary key, `created_at`, `updated_at`).

**Core Models**:
- `Player` - Discord users (linked to `Character` via junction table)
- `Character` - Player characters (class, stats, inventory, location)
- `CharacterClass` - Character classes with starting equipment/stats
- `GameSession` - Multiplayer game sessions with dedicated Discord channels
- `GMHistory` - AI interaction history for context preservation

**World Models**:
- `LocationNode`, `LocationEdge` - Dynamic world graph
- `LocationFact` - Geographic and lore facts
- `NPC`, `Quest`, `WorldItem` - World assets
- `WorldRegion`, `WorldEvent`, `CalendarEvent` - World state
- `GameTime` - Persistent game time with fast-forward

**Memory Models**:
- `SessionMemory`, `EpisodeMemory`, `WorldMemory` - Three-tier memory
- `MemorySettings` - Memory system configuration

### Critical Patterns

**DateTime UTC Requirement**: ALL datetime fields MUST use `sa_type=DateTime(timezone=True)` and `datetime.now(UTC)`. Never use naive datetimes. This applies to models AND Alembic migrations.

**Model Import Order**: When models have `link_model` relationships (junction tables), import order matters. Base models (e.g., `ItemTemplate`) must be imported BEFORE models that reference them (e.g., `CharacterClass`). Use the actual class for `link_model`, not strings. Import `ds_common.models` early to ensure all models are registered.

**World State Logging**: When creating/modifying world assets (NPCs, quests, locations, etc.), MUST log at INFO level with details AND record metrics via `metrics.record_world_state_change(asset_type, action)`.

**Async Everywhere**: All database operations, Discord commands, and AI interactions are async. Use `async with` for sessions, `await` for all async operations.

**Session Management**: Repositories use `_with_session()` helper. Pass `session` parameter to chain operations in transactions. Use `read_only=True` for read operations to leverage read replicas.

## Configuration

**Environment Variables** (`.env`):
- `DB_DISCORD_TOKEN` - Discord bot token
- `DB_POSTGRES_HOST`, `DB_POSTGRES_PORT`, `DB_POSTGRES_DB`, `DB_POSTGRES_USER`, `DB_POSTGRES_PASSWORD` - PostgreSQL connection
- `DB_GM_MODEL_NAME`, `DB_GM_BASE_URL` - AI model configuration (supports Ollama local models)
- `OPENAI_API_KEY` - Optional for cloud AI models
- `DB_VALKEY_HOST`, `DB_VALKEY_PORT` - Redis/Valkey for caching

**Configuration Files**:
- `config.toml` - Non-sensitive settings (channels, roles, memory system config)
- `alembic.ini` - Alembic migration settings

## Testing

```bash
make test             # Run all tests
make test-cov         # Run with coverage report
make test-fast        # Skip coverage (faster)
uv run pytest tests/  # Direct pytest invocation (use uv run!)
```

Use `pytest-asyncio` for async tests. Mock Discord API and database in tests.

## AI Game Master Development

**Creating Tools**: Add async functions to `_create_tools()` in `game.py`. Tools receive `RunContext[GMAgentDependencies]` and typed Pydantic request/response models.

**Adding Prompts**: Create markdown files in `extensions/prompts/modules/`. Update `prompt_analyzer.py` to define keywords/context that trigger the prompt. Prompts are cached in Redis and loaded dynamically based on AI-analyzed message intent.

**Agent Dependencies**: `GMAgentDependencies` dataclass provides `postgres_manager`, `game_session`, `player`, `characters`, and optional `action_character` to all tools.

## Database Migrations

**Workflow**:
1. Modify models in `ds_common/models/`
2. Create migration: `make migrate-create MSG="description"`
3. Review auto-generated migration in `alembic/versions/`
4. Ensure all datetime columns use `sa.DateTime(timezone=True)`
5. Test both upgrade and downgrade
6. Apply: `make migrate`

**Critical**: All models must be imported in `alembic/env.py` via `import ds_common.models`. Junction tables and models with `link_model` relationships require correct import order.

## Code Style

- **Python 3.13**: Use modern features (`|` for unions, generic `[T]` syntax)
- **Line Length**: 100 characters (Ruff enforced)
- **Type Hints**: Always use explicit types, avoid `Any`
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Imports**: Absolute imports, grouped (stdlib → third-party → first-party)
- **Logging**: Use `self.logger` (created via `logging.getLogger(__name__)`)
- **Docstrings**: Google-style docstrings for all public functions/classes

## Important Notes

**Never**:
- Use naive datetimes (always `DateTime(timezone=True)` and `datetime.now(UTC)`)
- Use sync database operations (always async)
- Hardcode IDs or credentials (use env vars or config)
- Skip error handling or logging
- Create circular imports
- Use `print()` for logging (use `self.logger`)
- Forget to update `updated_at` on model updates

**Always**:
- Use `uv run python ...` instead of raw `python`/`python3` commands (dependencies are managed by uv)
- Read files before modifying them
- Use `_with_session()` helper in repositories
- Pass `session` parameter for transactional operations
- Log world state changes with metrics
- Import `ds_common.models` early to register relationships
- Test migrations both up and down
- Use ephemeral responses for user-specific Discord interactions
- Handle `None` cases when querying database

## Discord Extension Development

**Extension Pattern**:
```python
class MyExtension(commands.Cog):
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        self.logger = logging.getLogger(__name__)
        self.bot = bot
        self.postgres_manager = postgres_manager

    @app_commands.command(name="cmd", description="Description")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        # Implementation
        await interaction.followup.send("Response")
```

Use `app_commands` for slash commands (preferred). Use `defer()` for long operations, `ephemeral=True` for private responses.

## Memory System

**Tiers**:
1. **Session**: `add_session_memory()` stores raw events with embeddings
2. **Episode**: Background task condenses sessions into episode summaries (24-72h TTL)
3. **World**: Promoted important memories with permanent storage

**Retrieval**: `retrieve_relevant_memories()` performs semantic search using pgvector to find contextually relevant memories. Context is prepended to AI messages.

**Processing**: Background tasks handle cleanup (expired memories), compression (session→episode), and promotion (episode→world).

## Metrics and Monitoring

Prometheus metrics exposed at `:8000/metrics`. Grafana dashboards available at `:3000` when services are running. Record custom metrics via `metrics.record_*()` methods.

## Reference Files

**Core Patterns**:
- `src/ds_common/models/base_model.py` - Base model with UTC datetime
- `src/ds_common/repository/base_repository.py` - Repository pattern
- `src/ds_discord_bot/postgres_manager.py` - Database session management
- `src/ds_discord_bot/extensions/game.py` - AI Game Master implementation
- `src/ds_common/memory/memory_processor.py` - Memory system core

**Cursor Rules**: See `.cursor/rules/` for detailed standards on models, repositories, Discord extensions, Alembic migrations, and pydantic-ai usage.
