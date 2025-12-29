from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel


class MemorySettings(BaseSQLModel, table=True):
    """
    Memory settings model for configurable expiration times and cleanup settings.

    Singleton pattern - only one settings record should exist.
    """

    __tablename__ = "memory_settings"

    session_memory_expiration_hours: int = Field(
        default=4,
        description="Hours after processing before session memories expire",
    )
    episode_memory_expiration_hours: int = Field(
        default=48,
        description="Hours before episode memories expire (unless promoted)",
    )
    snapshot_retention_days: int = Field(
        default=90,
        description="Days to retain snapshots before archiving",
    )
    auto_cleanup_enabled: bool = Field(
        default=True,
        description="Whether automatic cleanup is enabled",
    )
