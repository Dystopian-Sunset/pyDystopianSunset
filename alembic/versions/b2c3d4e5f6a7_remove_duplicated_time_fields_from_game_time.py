"""remove_duplicated_time_fields_from_game_time

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns exist (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    game_time_columns = (
        [col["name"] for col in inspector.get_columns("game_time")]
        if "game_time" in inspector.get_table_names()
        else []
    )

    # Migrate time_multiplier from game_time to game_settings if it exists
    if "time_multiplier" in game_time_columns:
        # Get the time_multiplier value from game_time (if any record exists)
        result = conn.execute(sa.text("SELECT time_multiplier FROM game_time LIMIT 1"))
        row = result.fetchone()
        if row and row[0] is not None:
            time_multiplier_value = row[0]
            # Update game_settings with this value if game_time_multiplier is NULL or default
            conn.execute(
                sa.text("""
                UPDATE game_settings 
                SET game_time_multiplier = :multiplier
                WHERE game_time_multiplier IS NULL OR game_time_multiplier = 60.0
            """),
                {"multiplier": time_multiplier_value},
            )

        # Drop the column
        op.drop_column("game_time", "time_multiplier")

    # Migrate epoch_start from game_time to game_settings if it exists
    if "epoch_start" in game_time_columns:
        # Get the epoch_start value from game_time (if any record exists)
        result = conn.execute(sa.text("SELECT epoch_start FROM game_time LIMIT 1"))
        row = result.fetchone()
        if row and row[0] is not None:
            epoch_start_value = row[0]
            # Update game_settings with this value if game_epoch_start is NULL
            conn.execute(
                sa.text("""
                UPDATE game_settings 
                SET game_epoch_start = :epoch_start
                WHERE game_epoch_start IS NULL
            """),
                {"epoch_start": epoch_start_value},
            )

        # Drop the column
        op.drop_column("game_time", "epoch_start")

    # Update game_time_config to remove duplicated fields
    # Remove hours_per_day, days_per_year, day_start_hour, night_start_hour from JSON
    op.execute("""
        UPDATE game_time 
        SET game_time_config = (
            SELECT jsonb_build_object(
                'months_per_year', COALESCE((game_time_config::jsonb->>'months_per_year')::int, 20),
                'days_per_month', COALESCE((game_time_config::jsonb->>'days_per_month')::int, 20),
                'season_days', COALESCE(game_time_config::jsonb->'season_days', '{"SPRING": 100, "SUMMER": 100, "FALL": 100, "WINTER": 100}'::jsonb),
                'seasonal_day_night', COALESCE(game_time_config::jsonb->'seasonal_day_night', '{"SPRING": {"day_start": 0, "night_start": 15}, "SUMMER": {"day_start": 0, "night_start": 18}, "FALL": {"day_start": 0, "night_start": 15}, "WINTER": {"day_start": 0, "night_start": 12}}'::jsonb)
            )
        )::json
        WHERE game_time_config IS NOT NULL;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add time_multiplier column
    op.add_column(
        "game_time", sa.Column("time_multiplier", sa.Float(), nullable=False, server_default="60.0")
    )

    # Re-add epoch_start column
    op.add_column("game_time", sa.Column("epoch_start", sa.DateTime(timezone=True), nullable=False))

    # Migrate values back from game_settings
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT game_time_multiplier, game_epoch_start FROM game_settings LIMIT 1")
    )
    row = result.fetchone()
    if row:
        multiplier = row[0] if row[0] is not None else 60.0
        epoch_start = row[1] if row[1] is not None else sa.func.now()
        conn.execute(
            sa.text("""
            UPDATE game_time 
            SET time_multiplier = :multiplier,
                epoch_start = :epoch_start
        """),
            {"multiplier": multiplier, "epoch_start": epoch_start},
        )

    # Restore duplicated fields in game_time_config
    op.execute("""
        UPDATE game_time 
        SET game_time_config = jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        game_time_config::jsonb,
                        '{hours_per_day}',
                        '30'::jsonb
                    ),
                    '{days_per_year}',
                    '400'::jsonb
                ),
                '{day_start_hour}',
                '0'::jsonb
            ),
            '{night_start_hour}',
            '15'::jsonb
        )::json
        WHERE game_time_config IS NOT NULL;
    """)
