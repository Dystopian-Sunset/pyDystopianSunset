---
description: "Standards for Alembic database migrations - creating, testing, and managing schema changes"
globs:
  - "alembic/versions/**/*.py"
  - "alembic/env.py"
alwaysApply: false
---

# Alembic Migrations Standards

## Migration Workflow

### Creating Migrations
- Use `alembic revision --autogenerate -m "description"` for automatic migration generation
- Review auto-generated migrations carefully before applying
- Use `alembic revision -m "description"` for manual migrations when needed
- Always provide clear, descriptive migration messages

### Migration File Structure
Migration files follow this pattern:

```python
"""Brief description of the migration

Revision ID: <revision_id>
Revises: <previous_revision_id>
Create Date: <timestamp>

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '<revision_id>'
down_revision: Union[str, Sequence[str], None] = '<previous_revision_id>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Migration logic here

def downgrade() -> None:
    """Downgrade schema."""
    # Rollback logic here
```

### Reference Files
@alembic/env.py
@alembic/versions/cbfd9ede97eb_change_game_session_channel_id_to_.py
@alembic/versions/195a5d532906_change_discord_id_to_bigint_for_64_bit_.py

## Best Practices

### Upgrade Function
- Always implement `upgrade()` function
- Use descriptive comments explaining the change
- Include warnings for potentially destructive operations
- Test with real data when possible

### Downgrade Function
- Always implement `downgrade()` function for rollback capability
- Include warnings if downgrade may fail (e.g., data loss, type conversions)
- Document any data loss risks in comments

### Column Modifications
- Use `op.alter_column()` for column type changes
- Always specify `existing_type` and `type_` parameters
- Include `existing_nullable` when changing nullability
- Be careful with type conversions that may lose data

Example:
```python
def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'table_name',
        'column_name',
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=True
    )
```

### Table Operations
- Use `op.create_table()` for new tables
- Use `op.drop_table()` for table removal
- Use `op.rename_table()` for renaming
- Always handle foreign key constraints properly

### Index Operations
- Use `op.create_index()` for new indexes
- Use `op.drop_index()` for index removal
- Include index name and table name explicitly

### Foreign Key Constraints
- Create foreign keys after tables are created
- Use `op.create_foreign_key()` with explicit constraint names
- Drop foreign keys before dropping tables in downgrade

## Common Patterns

### Adding a New Column
```python
def upgrade() -> None:
    op.add_column('table_name', sa.Column('new_column', sa.String(255), nullable=True))

def downgrade() -> None:
    op.drop_column('table_name', 'new_column')
```

### Changing Column Type
```python
def upgrade() -> None:
    op.alter_column(
        'table_name',
        'column_name',
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False
    )

def downgrade() -> None:
    op.alter_column(
        'table_name',
        'column_name',
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False
    )
```

### Adding a Foreign Key
```python
def upgrade() -> None:
    op.create_foreign_key(
        'fk_name',
        'source_table',
        'target_table',
        ['source_column'],
        ['target_column']
    )

def downgrade() -> None:
    op.drop_constraint('fk_name', 'source_table', type_='foreignkey')
```

## Testing Migrations

### Before Applying
1. Review the generated migration code carefully
2. Check for potential data loss or type conversion issues
3. Test on a copy of production data if possible
4. Verify both upgrade and downgrade paths

### Applying Migrations
- Use `alembic upgrade head` to apply all pending migrations
- Use `alembic upgrade <revision>` to upgrade to a specific revision
- Use `alembic downgrade -1` to rollback one migration
- Use `alembic downgrade <revision>` to downgrade to a specific revision

### Migration History
- Use `alembic history` to view migration history
- Use `alembic current` to see current database revision
- Use `alembic heads` to see latest migration

## Important Notes

### SQLModel Integration
- All SQLModel models must be imported in `alembic/env.py`
- Models are registered with SQLModel.metadata automatically
- Use `target_metadata = SQLModel.metadata` in env.py

### Model Import Order and Relationship Resolution
**CRITICAL**: When models have relationships with `link_model` (junction tables), import order matters.

1. **Import Order Requirements**:
   - Base models (e.g., `ItemCategory`, `ItemTemplate`) must be imported BEFORE models that reference them (e.g., `CharacterClass`)
   - Junction tables should be imported after the models they link
   - This ensures SQLAlchemy can resolve relationship targets when configuring mappers

2. **Runtime Model Loading**:
   - All models must be imported at application startup before any database operations
   - Created `ds_common/models/__init__.py` to import all models in correct order
   - Import `ds_common.models` in `postgres_manager.py` and extension files that use models
   - This prevents `InvalidRequestError: failed to locate a name` when SQLAlchemy tries to resolve relationships

3. **Relationship Configuration**:
   - When using `link_model` with junction tables, ensure the target model class is available (not just a string reference)
   - Import the junction table class directly, not as a string: `link_model=CharacterClassStartingEquipment` (not `link_model="CharacterClassStartingEquipment"`)
   - Forward references in type hints (`list["ItemTemplate"]`) are fine, but `link_model` needs the actual class

4. **Example Import Order**:
   ```python
   # Correct order in models/__init__.py:
   from ds_common.models.item_category import ItemCategory
   from ds_common.models.item_template import ItemTemplate
   from ds_common.models.junction_tables import CharacterClassStartingEquipment
   from ds_common.models.character_class import CharacterClass  # Can now resolve ItemTemplate relationship
   ```

### Async Support
- The project uses async migrations (see `alembic/env.py`)
- Migrations run in async mode by default
- Use `run_async_migrations()` function pattern

### Environment Variables
- Database connection uses environment variables (see `get_database_url()` in env.py)
- Ensure `.env` file is configured before running migrations
- Connection string format: `postgresql+asyncpg://user:pass@host:port/dbname`

### Warnings
- Suppress expected warnings (e.g., circular foreign keys) in env.py
- Document any warnings that are expected and safe to ignore

## Things to Avoid

- ❌ Don't create migrations that will fail on existing data
- ❌ Don't skip implementing `downgrade()` function
- ❌ Don't use raw SQL unless absolutely necessary (prefer Alembic operations)
- ❌ Don't forget to test both upgrade and downgrade paths
- ❌ Don't create migrations that break foreign key constraints
- ❌ Don't modify existing migration files after they've been applied to production

