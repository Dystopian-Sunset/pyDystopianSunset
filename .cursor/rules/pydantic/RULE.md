---
description: "Standards for Pydantic models - BaseSurrealModel, request/response models, validators, and serializers"
globs:
  - "**/ds_common/models/**/*.py"
alwaysApply: false
---

# Pydantic Models Standards

## Pydantic Usage in This Project

Pydantic is used for:
1. **SurrealDB Models** - `BaseSurrealModel` for SurrealDB entities
2. **Request/Response Models** - API request and response schemas (e.g., in `game_master.py`)
3. **Custom Type Annotations** - Custom validators for SurrealDB RecordID

## BaseSurrealModel Pattern

### Base Requirements
- Inherit from `pydantic.BaseModel` and `ABC`
- Use `RecordIDType` for ID fields (custom annotated type)
- Configure `model_config` with appropriate settings
- Implement custom validators and serializers for RecordID

### BaseSurrealModel Pattern
```python
from abc import ABC
from typing import Any
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator
from pydantic.types import Annotated
from surrealdb.data.types.record_id import RecordID
from ds_common.models.record_id_annotation import RecordIDAnnotation

RecordIDType = Annotated[RecordID, RecordIDAnnotation]

class BaseSurrealModel(BaseModel, ABC):
    id: RecordIDType

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_by_name=True,
        json_schema_extra={
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_]+$",
                    "examples": ["user:123", "post:abc123"],
                }
            }
        },
    )

    def __init__(self, **data: Any) -> None:
        if "id" not in data:
            data["id"] = self.create_id()
        super().__init__(**data)

    @field_validator("id", mode="before", check_fields=False)
    def validate_id(cls, v) -> RecordID:
        if isinstance(v, RecordID):
            return str(v)
        raise ValueError(f"Invalid ID: {v} should be string, number or RecordID")

    @field_serializer("id", mode="plain", check_fields=False)
    def serialize_id(cls, v) -> str:
        if isinstance(v, RecordID):
            return str(v)
        if isinstance(v, str):
            if ":" in v:
                parts = v.split(":")
                if len(parts) != 2:
                    raise ValueError(f"Invalid ID: {v} string format should be <table>:<id>")
                id = RecordID.parse(f"{parts[0]}:{parts[1]}")
                return str(id)
            raise ValueError(f"Invalid ID: {v} string format should be <table>:<id>")
        raise ValueError(f"Invalid ID: {v} should be string or RecordID")
```

### Reference Files
@src/ds_common/models/surreal_model.py
@src/ds_common/models/record_id_annotation.py

## Request/Response Models

### Pattern for API Models
Use Pydantic `BaseModel` for request and response schemas:

```python
from pydantic import BaseModel
from typing import Literal

# Use Literal types for constrained string values
CURRENCY_TYPES = Literal["quill", "credit"]

class RequestAddCredits(BaseModel):
    """Request model for adding credits to a character."""
    character: Character
    amount: int
    currency: CURRENCY_TYPES

class ResponseCharacterCredits(BaseModel):
    """Response model for character credits."""
    character: Character
    credits: int
    currency: CURRENCY_TYPES
```

### Reference Files
@src/ds_common/models/game_master.py

## Custom Type Annotations

### Creating Custom Validators
Use Pydantic's annotation system for custom types:

```python
from typing import Any
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema

class RecordIDAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler):
        def validate(value):
            if isinstance(value, RecordID):
                return value
            return RecordID.parse(value)
        return core_schema.no_info_after_validator_function(validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler: GetJsonSchemaHandler):
        return {
            "type": "string",
            "title": "RecordID",
            "examples": ["table:123", "table:⟨123⟩"],
        }
```

## Best Practices

### Model Configuration
- Use `ConfigDict` (Pydantic v2) instead of `Config` class
- Set `arbitrary_types_allowed=True` when using custom types (e.g., RecordID)
- Use `validate_by_name=True` for better validation
- Add `json_schema_extra` for better API documentation

### Field Validation
- Use `field_validator` for custom validation logic
- Use `mode="before"` to validate before type conversion
- Use `check_fields=False` when validating fields that may not exist yet
- Provide clear error messages in validators

### Field Serialization
- Use `field_serializer` for custom serialization logic
- Use `mode="plain"` for standard serialization
- Ensure serializers handle all valid input types

### Type Hints
- Always use type hints for all fields
- Use `|` for union types (e.g., `str | None`)
- Use `Literal` types for constrained string values
- Use `Annotated` for custom type annotations

### Documentation
- Add docstrings to all model classes
- Document field purposes in field descriptions
- Use descriptive model and field names

### Naming Conventions
- Request models: `Request<Action>` (e.g., `RequestAddCredits`)
- Response models: `Response<Entity><Property>` (e.g., `ResponseCharacterCredits`)
- Use PascalCase for model class names
- Use snake_case for field names

## Common Patterns

### Optional Fields
```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    required_field: str
    optional_field: str | None = None
    optional_with_default: str = Field(default="default_value")
```

### Field Validation
```python
from pydantic import BaseModel, field_validator

class MyModel(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()
```

### Field Serialization
```python
from pydantic import BaseModel, field_serializer

class MyModel(BaseModel):
    value: int

    @field_serializer("value")
    def serialize_value(self, v: int) -> str:
        return str(v)
```

### Using Literal Types
```python
from typing import Literal
from pydantic import BaseModel

STATUS = Literal["active", "inactive", "pending"]

class MyModel(BaseModel):
    status: STATUS
```

## Integration with SQLModel

### Note on SQLModel vs Pydantic
- **SQLModel models** (PostgreSQL): Inherit from `BaseSQLModel` (SQLModel)
- **Pydantic models** (SurrealDB/API): Inherit from `BaseSurrealModel` or `BaseModel` (Pydantic)
- Don't mix SQLModel and Pydantic for the same model
- Use SQLModel for database-backed models
- Use Pydantic for API schemas and SurrealDB models

## Things to Avoid

- ❌ Don't use Pydantic v1 syntax (use v2 with `ConfigDict`)
- ❌ Don't mix SQLModel and Pydantic for the same model
- ❌ Don't skip validation - always validate input data
- ❌ Don't use `Any` type without justification
- ❌ Don't forget to handle None values for optional fields
- ❌ Don't create circular dependencies between models
- ❌ Don't use mutable default arguments (use `default_factory` instead)




