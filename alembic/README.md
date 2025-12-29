# Alembic Migrations

This directory contains Alembic database migration scripts for the DystopianSunset project.

## Setup

Alembic has been configured to work with:
- Async SQLAlchemy (using asyncpg)
- SQLModel models
- Environment variable-based database configuration

## Configuration

Database connection settings are read from environment variables (see `.env.example`):
- `DS_POSTGRES_HOST` - PostgreSQL host (default: localhost)
- `DS_POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `DS_POSTGRES_DATABASE` - Database name (default: game)
- `DS_POSTGRES_USER` - Database user (default: postgres)
- `DS_POSTGRES_PASSWORD` - Database password (default: postgres)

## Usage

### Generate a new migration

```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

**Note:** The database must be running and accessible for autogenerate to work, as it needs to compare the current database schema with the models.

### Apply migrations

```bash
uv run alembic upgrade head
```

### Rollback migrations

```bash
uv run alembic downgrade -1
```

### View migration history

```bash
uv run alembic history
```

### View current revision

```bash
uv run alembic current
```

## Models

All SQLModel models are automatically discovered from:
- `ds_common.models.base_model.BaseSQLModel` (base class)
- All models in `ds_common.models.*` that inherit from `BaseSQLModel` with `table=True`

The models are imported in `alembic/env.py` to ensure they are registered with SQLAlchemy metadata.

## Important Notes

1. **Database must be running**: Autogenerate requires a database connection to compare schemas
2. **pgvector extension**: If using vector embeddings (GameHistoryEmbedding, NPCMemory), ensure the `pgvector` extension is installed in PostgreSQL:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. **Async migrations**: Migrations run in async mode to support async SQLAlchemy operations

