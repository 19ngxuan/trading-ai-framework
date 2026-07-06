"""Add agentic trading v2 decisions and news event audit tables.

Revision ID: 0008_agentic_trading_v2_events
Revises: 0007_add_multi_agent_step_names
Create Date: 2026-07-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_agentic_trading_v2_events"
down_revision: str | None = "0007_add_multi_agent_step_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


trade_intent = postgresql.ENUM(
    "OPEN_LONG",
    "ADD_TO_LONG",
    "HOLD_POSITION",
    "REDUCE_LONG",
    "CLOSE_LONG",
    "STAY_OUT",
    name="trade_intent",
    create_type=False,
)
primary_driver = postgresql.ENUM(
    "TECHNICAL",
    "FUNDAMENTAL",
    "SENTIMENT",
    "RISK",
    "PORTFOLIO",
    "EVENT_RISK",
    name="primary_driver",
    create_type=False,
)
news_event_type = postgresql.ENUM(
    "GEOPOLITICAL_RISK",
    "FED_RATE_DECISION",
    "INFLATION_CPI",
    "EARNINGS_BEAT",
    "EARNINGS_MISS",
    "GUIDANCE_CUT",
    "ANALYST_UPGRADE",
    "ANALYST_DOWNGRADE",
    "LEGAL_REGULATORY_RISK",
    "M_AND_A",
    "PRODUCT_LAUNCH",
    "SUPPLY_CHAIN_SHOCK",
    "CYBERSECURITY_INCIDENT",
    "CEO_CHANGE",
    "GENERAL_MARKET_NEWS",
    name="news_event_type",
    create_type=False,
)
news_event_severity = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="news_event_severity",
    create_type=False,
)
impact_direction = postgresql.ENUM(
    "POSITIVE",
    "NEGATIVE",
    "NEUTRAL",
    name="impact_direction",
    create_type=False,
)
event_decision_status = postgresql.ENUM(
    "TRIGGERED",
    "SKIPPED",
    "FAILED",
    name="event_decision_status",
    create_type=False,
)


NEW_ENUMS = (
    trade_intent,
    primary_driver,
    news_event_type,
    news_event_severity,
    impact_direction,
    event_decision_status,
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("ALTER TYPE trigger_type ADD VALUE IF NOT EXISTS 'EVENT'")
    for enum_type in NEW_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.add_column(
        "trading_decisions",
        sa.Column("trade_intent", trade_intent, nullable=True),
    )
    op.add_column(
        "trading_decisions",
        sa.Column("target_exposure_pct", sa.Numeric(7, 6), nullable=True),
    )
    op.add_column(
        "trading_decisions",
        sa.Column("primary_driver", primary_driver, nullable=True),
    )
    op.add_column(
        "trading_decisions",
        sa.Column("new_information", sa.Boolean(), nullable=True),
    )
    op.create_index(
        "ix_trading_decisions_trade_intent",
        "trading_decisions",
        ["trade_intent"],
    )
    op.create_index(
        "ix_trading_decisions_primary_driver",
        "trading_decisions",
        ["primary_driver"],
    )

    op.create_table(
        "news_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("external_event_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("event_type", news_event_type, nullable=False),
        sa.Column("severity", news_event_severity, nullable=False),
        sa.Column("affected_symbols_json", postgresql.JSONB(), nullable=False),
        sa.Column("raw_payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "external_event_id",
            name="uq_news_events_provider_external_event_id",
        ),
    )
    op.create_index("ix_news_events_timestamp", "news_events", ["timestamp"])
    op.create_index("ix_news_events_event_type", "news_events", ["event_type"])
    op.create_index("ix_news_events_severity", "news_events", ["severity"])

    op.create_table(
        "event_asset_impacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("impact_direction", impact_direction, nullable=False),
        sa.Column("relevance_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("raw_impact_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "symbol",
            name="uq_event_asset_impacts_event_symbol",
        ),
    )
    op.create_index(
        "ix_event_asset_impacts_event_id", "event_asset_impacts", ["event_id"]
    )
    op.create_index(
        "ix_event_asset_impacts_symbol", "event_asset_impacts", ["symbol"]
    )
    op.create_index(
        "ix_event_asset_impacts_relevance_score",
        "event_asset_impacts",
        ["relevance_score"],
    )

    op.create_table(
        "event_decisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=True),
        sa.Column("trading_decision_id", sa.BigInteger(), nullable=True),
        sa.Column("status", event_decision_status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["trading_decision_id"], ["trading_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "experiment_id",
            name="uq_event_decisions_event_experiment",
        ),
    )
    op.create_index("ix_event_decisions_event_id", "event_decisions", ["event_id"])
    op.create_index(
        "ix_event_decisions_experiment_id", "event_decisions", ["experiment_id"]
    )
    op.create_index("ix_event_decisions_status", "event_decisions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_event_decisions_status", table_name="event_decisions")
    op.drop_index("ix_event_decisions_experiment_id", table_name="event_decisions")
    op.drop_index("ix_event_decisions_event_id", table_name="event_decisions")
    op.drop_table("event_decisions")

    op.drop_index(
        "ix_event_asset_impacts_relevance_score", table_name="event_asset_impacts"
    )
    op.drop_index("ix_event_asset_impacts_symbol", table_name="event_asset_impacts")
    op.drop_index("ix_event_asset_impacts_event_id", table_name="event_asset_impacts")
    op.drop_table("event_asset_impacts")

    op.drop_index("ix_news_events_severity", table_name="news_events")
    op.drop_index("ix_news_events_event_type", table_name="news_events")
    op.drop_index("ix_news_events_timestamp", table_name="news_events")
    op.drop_table("news_events")

    op.drop_index("ix_trading_decisions_primary_driver", table_name="trading_decisions")
    op.drop_index("ix_trading_decisions_trade_intent", table_name="trading_decisions")
    op.drop_column("trading_decisions", "new_information")
    op.drop_column("trading_decisions", "primary_driver")
    op.drop_column("trading_decisions", "target_exposure_pct")
    op.drop_column("trading_decisions", "trade_intent")

    bind = op.get_bind()
    for enum_type in reversed(NEW_ENUMS):
        enum_type.drop(bind, checkfirst=True)

    op.execute("ALTER TYPE trigger_type RENAME TO trigger_type_old")
    op.execute(
        "CREATE TYPE trigger_type AS ENUM ('HISTORICAL', 'SCHEDULED', 'MANUAL')"
    )
    op.execute(
        "ALTER TABLE execution_steps ALTER COLUMN trigger_type "
        "TYPE trigger_type USING trigger_type::text::trigger_type"
    )
    op.execute("DROP TYPE trigger_type_old")
