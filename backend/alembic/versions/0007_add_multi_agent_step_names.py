"""Add multi-agent step names to agent_step_name enum.

Revision ID: 0007_add_multi_agent_step_names
Revises: 0006_add_hourly_frequency
Create Date: 2026-06-24
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0007_add_multi_agent_step_names"
down_revision: str | None = "0006_add_hourly_frequency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_VALUES = (
    "FETCH_DATA",
    "TECHNICAL_ANALYST",
    "FUNDAMENTAL_ANALYST",
    "SENTIMENT_ANALYST",
    "PORTFOLIO_MANAGER",
)


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE agent_step_name ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    op.execute("ALTER TYPE agent_step_name RENAME TO agent_step_name_old")
    op.execute(
        "CREATE TYPE agent_step_name AS ENUM "
        "('SINGLE_DECISION_AGENT', 'MARKET_ANALYST', 'TRADING_DECISION', "
        "'RISK_MANAGER')"
    )
    op.execute(
        "ALTER TABLE agent_decision_logs ALTER COLUMN agent_step_name "
        "TYPE agent_step_name USING agent_step_name::text::agent_step_name"
    )
    op.execute("DROP TYPE agent_step_name_old")
