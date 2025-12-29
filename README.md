# Quillian Undercity: Shadows of the Syndicate

Welcome to **Quillian Undercity: Shadows of the Syndicate** — a community-driven, narrative-rich roguelike adventure game designed for Discord! This project thrives on community contributions and collaboration, aiming to build an immersive world of espionage, intrigue, and emergent storytelling.

---

## 🌆 Project Vision

Quillian Undercity is a text-based adventure where players explore a sprawling, dystopian metropolis teeming with secrets, factions, and syndicates. The game leverages Discord as its primary interface, providing a social, persistent, and ever-evolving world shaped by both developers and players.

---

## 🎮 Features & Gameplay
- **Narrative-driven Roguelike:** Each playthrough offers unique stories, choices, and consequences.
- **AI-Powered Game Master:** Uses pydantic-ai with local or cloud LLMs to create dynamic, responsive narratives.
- **Intelligent Prompt System:** AI-based intent classification and contextual prompt loading for enhanced game interactions.
- **Character System:** Create and manage multiple characters with classes, stats, inventory, quests, and cooldowns.
- **Location Graph System:** Dynamic location nodes and edges with POI generation and travel validation.
- **Memory System:** Three-tier memory architecture (Session → Episode → World) with AI-powered compression and semantic search.
- **Combat System:** Encounter rewards, experience distribution, loot generation, and character cooldowns.
- **World Management:** Game time persistence, calendar events, world events, regions, and location facts.
- **Game Sessions:** Join multiplayer game sessions with player management (add/remove players) and session capacity limits.
- **Persistent World:** Player and character data stored in PostgreSQL with pgvector for semantic search and Redis caching.
- **Discord Integration:** Play directly in Discord with rich slash commands and real-time interaction.
- **Community World-Building:** Expand the world, lore, and gameplay through open contributions.

---

## 🛠️ Technologies Used
- **Python 3.13+** (core game logic)
- **discord.py** (Discord bot framework)
- **PostgreSQL + pgvector** (database with vector embeddings)
- **SQLModel** (data modeling with SQLAlchemy)
- **Alembic** (database migrations)
- **pydantic-ai** (AI agent framework for Game Master)
- **Redis** (caching for embeddings and prompts)
- **TOML** (configuration management)
- **Docker/Podman** (containerization)
- **uv** (fast Python package manager)

---

## 📁 Project Structure
```
├── src/
│   ├── ds_discord_bot/      # Discord bot service and extensions
│   │   ├── extensions/       # Bot cogs (admin, character, game, etc.)
│   │   ├── bot.py           # Main bot class
│   │   └── postgres_manager.py  # Database connection manager
│   └── ds_common/           # Shared models and utilities
│       ├── models/          # SQLModel database models
│       ├── repository/      # Data access layer
│       └── seed_data.py     # Database seeding script
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   └── env.py              # Alembic configuration
├── db/                      # Legacy SurrealDB schemas (for reference)
├── Docker/                  # Containerization files
├── docs/                    # Documentation (see below)
├── Makefile                 # Common development tasks
├── docker-compose.yaml      # Local development services
└── README.md               # This file
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.13+**
- **[uv](https://github.com/astral-sh/uv)** (recommended) or pip
- **Docker/Podman** (for PostgreSQL)
- **Discord Bot Token** ([Discord Developer Portal](https://discord.com/developers/applications))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pyDystopianSunset
   ```

2. **Install dependencies**
   ```bash
   make install-dev  # Installs all dependencies including dev tools
   # or
   uv sync --extra dev
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   cp config.example.toml config.toml
   # Edit .env for secrets (Discord token, API keys, passwords)
   # Edit config.toml for non-sensitive settings
   ```

4. **Start PostgreSQL**
   ```bash
   make services-up
   # or
   docker-compose up -d
   ```

5. **Run database migrations**
   ```bash
   make migrate
   # or
   uv run alembic upgrade head
   ```

6. **Seed initial data** (character classes, stats, etc.)
   ```bash
   make seed
   # or
   uv run python -m ds_common.seed_data
   ```

7. **Start the bot**
   ```bash
   make run
   # or for development with auto-reload
   make run-dev
   ```

