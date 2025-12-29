import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel, table=False):
    """
    Base SQLModel class for all database models.

    Provides common fields and configuration for all models.
    Uses UUID primary keys instead of SurrealDB RecordID.
    All datetime fields use UTC timezone-aware timestamps.
    """

    id: UUID | None = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique identifier for the record",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        description="Timestamp when the record was created (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        description="Timestamp when the record was last updated (UTC)",
    )

    def __init__(self, **data: Any) -> None:
        """
        Initialize the model with optional ID generation.

        If no ID is provided, a UUID will be generated automatically.
        """
        if "id" not in data or data["id"] is None:
            data["id"] = uuid.uuid4()
        if "created_at" not in data or data["created_at"] is None:
            data["created_at"] = datetime.now(UTC)
        if "updated_at" not in data or data["updated_at"] is None:
            data["updated_at"] = datetime.now(UTC)
        super().__init__(**data)
