"""Add research data cache table.

Revision ID: 0009_research_data_cache
Revises: 0008_agentic_trading_v2_events
Create Date: 2026-07-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_research_data_cache"
down_revision: str | None = "0008_agentic_trading_v2_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_data_cache",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("dataset", sa.String(), nullable=False),
        sa.Column("cache_key", sa.Text(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "symbol",
            "dataset",
            "cache_key",
            name="uq_research_data_cache_provider_symbol_dataset_key",
        ),
    )
    op.create_index(
        "ix_research_data_cache_provider_symbol",
        "research_data_cache",
        ["provider", "symbol"],
    )
    op.create_index(
        "ix_research_data_cache_dataset",
        "research_data_cache",
        ["dataset"],
    )
    op.create_index(
        "ix_research_data_cache_expires_at",
        "research_data_cache",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_data_cache_expires_at", table_name="research_data_cache")
    op.drop_index("ix_research_data_cache_dataset", table_name="research_data_cache")
    op.drop_index(
        "ix_research_data_cache_provider_symbol", table_name="research_data_cache"
    )
    op.drop_table("research_data_cache")
