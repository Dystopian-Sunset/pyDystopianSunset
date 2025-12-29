# Configuration Guide

This guide covers all configuration options available for the Quillian Undercity Discord bot.

## Configuration System

The bot uses a **dual configuration system**:
1. **TOML Configuration File** (`config.toml`) - For non-sensitive settings
2. **Environment Variables** (`.env` file) - For secrets and overrides

**Key Principle**: Environment variables always override TOML values, allowing you to:
- Store non-sensitive defaults in `config.toml` (can be version controlled)
- Store secrets in `.env` (never version controlled)
- Override any setting via environment variables

### Setup

1. Copy the example files:
   ```bash
   cp config.example.toml config.toml
   cp .env.example .env
   ```

2. Edit `config.toml` for non-sensitive settings (hosts, ports, model names, etc.)

3. Edit `.env` for secrets (tokens, passwords, API keys)

## TOML Configuration (`config.toml`)

The TOML file is organized into sections:

- `[discord]` - Discord bot settings
- `[postgres]` - Database connection settings
- `[game]` - Game session settings
- `[ai.gm]` - AI Game Master settings
- `[ai.embedding]` - Embedding service settings
- `[redis]` - Redis caching settings
- `[prompt_analyzer]` - Prompt analysis settings
- `[logging]` - Logging configuration

See `config.example.toml` for a complete example with all available options.

## Environment Variables

Environment variables override TOML values and are typically set in a `.env` file. Copy `.env.example` to `.env` and customize as needed.

## Discord Bot Configuration

### Required

- **`DS_DISCORD_TOKEN`** (required)
  - Your Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
  - Example: `DS_DISCORD_TOKEN="TOKEN"`

### Optional

- **`DS_DISCORD_APP_ID`**
  - Discord Application ID (for slash commands)
  
- **`DS_DISCORD_APP_PUBLIC_KEY`**
  - Discord Application Public Key (for interactions)

- **`DS_EXTENSIONS`**
  - Comma-separated list of extensions to load
  - Available: `ADMIN`, `CHARACTER`, `GAME`, `GENERAL`, `MODERATION`, `PLAYER`, `WELCOME`
  - Leave empty to load all extensions
  - Example: `DS_EXTENSIONS="CHARACTER,GAME"`

## PostgreSQL Database Configuration

### Connection Settings

- **`DS_POSTGRES_HOST`**
  - PostgreSQL host (default: `"localhost"`)
  
- **`DS_POSTGRES_PORT`**
  - PostgreSQL port (default: `"5432"`)

- **`DS_POSTGRES_DATABASE`**
  - Database name (default: `"game"`)

- **`DS_POSTGRES_USER`**
  - Database user (default: `"postgres"`)

- **`DS_POSTGRES_PASSWORD`**
  - Database password (default: `"postgres"`)

### Connection Pool Settings

- **`DS_POSTGRES_POOL_SIZE`**
  - Connection pool size (default: `"5"`)

- **`DS_POSTGRES_MAX_OVERFLOW`**
  - Maximum overflow connections (default: `"10"`)

- **`DS_POSTGRES_ECHO`**
  - Enable SQL query logging (default: `"false"`)
  - Set to `"true"` for debugging SQL queries

## Game Configuration

- **`GAME_SESSION_CATEGORY_NAME`**
  - Discord category name for game sessions (default: `"Speakeasy"`)

- **`GAME_SESSION_JOIN_CHANNEL_NAME`**
  - Voice channel name for joining games (default: `"Join-to-Play"`)

## AI Game Master Configuration

The bot uses pydantic-ai for AI-powered game master functionality.

- **`DS_AI_GM_MODEL_NAME`** (or deprecated `DB_GM_MODEL_NAME`)
  - AI model name (default: `"gpt-oss"`)
  - For Ollama: `"gpt-oss"`, `"gemma3"`, `"llama3"`, etc.
  - For OpenAI: `"gpt-4"`, `"gpt-3.5-turbo"`, etc.

- **`DS_AI_GM_BASE_URL`** (or deprecated `DB_GM_BASE_URL`)
  - Base URL for the AI model API
  - For local Ollama: `"http://localhost:11434/v1"`
  - For OpenAI: `"https://api.openai.com/v1"`
  - For other providers: Check their API documentation

- **`DS_AI_GM_SYSTEM_PROMPT_PATH`** (or deprecated `DB_GM_SYSTEM_PROMPT_PATH`)
  - Path to custom system prompt file (optional)
  - If not set, uses default: `src/ds_discord_bot/extensions/prompts/gm_base.md`
  - Example: `DS_AI_GM_SYSTEM_PROMPT_PATH="/path/to/custom_prompt.md"`

## Embedding Service Configuration

The bot uses embeddings for semantic search in the memory system.

