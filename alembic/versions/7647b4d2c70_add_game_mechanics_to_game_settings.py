"""add_game_mechanics_to_game_settings

Revision ID: 7647b4d2c70
Revises: 50e9f71cf746
Create Date: 2025-12-25 17:03:12.529

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7647b4d2c70"
down_revision: str | Sequence[str] | None = "50e9f71cf746"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns already exist (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    game_settings_columns = (
        [col["name"] for col in inspector.get_columns("game_settings")]
        if "game_settings" in inspector.get_table_names()
        else []
    )

    # Character stat generation settings
    if "character_stats_pool_min" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_pool_min", sa.Integer(), nullable=False, server_default="60"
            ),
        )
    if "character_stats_pool_max" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_pool_max", sa.Integer(), nullable=False, server_default="80"
            ),
        )
    if "character_stats_primary_weight" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_primary_weight", sa.Float(), nullable=False, server_default="2.5"
            ),
        )
    if "character_stats_secondary_weight" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_secondary_weight", sa.Float(), nullable=False, server_default="1.0"
            ),
        )
    if "character_stats_luck_min" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("character_stats_luck_min", sa.Integer(), nullable=False, server_default="1"),
        )
    if "character_stats_luck_max" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_luck_max", sa.Integer(), nullable=False, server_default="10"
            ),
        )
    if "character_stats_stat_min" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("character_stats_stat_min", sa.Integer(), nullable=False, server_default="1"),
        )
    if "character_stats_stat_max" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_stat_max", sa.Integer(), nullable=False, server_default="20"
            ),
        )
    if "character_stats_allocation_variance" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_allocation_variance",
                sa.Integer(),
                nullable=False,
                server_default="2",
            ),
        )
    if "character_stats_max_rerolls" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "character_stats_max_rerolls", sa.Integer(), nullable=False, server_default="5"
            ),
        )

    # Memory compression settings
    if "memory_max_memories" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column("memory_max_memories", sa.Integer(), nullable=False, server_default="12"),
        )
    if "memory_max_recent_memories" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "memory_max_recent_memories", sa.Integer(), nullable=False, server_default="8"
            ),
        )
    if "memory_importance_threshold" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "memory_importance_threshold", sa.Float(), nullable=False, server_default="0.3"
            ),
        )
    if "memory_recent_cutoff_minutes" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "memory_recent_cutoff_minutes", sa.Integer(), nullable=False, server_default="30"
            ),
        )
    if "memory_description_truncate_length" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "memory_description_truncate_length",
                sa.Integer(),
                nullable=False,
                server_default="400",
            ),
        )
    if "memory_environmental_items_lookback_minutes" not in game_settings_columns:
        op.add_column(
            "game_settings",
            sa.Column(
                "memory_environmental_items_lookback_minutes",
                sa.Integer(),
                nullable=False,
                server_default="30",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove all added columns
    op.drop_column("game_settings", "memory_environmental_items_lookback_minutes")
    op.drop_column("game_settings", "memory_description_truncate_length")
    op.drop_column("game_settings", "memory_recent_cutoff_minutes")
    op.drop_column("game_settings", "memory_importance_threshold")
    op.drop_column("game_settings", "memory_max_recent_memories")
    op.drop_column("game_settings", "memory_max_memories")
    op.drop_column("game_settings", "character_stats_max_rerolls")
    op.drop_column("game_settings", "character_stats_allocation_variance")
    op.drop_column("game_settings", "character_stats_stat_max")
    op.drop_column("game_settings", "character_stats_stat_min")
    op.drop_column("game_settings", "character_stats_luck_max")
    op.drop_column("game_settings", "character_stats_luck_min")
    op.drop_column("game_settings", "character_stats_secondary_weight")
    op.drop_column("game_settings", "character_stats_primary_weight")
    op.drop_column("game_settings", "character_stats_pool_max")
    op.drop_column("game_settings", "character_stats_pool_min")
