"""Add paper trading smoke-test enum values.

Revision ID: 0004_smoke_test_enums
Revises: 0003_orb_intraday_enums
Create Date: 2026-05-26
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0004_smoke_test_enums"
down_revision: str | None = "0003_orb_intraday_enums"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE strategy_type ADD VALUE IF NOT EXISTS "
        "'PAPER_TRADING_SMOKE_TEST'"
    )
    op.execute(
        "ALTER TYPE trading_frequency ADD VALUE IF NOT EXISTS "
        "'TEST_1_MIN'"
    )


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally not attempted.
    pass