- **`DS_AI_EMBEDDING_BASE_URL`**
  - Base URL for embedding API (optional, for local services like Ollama)
  - For Ollama: `"http://localhost:11434/v1"`
  - For OpenAI: Leave empty (uses OpenAI's default API endpoint)

- **`DS_AI_EMBEDDING_API_KEY`**
  - OpenAI API Key (only needed if using OpenAI's embedding API)
  - Not needed if using local services like Ollama

- **`DS_AI_EMBEDDING_MODEL`**
  - Embedding model for memory system
  - For OpenAI: `"text-embedding-3-small"` (1536 dims), `"text-embedding-3-large"` (3072 dims)
  - For Ollama: `"nomic-embed-text"` (768 dims)
  - ⚠️ **IMPORTANT**: Changing the model/dimensions requires a database schema migration!
  - Use the utility script: `python scripts/manage_embedding_model.py`

- **`DS_AI_EMBEDDING_DIMENSIONS`**
  - Embedding dimensions (must match database schema)
  - ⚠️ **IMPORTANT**: This MUST match the database schema. Changing requires:
    1. Running a database migration to update vector column dimensions
    2. Regenerating all existing embeddings (they will be incompatible)
  - Common dimensions:
    - `nomic-embed-text`: 768
    - `text-embedding-3-small`: 1536
    - `text-embedding-3-large`: 3072

## Redis Configuration

Redis is used for caching embeddings and prompts to improve performance.

- **`REDIS_URL`**
  - Redis connection URL (optional)
  - Format: `"redis://localhost:6379"` or `"redis://user:password@host:port"`
  - If not set, caching is disabled

## Prompt Analyzer Configuration

The prompt analyzer uses AI to classify user intents and load contextual prompts.

- **`DS_PROMPT_ANALYZER_USE_AI`**
  - Enable AI-based intent classification (default: `true`)

- **`DS_PROMPT_ANALYZER_AI_THRESHOLD`**
  - AI confidence threshold for classification (0.0 to 1.0, default: `0.7`)

- **`DS_PROMPT_ANALYZER_AI_VALIDATE`**
  - Use AI to validate keyword matches (default: `true`)

- **`DS_PROMPT_ANALYZER_EMBEDDING_MODEL`**
  - Embedding model for prompt analyzer (input classification)
  - For OpenAI: `"text-embedding-3-small"`, `"text-embedding-3-large"`
  - For Ollama: `"nomic-embed-text"`
  - NOTE: Prompt analyzer embeddings are not stored in the database, so changing this model/dimensions does NOT require a schema migration.

- **`DS_PROMPT_ANALYZER_EMBEDDING_DIMENSIONS`**
  - Embedding dimensions for prompt analyzer
  - NOTE: These embeddings are only used for classification and are not stored, so dimensions can be changed without schema updates.

- **`DS_PROMPT_ANALYZER_KEYWORDS_ONLY`**
  - Use keywords only, disable AI (default: `false`)

- **`DS_PROMPT_ANALYZER_AI_FALLBACK_ONLY`**
  - Use AI only as fallback when keywords fail (default: `false`)

## Logging Configuration

- **`DS_LOG_LEVEL`**
  - Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `"INFO"`)
  - Use `DEBUG` for detailed logging during development

## Prometheus Metrics Configuration

The bot includes comprehensive Prometheus metrics collection for monitoring and observability.

### Configuration Options

In `config.toml`:

```toml
[metrics]
# Enable Prometheus metrics collection
enabled = true

# Metrics server host (default: 0.0.0.0)
host = "0.0.0.0"

# Metrics server port (default: 8000)
port = 8000
```

### Environment Variables

- **`DS_METRICS_ENABLED`**: Enable/disable metrics (default: `true`)
- **`DS_METRICS_HOST`**: Metrics server host (default: `"0.0.0.0"`)
- **`DS_METRICS_PORT`**: Metrics server port (default: `8000`)

### Metrics Endpoint

When enabled, metrics are exposed at:
- **Metrics**: `http://<host>:<port>/metrics` - Prometheus metrics in text format
- **Health**: `http://<host>:<port>/health` - Health check endpoint

### Available Metrics

The bot exposes comprehensive metrics across multiple categories:

#### Bot Health Metrics
- `ds_bot_uptime_seconds` - Bot uptime in seconds
- `ds_bot_ready` - Bot ready state (1 = ready, 0 = not ready)
- `ds_bot_shard_id` - Bot shard ID
- `ds_bot_shard_count` - Total number of shards
- `ds_bot_guild_count` - Number of guilds
- `ds_bot_user_count` - Number of users

#### Command Metrics
- `ds_bot_commands_total` - Total commands executed (labeled by command name and status)
- `ds_bot_command_duration_seconds` - Command execution duration (histogram)

#### Database Metrics
- `ds_bot_database_queries_total` - Total database queries (labeled by operation and status)
- `ds_bot_database_query_duration_seconds` - Query duration (histogram)
- `ds_bot_database_pool_size` - Connection pool size (labeled by pool type)
- `ds_bot_database_pool_active` - Active connections (labeled by pool type)

#### AI Operations Metrics
- `ds_bot_ai_agent_runs_total` - AI agent runs (labeled by agent type and status)
- `ds_bot_ai_agent_duration_seconds` - Agent execution duration (histogram)
- `ds_bot_ai_embedding_generations_total` - Embedding generations (labeled by model and status)
- `ds_bot_ai_embedding_duration_seconds` - Embedding generation duration (histogram)

#### Memory System Metrics
- `ds_bot_memory_captures_total` - Memory captures (labeled by memory type)
- `ds_bot_memory_compressions_total` - Memory compressions (labeled by status)
- `ds_bot_memory_retrievals_total` - Memory retrievals
- `ds_bot_memory_episode_promotions_total` - Episode memory promotions
- `ds_bot_memory_duration_seconds` - Memory operation duration (histogram, labeled by operation)

#### Game Events Metrics
- `ds_bot_game_sessions_total` - Game session events (labeled by action)
- `ds_bot_game_sessions_active` - Number of active game sessions
- `ds_bot_game_encounters_total` - Encounters (labeled by encounter type and status)
- `ds_bot_game_character_actions_total` - Character actions (labeled by action type)

#### Background Tasks Metrics
- `ds_bot_background_tasks_total` - Background task executions (labeled by task type and status)
- `ds_bot_background_task_duration_seconds` - Task execution duration (histogram)

#### Discord Events Metrics
- `ds_bot_discord_messages_total` - Discord messages received
- `ds_bot_discord_reactions_total` - Discord reactions
- `ds_bot_discord_member_joins_total` - Member joins
- `ds_bot_discord_member_leaves_total` - Member leaves

### Prometheus Scraping

To scrape metrics with Prometheus, add a job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'dystopian-sunset-bot'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboards

You can create Grafana dashboards using these metrics to visualize:
- Bot health and uptime
- Command execution rates and latencies
- Database query performance
- AI agent performance
- Memory system operations
- Game session activity
- Background task health

## Example Configuration

### Example `config.toml` (Non-sensitive settings)

```toml
[discord]
app_id = "123456789"

[postgres]
host = "localhost"
port = 5432
database = "game"
user = "postgres"
# password should be in .env file

[game]
session_category_name = "Speakeasy"
session_join_channel_name = "Join-to-Play"

[ai.gm]
model_name = "gpt-oss"
base_url = "http://localhost:11434/v1"

[ai.embedding]
base_url = "http://localhost:11434/v1"
model = "nomic-embed-text"
dimensions = 768

[redis]
url = "redis://localhost:6379"

[prompt_analyzer]
use_ai = true
ai_threshold = 0.7
embedding_model = "nomic-embed-text"
embedding_dimensions = 768

[logging]
level = "INFO"

[metrics]
enabled = true
host = "0.0.0.0"
port = 8000
```

### Example `.env` File (Secrets and overrides)

```bash
# Discord Bot (SECRETS - never commit)
DS_DISCORD_TOKEN="your_token_here"
DS_DISCORD_APP_PUBLIC_KEY="your_public_key_here"

# PostgreSQL (SECRETS)
DS_POSTGRES_PASSWORD="your_secure_password"

# AI Embedding (SECRETS - only if using OpenAI)
DS_AI_EMBEDDING_API_KEY="sk-your-openai-key"

# Redis (SECRETS - if password required)
REDIS_URL="redis://user:password@host:port"

# Overrides (optional - can override any TOML setting)
DS_AI_GM_MODEL_NAME="gpt-4"
DS_LOG_LEVEL="DEBUG"
```

## Production Considerations

### Security
- **Never commit `.env` files** to version control
- **Never commit `config.toml`** if it contains secrets
- Store non-sensitive defaults in `config.toml` (can be version controlled)
- Store all secrets in `.env` file (never version controlled)
- Use strong database passwords in production
- Rotate Discord bot tokens regularly
- Consider using secret management services (AWS Secrets Manager, HashiCorp Vault, etc.)
- Environment variables always override TOML values - use this for secrets

### Performance
- Adjust `DS_POSTGRES_POOL_SIZE` based on expected load
- Monitor database connection usage
- Use connection pooling for high-traffic deployments

### AI Model Selection
- Local models (Ollama) are free but require local GPU/CPU resources
- Cloud models (OpenAI) are paid but don't require local resources
- Consider latency and cost when choosing models

## Environment-Specific Configuration

You can use different `.env` files for different environments:

```bash
# Development
.env.development

# Production
.env.production

# Load specific environment
export $(cat .env.production | xargs)
```

Or use environment variable injection in your deployment system.