For detailed setup instructions, see [docs/installation.md](docs/installation.md).

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Installation Guide](docs/installation.md)** - Detailed setup instructions
- **[Configuration](docs/configuration.md)** - Environment variables and settings
- **[Database Migrations](docs/migrations.md)** - Working with Alembic
- **[Development Guide](docs/development.md)** - Development workflow and best practices
- **[Architecture](docs/architecture.md)** - System design and structure
- **[API Reference](docs/api.md)** - Bot commands and extensions
- **[Contributing](docs/contributing.md)** - How to contribute to the project

---

## 🎯 Common Tasks

### Development
```bash
make run-dev          # Run bot with auto-reload
make format           # Format code
make lint             # Lint code
make typecheck        # Type checking
make test             # Run tests
```

### Database
```bash
make migrate          # Apply migrations
make migrate-create MSG="description"  # Create new migration
make migrate-current  # Show current revision
make seed             # Seed database with initial data
```

### Services
```bash
make services-up      # Start PostgreSQL, Valkey, Prometheus, and Grafana
make services-down    # Stop services
make services-logs    # View logs
```

### Monitoring

When services are running, you can access:
- **Prometheus**: http://localhost:9090 - Metrics collection and querying
- **Grafana**: http://localhost:3000 - Dashboards and visualization
  - Default credentials: `admin` / `admin` (change via `GRAFANA_ADMIN_PASSWORD` env var)
- **Bot Metrics**: http://localhost:8000/metrics - Direct metrics endpoint

Prometheus is configured to scrape metrics from the bot running on the host machine (port 8000). Make sure the bot is running with metrics enabled before starting the monitoring services.

**Verifying Setup:**
```bash
# Run verification script
./Docker/verify-prometheus.sh

# Or manually check Prometheus targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Check if metrics are being scraped
curl "http://localhost:9090/api/v1/query?query=ds_bot_uptime_seconds" | python3 -m json.tool
```

**Troubleshooting:**
- If Prometheus can't reach the bot, ensure the bot is running and metrics are enabled
- Check Prometheus logs: `docker-compose logs prometheus`
- Verify bot metrics endpoint: `curl http://localhost:8000/metrics`
- In Prometheus UI, go to Status → Targets to see scrape status

See `make help` for all available commands.

---

## 🤝 Contributing

We welcome contributions! Please see [docs/contributing.md](docs/contributing.md) for guidelines.

---

## 📜 License

This project is distributed under the MIT License.

**Note:** This project includes third-party packages, each with its own licensing terms. The major dependencies and their licenses are listed below:

### Major Dependencies

| Package | License | Repository |
|---------|---------|------------|
| [discord.py](https://github.com/Rapptz/discord.py) | MIT | [License](https://github.com/Rapptz/discord.py/blob/master/LICENSE) |
| [pydantic](https://github.com/pydantic/pydantic) | MIT | [License](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| [pydantic-ai](https://github.com/pydantic/pydantic-ai) | MIT | [License](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE) |
| [SQLModel](https://github.com/tiangolo/sqlmodel) | MIT | [License](https://github.com/tiangolo/sqlmodel/blob/main/LICENSE) |
| [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) | MIT | [License](https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE) |
| [Alembic](https://github.com/sqlalchemy/alembic) | MIT | [License](https://github.com/sqlalchemy/alembic/blob/main/LICENSE) |
| [asyncpg](https://github.com/MagicStack/asyncpg) | Apache 2.0 | [License](https://github.com/MagicStack/asyncpg/blob/master/LICENSE) |
| [pgvector](https://github.com/pgvector/pgvector-python) | MIT | [License](https://github.com/pgvector/pgvector-python/blob/master/LICENSE) |
| [aiofiles](https://github.com/Tinche/aiofiles) | Apache 2.0 | [License](https://github.com/Tinche/aiofiles/blob/master/LICENSE) |
| [uv](https://github.com/astral-sh/uv) | Apache 2.0 or MIT | [License](https://github.com/astral-sh/uv/blob/main/LICENSE-APACHE) |

For a complete list of all dependencies and their licenses, run:
```bash
uv pip list --format=json | jq '.[] | {name, version}'
```

---

## 🙏 Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [pydantic-ai](https://github.com/pydantic/pydantic-ai) - AI agent framework
- [SQLModel](https://github.com/tiangolo/sqlmodel) - SQL database ORM
- [Alembic](https://github.com/sqlalchemy/alembic) - Database migrations
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

> This project is built by the community, for the community. Your creativity shapes Quillian Undercity!