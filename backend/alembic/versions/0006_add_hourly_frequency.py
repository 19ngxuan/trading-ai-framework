"""Add hourly trading frequency enum.

Revision ID: 0006_add_hourly_frequency
Revises: 0005_remove_unused_config
Create Date: 2026-06-20
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0006_add_hourly_frequency"
down_revision: str | None = "0005_remove_unused_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE trading_frequency ADD VALUE IF NOT EXISTS 'HOURLY'")


def downgrade() -> None:
    op.execute("ALTER TYPE trading_frequency RENAME TO trading_frequency_old")
    op.execute(
        "CREATE TYPE trading_frequency AS ENUM "
        "('DAILY', 'WEEKLY', 'MONTHLY', 'INTRADAY_5_MIN', 'TEST_1_MIN')"
    )
    op.execute(
        "ALTER TABLE experiments ALTER COLUMN trading_frequency TYPE trading_frequency "
        "USING trading_frequency::text::trading_frequency"
    )
    op.execute(
        "DROP TYPE trading_frequency_old"
    )
