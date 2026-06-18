"""Remove unused strategy config fields and live simulation mode.

Revision ID: 0005_remove_unused_config
Revises: 0004_smoke_test_enums
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_remove_unused_config"
down_revision: str | None = "0004_smoke_test_enums"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    live_count = op.get_bind().execute(
        sa.text("SELECT count(*) FROM experiments WHERE mode = 'LIVE_SIMULATION'")
    ).scalar_one()
    if live_count:
        raise RuntimeError(
            "Cannot remove LIVE_SIMULATION while experiments still use it."
        )

    op.drop_index(
        "ix_strategy_configs_strategy_version",
        table_name="strategy_configs",
        if_exists=True,
    )
    op.drop_column("strategy_configs", "position_sizing_type")
    op.drop_column("strategy_configs", "strategy_version")

    op.execute("ALTER TYPE experiment_mode RENAME TO experiment_mode_old")
    op.execute(
        "CREATE TYPE experiment_mode AS ENUM "
        "('HISTORICAL_SIMULATION', 'PAPER_TRADING')"
    )
    op.execute(
        "ALTER TABLE experiments ALTER COLUMN mode TYPE experiment_mode "
        "USING mode::text::experiment_mode"
    )
    op.execute("DROP TYPE experiment_mode_old")


def downgrade() -> None:
    op.execute("ALTER TYPE experiment_mode RENAME TO experiment_mode_old")
    op.execute(
        "CREATE TYPE experiment_mode AS ENUM "
        "('HISTORICAL_SIMULATION', 'LIVE_SIMULATION', 'PAPER_TRADING')"
    )
    op.execute(
        "ALTER TABLE experiments ALTER COLUMN mode TYPE experiment_mode "
        "USING mode::text::experiment_mode"
    )
    op.execute("DROP TYPE experiment_mode_old")

    op.add_column(
        "strategy_configs",
        sa.Column("strategy_version", sa.String(), nullable=True),
    )
    op.add_column(
        "strategy_configs",
        sa.Column("position_sizing_type", sa.String(), nullable=True),
    )
    op.execute(
        "UPDATE strategy_configs SET strategy_version = "
        "lower(replace(strategy_type::text, '_', '-')) || '-v1'"
    )
    op.alter_column("strategy_configs", "strategy_version", nullable=False)
    op.create_index(
        "ix_strategy_configs_strategy_version",
        "strategy_configs",
        ["strategy_version"],
    )
