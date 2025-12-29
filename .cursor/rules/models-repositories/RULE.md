---
description: "Standards for SQLModel models and repository pattern implementation"
globs:
  - "**/ds_common/models/**/*.py"
  - "**/ds_common/repository/**/*.py"
alwaysApply: false
---

# Models and Repositories Standards

## Models (ds_common/models)

### Base Requirements
- All models inherit from `BaseSQLModel`
- Use UUID primary keys (not SurrealDB RecordID for PostgreSQL models)
- Always include `created_at` and `updated_at` (UTC timezone-aware)
- Use SQLModel for ORM functionality
- Add docstrings to all model classes

### Model Pattern
```python
from ds_common.models.base_model import BaseSQLModel
from sqlmodel import Field

class MyModel(BaseSQLModel, table=True):
    """Description of the model."""
    
    field_name: str = Field(description="Field description")
    optional_field: str | None = Field(default=None, description="Optional field")
```

### Reference Files
@src/ds_common/models/base_model.py
@src/ds_common/models/character.py

## Repositories (ds_common/repository)

### Base Requirements
- All repositories inherit from `BaseRepository[T]`
- Use generic type parameter `T` for the model type
- All methods must be async
- Use `_with_session()` helper for session management
- Accept optional `session` parameter for transaction control
- Include comprehensive docstrings with Args and Returns

### World State Changes - Logging and Metrics
**CRITICAL**: When creating or modifying world state assets (NPCs, Quests, Locations, World Items, etc.), you MUST:
1. **Log at INFO level** with context about what was created/modified
2. **Record metrics** using `metrics.record_world_state_change(asset_type, action)`

**Examples:**
- NPC creation: Log NPC details (name, race, profession, level, location) and record `record_world_state_change("npc", "created")`
- Quest creation: Log quest details (name, tasks) and record `record_world_state_change("quest", "created")`
- Location node creation: Log location details (name, type, discovery info) and record `record_world_state_change("location_node", "created")`
- Location edge creation: Log edge details (from/to, type) and record `record_world_state_change("location_edge", "created")`

**Implementation Pattern:**
```python
from ds_common.metrics.service import get_metrics_service

class MyRepository(BaseRepository[MyModel]):
    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, MyModel)
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.metrics = get_metrics_service()
    
    async def create(self, model: MyModel, session=None):
        """Create a model and log/metric the world state change."""
        created_model = await super().create(model, session)
        
        # Log and record metrics for world state change
        self.logger.info(
            f"World state change: {self.model_class.__name__} created - "
            f"{created_model.name} (ID: {created_model.id}, ...)"
        )
        self.metrics.record_world_state_change("asset_type", "created")
        
        return created_model
```

**Reference Implementations:**
- @src/ds_common/repository/npc.py - NPC creation logging and metrics
- @src/ds_common/repository/quest.py - Quest creation logging and metrics
- @src/ds_common/memory/location_graph_service.py - Location node/edge creation logging and metrics

### Repository Pattern
```python
from ds_common.repository.base_repository import BaseRepository
from ds_common.models.my_model import MyModel
from ds_discord_bot.postgres_manager import PostgresManager
from sqlalchemy.ext.asyncio import AsyncSession

class MyRepository(BaseRepository[MyModel]):
    """Repository for MyModel operations."""
    
    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, MyModel)
    
    async def custom_method(
        self, 
        param: str, 
        session: AsyncSession | None = None
    ) -> MyModel | None:
        """
        Custom repository method.
        
        Args:
            param: Description of parameter
            session: Optional database session
            
        Returns:
            Model instance or None if not found
        """
        async def _execute(sess: AsyncSession):
            # Implementation using sess
            stmt = select(self.model_class).where(...)
            result = await sess.execute(stmt)
            return result.scalar_one_or_none()
        
        return await self._with_session(_execute, session)
```

### Reference Files
@src/ds_common/repository/base_repository.py
@src/ds_common/repository/character.py

## Database Operations

### Session Management
- Always use `_with_session()` helper method
- Accept optional `session` parameter for transaction control
- Use async context managers when creating new sessions

### Query Patterns
- Use SQLModel `select()` for queries
- Use `await sess.get()` for single ID lookups
- Use `await sess.execute(stmt)` for complex queries
- Always handle `None` returns appropriately

### Transaction Handling
- Use provided `session` parameter for multi-step operations
- Commit changes in `create()`, `update()`, `delete()` methods
- Refresh models after commit to get updated data

## Model Import Order and Relationship Resolution

**CRITICAL**: When models have relationships with `link_model` (junction tables), import order matters for SQLAlchemy relationship resolution.

### Import Order Requirements

1. **Base Models First**: Import base models (e.g., `ItemCategory`, `ItemTemplate`) BEFORE models that reference them (e.g., `CharacterClass`)
2. **Junction Tables After Models**: Import junction tables after the models they link
3. **Runtime Loading**: All models must be imported at application startup before any database operations

### Relationship Configuration

- **link_model Must Be Class, Not String**: When using `link_model` in relationships, use the actual class, not a string:
  ```python
  # ✅ Correct
  from ds_common.models.junction_tables import CharacterClassStartingEquipment
  starting_equipment: list["ItemTemplate"] = Relationship(
      link_model=CharacterClassStartingEquipment,  # Actual class
  )
  
  # ❌ Incorrect - will cause "No inspection system is available for object of type <class 'str'>"
  starting_equipment: list["ItemTemplate"] = Relationship(
      link_model="CharacterClassStartingEquipment",  # String reference
  )
  ```

- **Forward References in Type Hints**: String forward references in type hints are fine: `list["ItemTemplate"]`
- **Models Package**: Use `ds_common/models/__init__.py` to import all models in correct order
- **Import in Application Code**: Import `ds_common.models` in `postgres_manager.py` and extension files to ensure models are loaded before database operations

### Common Error

If you see: `InvalidRequestError: When initializing mapper Mapper[CharacterClass(...)], expression 'ItemTemplate' failed to locate a name ('ItemTemplate')`

**Solution**: Ensure `ItemTemplate` is imported before `CharacterClass` in the import chain. Import `ds_common.models` early in application startup (e.g., in `postgres_manager.py`).

