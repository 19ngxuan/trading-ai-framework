"""Add Opening Range Breakout intraday enum values.

Revision ID: 0003_orb_intraday_enums
Revises: 0002_lifecycle_events
Create Date: 2026-05-25
"""

from typing import Sequence

from alembic import op


revision: str = "0003_orb_intraday_enums"
down_revision: str | None = "0002_lifecycle_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE strategy_type ADD VALUE IF NOT EXISTS "
        "'OPENING_RANGE_BREAKOUT'"
    )
    op.execute(
        "ALTER TYPE trading_frequency ADD VALUE IF NOT EXISTS "
        "'INTRADAY_5_MIN'"
    )


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally not attempted.
    pass
