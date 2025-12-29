from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import JSON, BigInteger, Column, DateTime
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

SnapshotType = Literal["world_change", "episode_promotion"]  # Used for type hints only


class MemorySnapshot(BaseSQLModel, table=True):
    """
    Memory snapshot model for storing world state before high-impact changes.

    Enables rollback capability if world-breaking changes occur.
    """

    __tablename__ = "memory_snapshots"

    snapshot_type: str = Field(
        description="Type of snapshot"
    )  # SnapshotType = Literal["world_change", "episode_promotion"]
    snapshot_data: dict = Field(
        sa_column=Column(JSON),
        description="Full snapshot data as JSONB",
    )
    world_memory_id: UUID | None = Field(
        default=None, index=True, description="World memory ID this snapshot protects"
    )
    episode_id: UUID | None = Field(
        default=None, index=True, description="Episode ID that triggered this snapshot"
    )
    created_reason: str = Field(description="Reason for creating this snapshot")
    can_unwind: bool = Field(default=True, description="Whether this snapshot can be unwound")

    unwound_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="When this snapshot was unwound (UTC)",
    )
    unwound_by: int | None = Field(
        default=None,
        sa_column=Column(BigInteger()),
        description="Discord user ID who performed the unwind",
    )
