---
description: "Core project standards for Quillian Undercity Discord bot - Python 3.13, discord.py, SQLModel, async patterns, and coding conventions"
alwaysApply: true
---

# Quillian Undercity: Shadows of the Syndicate - Project Standards

## Project Overview
This is a Discord bot for a narrative-driven roguelike text adventure game. The project uses Python 3.13, discord.py, SQLModel/PostgreSQL, SurrealDB, and follows modern async Python patterns.

## Core Technologies & Tools
- **Python**: 3.13+ (use modern Python features)
- **Package Manager**: uv (use `uv sync`, `uv add`, `uv run`)
- **Build System**: Pants
- **Database**: PostgreSQL (via SQLModel/SQLAlchemy) + SurrealDB
- **Discord**: discord.py 2.6.4+
- **Linting/Formatting**: Ruff (line length: 100)
- **Type Checking**: mypy (Python 3.13, strict settings)
- **Migrations**: Alembic
- **Testing**: pytest with pytest-asyncio

## Code Style & Conventions

### Naming Conventions
- **Files & Directories**: snake_case (e.g., `character_creation_modal.py`, `ds_discord_bot/`)
- **Variables & Functions**: snake_case (e.g., `get_by_id`, `postgres_manager`)
- **Classes**: PascalCase (e.g., `BaseRepository`, `DSBot`, `CharacterWidget`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SETTINGS_ID`)
- **Type Variables**: Single uppercase letter (e.g., `T`, `R`)

### Code Formatting
- Use Ruff for formatting (configured in pyproject.toml)
- Line length: 100 characters
- Use double quotes for strings
- Use spaces for indentation (4 spaces)
- Always use f-strings for string formatting (not `.format()` or `%`)

### Type Hints
- **Always** use type hints for function parameters and return types
- Use `typing.TYPE_CHECKING` for imports only needed for type checking
- Use `|` for union types (e.g., `str | None`, not `Optional[str]`)
- Use `collections.abc` for generic types (e.g., `Callable`, `Awaitable`)
- Use `override` decorator from `typing` when overriding methods
- Prefer explicit types over `Any`; use `Any` only when necessary

### Async/Await Patterns
- All database operations must be async
- All Discord bot commands and listeners must be async
- Use `async with` for context managers (e.g., database sessions)
- Use `await` for all async operations
- Never mix sync and async code without proper handling

### Imports
- Use absolute imports (e.g., `from ds_common.models.base_model import BaseSQLModel`)
- Group imports: stdlib, third-party, first-party (ds_common, ds_discord_bot)
- Use `isort` (via Ruff) for import sorting
- Known first-party packages: `ds_common`, `ds_discord_bot`

## Architecture Patterns

### Project Structure
```
src/
├── ds_common/          # Shared models, repositories, utilities
│   ├── models/         # SQLModel classes (inherit from BaseSQLModel)
│   └── repository/     # Repository pattern for database access
└── ds_discord_bot/     # Discord bot service
    ├── extensions/     # Discord cogs/commands
    │   ├── views/      # Discord UI components (buttons, select menus)
    │   ├── dialogs/    # Discord modals
    │   └── utils/      # Bot-specific utilities
    ├── bot.py          # Main bot class (DSBot)
    └── postgres_manager.py  # Database connection manager
```

### Models (ds_common/models)
- All models inherit from `BaseSQLModel`
- Use UUID primary keys (not SurrealDB RecordID for PostgreSQL models)
- Always include `created_at` and `updated_at` (UTC timezone-aware)
- **All datetime fields must use `DateTime(timezone=True)` and `datetime.now(UTC)`** (see Datetime Fields & UTC Requirements section)
- Use SQLModel for ORM functionality
- Add docstrings to all model classes

### Repositories (ds_common/repository)
- All repositories inherit from `BaseRepository[T]`
- Use generic type parameter `T` for the model type
- All methods must be async
- Use `_with_session()` helper for session management
- Accept optional `session` parameter for transaction control
- Include comprehensive docstrings with Args and Returns

### Discord Bot Extensions
- All extensions are `commands.Cog` classes
- Initialize with `bot` and `postgres_manager` in `__init__`
- Use `app_commands` for slash commands (preferred over prefix commands)
- Use `commands.Cog.listener()` for event listeners
- Use logging via `self.logger` (created in `__init__`)
- Store channel/role references as instance variables
- Use `@override` decorator when overriding parent methods

### Discord UI Components
- Views: Inherit from `discord.ui.View` (for buttons, select menus)
- Modals: Inherit from `discord.ui.Modal` (for forms)
- Use ephemeral responses when appropriate
- Handle timeouts and errors gracefully

## Database Patterns

### PostgreSQL (Primary Database)
- Use SQLModel/SQLAlchemy ORM
- All database operations go through repositories
- Use async sessions from `PostgresManager`
- Always use transactions for multi-step operations
- Update `updated_at` timestamp on model updates
- **All datetime fields must use UTC with timezone support** (see Datetime Fields & UTC Requirements section)

### SurrealDB
- Use SurrealDB for game state, NPCs, and memory systems
- SurrealDB schemas are in `db/*.surql` files
- Use `SurrealManager` for SurrealDB connections

### Migrations
- Use Alembic for database migrations
- Migration files in `alembic/versions/`
- Always test migrations up and down
- Include descriptive migration messages

## Datetime Fields & UTC Requirements

### Critical Rule: All datetime fields MUST use UTC with timezone support

**This is a non-negotiable requirement** to prevent timezone-related bugs and ensure consistent behavior across different environments.

### Model Field Requirements

1. **All datetime fields must specify timezone support:**
   ```python
   from datetime import UTC, datetime
   from sqlalchemy import DateTime
   from sqlmodel import Field
   
   # ✅ CORRECT: Uses timezone-aware datetime with UTC
   timestamp: datetime = Field(
       default_factory=lambda: datetime.now(UTC),
       sa_type=DateTime(timezone=True),
       description="When event occurred (UTC)",
   )
   
   # ❌ WRONG: Missing timezone support
   timestamp: datetime = Field(
       default_factory=lambda: datetime.now(UTC),
       description="When event occurred",
   )
   ```

2. **Always use `datetime.now(UTC)` for default values:**
   ```python
   # ✅ CORRECT
   created_at: datetime = Field(
       default_factory=lambda: datetime.now(UTC),
       sa_type=DateTime(timezone=True),
   )
   
   # ❌ WRONG: Using naive datetime
   created_at: datetime = Field(
       default_factory=datetime.now,  # Missing UTC
   )
   ```

3. **For nullable datetime fields:**
   ```python
   # ✅ CORRECT
   expires_at: datetime | None = Field(
       default=None,
       sa_type=DateTime(timezone=True),
       description="When this expires (UTC)",
   )
   ```

4. **When using `sa_column` instead of `sa_type`:**
   ```python
   from sqlalchemy import Column, DateTime
   
   # ✅ CORRECT
   last_active: datetime = Field(
       sa_column=Column(DateTime(timezone=True)),
   )
   ```

### Migration Requirements

**All datetime columns in Alembic migrations must use `timezone=True`:**

```python
# ✅ CORRECT
sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False)

# ❌ WRONG: Missing timezone=True
sa.Column('timestamp', sa.DateTime(), nullable=False)
```

### Code Patterns

1. **When creating datetime values in code:**
   ```python
   from datetime import UTC, datetime
   
   # ✅ CORRECT: Always use UTC
   now = datetime.now(UTC)
   
   # ❌ WRONG: Don't use naive datetime
   now = datetime.now()  # Missing UTC
   ```

2. **When comparing datetimes:**
   ```python
   # ✅ CORRECT: Both are timezone-aware
   if event_time > datetime.now(UTC):
       # ...
   
   # ❌ WRONG: Mixing timezone-aware and naive
   if event_time > datetime.now():  # Can cause errors
       # ...
   ```

3. **When converting to naive for database comparison (if needed):**
   ```python
   # Only if database column is TIMESTAMP WITHOUT TIME ZONE (should be avoided)
   # Convert timezone-aware to naive UTC before comparison
   naive_utc = datetime.now(UTC).replace(tzinfo=None)
   ```

### Verification Checklist

When adding or modifying datetime fields:

- [ ] Field uses `sa_type=DateTime(timezone=True)` or `sa_column=Column(DateTime(timezone=True))`
- [ ] Default values use `datetime.now(UTC)` (not `datetime.now()`)
- [ ] Field description mentions "(UTC)" for clarity
- [ ] Migration uses `sa.DateTime(timezone=True)` (not `sa.DateTime()`)
- [ ] All datetime operations in code use `datetime.now(UTC)`
- [ ] No mixing of timezone-aware and naive datetimes

### Why This Matters

- **Consistency**: All timestamps are stored in UTC, eliminating timezone confusion
- **Database Compatibility**: PostgreSQL `TIMESTAMP WITH TIME ZONE` properly handles timezone conversions
- **Bug Prevention**: Prevents "can't subtract offset-naive and offset-aware datetimes" errors
- **Portability**: Works correctly across different server timezones
- **Future-Proofing**: Makes it easier to support multiple timezones in the UI layer later

### Examples of Correct Implementations

See these models for reference:
- `BaseSQLModel` (`base_model.py`) - `created_at`, `updated_at`
- `GameTime` (`game_time.py`) - `current_game_time`, `epoch_start`, `last_shutdown_time`
- `GameSettings` (`game_settings.py`) - `game_epoch_start`
- `SessionMemory` (`session_memory.py`) - `timestamp`, `expires_at`
- `EpisodeMemory` (`episode_memory.py`) - `expires_at`

## Error Handling & Logging

### Logging
- Use `logging.getLogger(__name__)` in each module
- Store logger as instance variable: `self.logger: logging.Logger`
- Use appropriate log levels:
  - `DEBUG`: Detailed information for debugging
  - `INFO`: General informational messages
  - `WARNING`: Warning messages for potential issues
  - `ERROR`: Error messages for failures
- Include context in log messages (IDs, names, etc.)

### Error Handling
- Use try/except blocks for expected errors
- Log errors with full traceback when appropriate
- Use specific exception types when possible
- Don't silently swallow exceptions unless intentional
- Provide user-friendly error messages for Discord interactions

## Testing

### Test Structure
- Unit tests: Test individual functions/classes in isolation
- Integration tests: Test service interactions
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Test Patterns
- Use pytest fixtures for common setup
- Use `pytest-asyncio` for async tests
- Mock external dependencies (Discord API, database)
- Use `pytest-cov` for coverage reporting
- Aim for high test coverage on business logic

## Documentation

### Docstrings
- Add docstrings to all public functions, classes, and methods
- Use Google-style docstrings or NumPy-style
- Include:
  - Brief description
  - Args section (for functions/methods)
  - Returns section (for functions/methods)
  - Raises section (if applicable)

### Comments
- Write self-documenting code (prefer clear code over comments)
- Add comments for complex logic or non-obvious decisions
- Keep comments up-to-date with code changes

## Dependencies & Environment

### Adding Dependencies
- Use `uv add <package>` for runtime dependencies
- Use `uv add --dev <package>` for development dependencies
- Update `pyproject.toml` (uv handles this automatically)
- Run `uv sync` after adding dependencies

### Environment Variables
- Use `.env` file for configuration (see `.env.example`)
- Never commit `.env` file
- Use `python-dotenv` to load environment variables
- Validate required environment variables at startup

## Common Patterns & Best Practices

### Repository Pattern
```python
class MyRepository(BaseRepository[MyModel]):
    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, MyModel)
    
    async def custom_method(self, session: AsyncSession | None = None) -> MyModel | None:
        # Implementation
```

### Discord Command Pattern
```python
@character.command(name="action", description="Description")
async def action_command(self, interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    # Implementation
    await interaction.followup.send("Response")
```

### Model Pattern
```python
class MyModel(BaseSQLModel, table=True):
    """Description of the model."""
    
    field_name: str = Field(description="Field description")
```

## Things to Avoid

- ❌ Don't use `print()` for logging (use `self.logger`)
- ❌ Don't use sync database operations (always use async)
- ❌ Don't hardcode IDs or magic numbers (use constants or config)
- ❌ Don't commit secrets or tokens to git
- ❌ Don't use `Any` type without justification
- ❌ Don't ignore type checking errors
- ❌ Don't create circular imports
- ❌ Don't use global state (pass dependencies through constructors)
- ❌ Don't mix timezones (always use UTC with `DateTime(timezone=True)` in models and migrations)
- ❌ Don't skip error handling

## When Making Changes

1. **Run linting**: `uv run ruff check .` and `uv run ruff format .`
2. **Run type checking**: `uv run mypy src/`
3. **Run tests**: `uv run pytest`
4. **Check migrations**: Ensure Alembic migrations are up-to-date
5. **Update documentation**: Update docstrings and README if needed
6. **Test Discord commands**: Test in development environment

## Quick Reference

- **Run bot**: `uv run bot`
- **Add dependency**: `uv add <package>`
- **Format code**: `uv run ruff format .`
- **Lint code**: `uv run ruff check .`
- **Type check**: `uv run mypy src/`
- **Run tests**: `uv run pytest`
- **Create migration**: `alembic revision --autogenerate -m "description"`
- **Apply migrations**: `alembic upgrade head`


