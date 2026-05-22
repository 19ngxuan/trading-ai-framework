"""Create initial documented schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-22 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


experiment_mode = postgresql.ENUM(
    "HISTORICAL_SIMULATION",
    "LIVE_SIMULATION",
    "PAPER_TRADING",
    name="experiment_mode",
    create_type=False,
)
strategy_type = postgresql.ENUM(
    "BUY_AND_HOLD",
    "MOVING_AVERAGE",
    "AGENTIC_AI",
    name="strategy_type",
    create_type=False,
)
experiment_status = postgresql.ENUM(
    "CREATED",
    "RUNNING",
    "PAUSED",
    "STOPPED",
    "COMPLETED",
    "FAILED",
    name="experiment_status",
    create_type=False,
)
trading_frequency = postgresql.ENUM(
    "DAILY",
    "WEEKLY",
    "MONTHLY",
    name="trading_frequency",
    create_type=False,
)
fee_model_type = postgresql.ENUM(
    "NONE",
    "FIXED",
    "PERCENTAGE",
    name="fee_model_type",
    create_type=False,
)
execution_step_status = postgresql.ENUM(
    "RUNNING",
    "COMPLETED",
    "SKIPPED",
    "FAILED",
    name="execution_step_status",
    create_type=False,
)
trigger_type = postgresql.ENUM(
    "HISTORICAL",
    "SCHEDULED",
    "MANUAL",
    name="trigger_type",
    create_type=False,
)
decision_source_type = postgresql.ENUM(
    "STRATEGY",
    "AGENT",
    name="decision_source_type",
    create_type=False,
)
trade_action = postgresql.ENUM(
    "BUY", "SELL", "HOLD", name="trade_action", create_type=False
)
final_action = postgresql.ENUM(
    "BUY", "SELL", "HOLD", name="final_action", create_type=False
)
order_mode = postgresql.ENUM(
    "SIMULATED",
    "PAPER_BROKER",
    name="order_mode",
    create_type=False,
)
broker_name = postgresql.ENUM("ALPACA", "NONE", name="broker_name", create_type=False)
order_side = postgresql.ENUM("BUY", "SELL", name="order_side", create_type=False)
order_type = postgresql.ENUM("MARKET", name="order_type", create_type=False)
order_status = postgresql.ENUM(
    "CREATED",
    "SUBMITTED",
    "FILLED",
    "REJECTED",
    "FAILED",
    "CANCELLED",
    name="order_status",
    create_type=False,
)
agent_mode = postgresql.ENUM(
    "SINGLE_AGENT",
    "PIPELINE",
    name="agent_mode",
    create_type=False,
)
agent_step_name = postgresql.ENUM(
    "SINGLE_DECISION_AGENT",
    "MARKET_ANALYST",
    "TRADING_DECISION",
    "RISK_MANAGER",
    name="agent_step_name",
    create_type=False,
)
parsing_status = postgresql.ENUM(
    "SUCCESS",
    "FAILED",
    "REPAIRED",
    name="parsing_status",
    create_type=False,
)
broker_sync_status = postgresql.ENUM(
    "SUCCESS",
    "FAILED",
    "MISMATCH",
    name="broker_sync_status",
    create_type=False,
)
event_level = postgresql.ENUM(
    "INFO", "WARNING", "ERROR", name="event_level", create_type=False
)
system_event_type = postgresql.ENUM(
    "EXPERIMENT_CREATED",
    "EXPERIMENT_STARTED",
    "EXPERIMENT_PAUSED",
    "EXPERIMENT_STOPPED",
    "EXPERIMENT_COMPLETED",
    "MARKET_DATA_MISSING",
    "STRATEGY_DECISION_CREATED",
    "RISK_LIMIT_TRIGGERED",
    "ORDER_SUBMITTED",
    "ORDER_FILLED",
    "ORDER_FAILED",
    "BROKER_SYNC_FAILED",
    "BROKER_STATE_MISMATCH",
    "LLM_OUTPUT_INVALID",
    "LLM_REPAIR_ATTEMPTED",
    "FALLBACK_HOLD_USED",
    name="system_event_type",
    create_type=False,
)

ENUMS = (
    experiment_mode,
    strategy_type,
    experiment_status,
    trading_frequency,
    fee_model_type,
    execution_step_status,
    trigger_type,
    decision_source_type,
    trade_action,
    final_action,
    order_mode,
    broker_name,
    order_side,
    order_type,
    order_status,
    agent_mode,
    agent_step_name,
    parsing_status,
    broker_sync_status,
    event_level,
    system_event_type,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "experiments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("mode", experiment_mode, nullable=False),
        sa.Column("strategy_type", strategy_type, nullable=False),
        sa.Column("asset_symbol", sa.String(), nullable=False),
        sa.Column("status", experiment_status, nullable=False),
        sa.Column("initial_capital", sa.Numeric(19, 4), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("trading_frequency", trading_frequency, nullable=False),
        sa.Column("fee_model_type", fee_model_type, nullable=False),
        sa.Column("fee_value", sa.Numeric(19, 8), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiments_asset_symbol", "experiments", ["asset_symbol"])
    op.create_index("ix_experiments_created_at", "experiments", ["created_at"])
    op.create_index("ix_experiments_mode", "experiments", ["mode"])
    op.create_index("ix_experiments_status", "experiments", ["status"])
    op.create_index("ix_experiments_strategy_type", "experiments", ["strategy_type"])

    op.create_table(
        "strategy_configs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("strategy_type", strategy_type, nullable=False),
        sa.Column("strategy_version", sa.String(), nullable=False),
        sa.Column("moving_average_window", sa.Integer(), nullable=True),
        sa.Column("position_sizing_type", sa.String(), nullable=True),
        sa.Column("agent_mode", agent_mode, nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("confidence_threshold", sa.Numeric(5, 4), nullable=True),
        sa.Column("parameters_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id"),
    )
    op.create_index(
        "ix_strategy_configs_agent_mode", "strategy_configs", ["agent_mode"]
    )
    op.create_index(
        "ix_strategy_configs_strategy_type", "strategy_configs", ["strategy_type"]
    )
    op.create_index(
        "ix_strategy_configs_strategy_version",
        "strategy_configs",
        ["strategy_version"],
    )

    op.create_table(
        "portfolios",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("cash", sa.Numeric(19, 4), nullable=False),
        sa.Column("position_symbol", sa.String(), nullable=True),
        sa.Column("position_quantity", sa.Numeric(19, 8), nullable=True),
        sa.Column("current_price", sa.Numeric(19, 8), nullable=True),
        sa.Column("current_position_value", sa.Numeric(19, 4), nullable=True),
        sa.Column("current_portfolio_value", sa.Numeric(19, 4), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id"),
    )

    op.create_table(
        "execution_steps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", execution_step_status, nullable=False),
        sa.Column("trigger_type", trigger_type, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id",
            "sequence_number",
            name="uq_execution_steps_experiment_sequence",
        ),
    )
    op.create_index("ix_execution_steps_created_at", "execution_steps", ["created_at"])
    op.create_index(
        "ix_execution_steps_experiment_id", "execution_steps", ["experiment_id"]
    )
    op.create_index(
        "ix_execution_steps_scheduled_for", "execution_steps", ["scheduled_for"]
    )
    op.create_index(
        "ix_execution_steps_sequence_number", "execution_steps", ["sequence_number"]
    )
    op.create_index("ix_execution_steps_status", "execution_steps", ["status"])

    op.create_table(
        "market_data_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(19, 8), nullable=True),
        sa.Column("open", sa.Numeric(19, 8), nullable=True),
        sa.Column("high", sa.Numeric(19, 8), nullable=True),
        sa.Column("low", sa.Numeric(19, 8), nullable=True),
        sa.Column("close", sa.Numeric(19, 8), nullable=True),
        sa.Column("volume", sa.Numeric(19, 4), nullable=True),
        sa.Column("moving_average", sa.Numeric(19, 8), nullable=True),
        sa.Column("rsi", sa.Numeric(10, 4), nullable=True),
        sa.Column("raw_data_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_step_id"),
    )
    op.create_index(
        "ix_market_data_snapshots_execution_step_id",
        "market_data_snapshots",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_market_data_snapshots_experiment_id",
        "market_data_snapshots",
        ["experiment_id"],
    )
    op.create_index(
        "ix_market_data_snapshots_symbol", "market_data_snapshots", ["symbol"]
    )
    op.create_index(
        "ix_market_data_snapshots_timestamp", "market_data_snapshots", ["timestamp"]
    )

    op.create_table(
        "trading_decisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("market_data_snapshot_id", sa.BigInteger(), nullable=False),
        sa.Column("source_type", decision_source_type, nullable=False),
        sa.Column("source_name", sa.String(), nullable=True),
        sa.Column("action", trade_action, nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("suggested_quantity", sa.Numeric(19, 8), nullable=True),
        sa.Column("suggested_notional", sa.Numeric(19, 4), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("raw_decision_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(
            ["market_data_snapshot_id"], ["market_data_snapshots.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_step_id"),
    )
    op.create_index("ix_trading_decisions_action", "trading_decisions", ["action"])
    op.create_index(
        "ix_trading_decisions_execution_step_id",
        "trading_decisions",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_trading_decisions_experiment_id", "trading_decisions", ["experiment_id"]
    )
    op.create_index(
        "ix_trading_decisions_market_data_snapshot_id",
        "trading_decisions",
        ["market_data_snapshot_id"],
    )
    op.create_index(
        "ix_trading_decisions_source_type", "trading_decisions", ["source_type"]
    )

    op.create_table(
        "risk_checks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("trading_decision_id", sa.BigInteger(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("final_action", final_action, nullable=False),
        sa.Column("final_quantity", sa.Numeric(19, 8), nullable=True),
        sa.Column("final_notional", sa.Numeric(19, 4), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("rules_triggered_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["trading_decision_id"], ["trading_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_step_id"),
        sa.UniqueConstraint("trading_decision_id"),
    )
    op.create_index("ix_risk_checks_approved", "risk_checks", ["approved"])
    op.create_index(
        "ix_risk_checks_execution_step_id", "risk_checks", ["execution_step_id"]
    )
    op.create_index("ix_risk_checks_experiment_id", "risk_checks", ["experiment_id"])
    op.create_index("ix_risk_checks_final_action", "risk_checks", ["final_action"])
    op.create_index(
        "ix_risk_checks_trading_decision_id", "risk_checks", ["trading_decision_id"]
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("risk_check_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", order_mode, nullable=False),
        sa.Column("broker_name", broker_name, nullable=True),
        sa.Column("broker_order_id", sa.String(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", order_side, nullable=False),
        sa.Column("quantity", sa.Numeric(19, 8), nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("filled_at", sa.DateTime(), nullable=True),
        sa.Column("average_fill_price", sa.Numeric(19, 8), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["risk_check_id"], ["risk_checks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_step_id"),
        sa.UniqueConstraint("risk_check_id"),
    )
    op.create_index("ix_orders_broker_order_id", "orders", ["broker_order_id"])
    op.create_index("ix_orders_execution_step_id", "orders", ["execution_step_id"])
    op.create_index("ix_orders_experiment_id", "orders", ["experiment_id"])
    op.create_index("ix_orders_risk_check_id", "orders", ["risk_check_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_symbol", "orders", ["symbol"])

    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", order_side, nullable=False),
        sa.Column("quantity", sa.Numeric(19, 8), nullable=False),
        sa.Column("price", sa.Numeric(19, 8), nullable=False),
        sa.Column("order_value", sa.Numeric(19, 4), nullable=True),
        sa.Column("fee", sa.Numeric(19, 8), nullable=True),
        sa.Column("portfolio_value_after_trade", sa.Numeric(19, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_execution_step_id", "trades", ["execution_step_id"])
    op.create_index("ix_trades_experiment_id", "trades", ["experiment_id"])
    op.create_index("ix_trades_order_id", "trades", ["order_id"])
    op.create_index("ix_trades_symbol", "trades", ["symbol"])
    op.create_index("ix_trades_timestamp", "trades", ["timestamp"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("cash", sa.Numeric(19, 4), nullable=False),
        sa.Column("position_symbol", sa.String(), nullable=True),
        sa.Column("position_quantity", sa.Numeric(19, 8), nullable=True),
        sa.Column("position_market_value", sa.Numeric(19, 4), nullable=True),
        sa.Column("total_portfolio_value", sa.Numeric(19, 4), nullable=True),
        sa.Column("current_price", sa.Numeric(19, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_step_id"),
    )
    op.create_index(
        "ix_portfolio_snapshots_execution_step_id",
        "portfolio_snapshots",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_portfolio_snapshots_experiment_id",
        "portfolio_snapshots",
        ["experiment_id"],
    )
    op.create_index(
        "ix_portfolio_snapshots_timestamp", "portfolio_snapshots", ["timestamp"]
    )

    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("total_return", sa.Numeric(19, 8), nullable=True),
        sa.Column("profit_loss", sa.Numeric(19, 4), nullable=True),
        sa.Column("number_of_trades", sa.Integer(), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(19, 8), nullable=True),
        sa.Column("buy_and_hold_return", sa.Numeric(19, 8), nullable=True),
        sa.Column("difference_to_buy_and_hold", sa.Numeric(19, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_step_id"),
    )
    op.create_index(
        "ix_metric_snapshots_execution_step_id",
        "metric_snapshots",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_metric_snapshots_experiment_id", "metric_snapshots", ["experiment_id"]
    )
    op.create_index("ix_metric_snapshots_timestamp", "metric_snapshots", ["timestamp"])

    op.create_table(
        "agent_decision_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("trading_decision_id", sa.BigInteger(), nullable=True),
        sa.Column("agent_mode", agent_mode, nullable=False),
        sa.Column("agent_step_name", agent_step_name, nullable=False),
        sa.Column("agent_name", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("input_json", postgresql.JSONB(), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("raw_output_text", sa.Text(), nullable=True),
        sa.Column("parsed_output_json", postgresql.JSONB(), nullable=True),
        sa.Column("parsing_status", parsing_status, nullable=False),
        sa.Column("repair_prompt_text", sa.Text(), nullable=True),
        sa.Column("repair_raw_output_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["trading_decision_id"], ["trading_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_decision_logs_agent_mode", "agent_decision_logs", ["agent_mode"]
    )
    op.create_index(
        "ix_agent_decision_logs_agent_step_name",
        "agent_decision_logs",
        ["agent_step_name"],
    )
    op.create_index(
        "ix_agent_decision_logs_created_at", "agent_decision_logs", ["created_at"]
    )
    op.create_index(
        "ix_agent_decision_logs_execution_step_id",
        "agent_decision_logs",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_agent_decision_logs_experiment_id",
        "agent_decision_logs",
        ["experiment_id"],
    )
    op.create_index(
        "ix_agent_decision_logs_parsing_status",
        "agent_decision_logs",
        ["parsing_status"],
    )
    op.create_index(
        "ix_agent_decision_logs_trading_decision_id",
        "agent_decision_logs",
        ["trading_decision_id"],
    )

    op.create_table(
        "broker_sync_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("broker_name", broker_name, nullable=False),
        sa.Column("sync_status", broker_sync_status, nullable=False),
        sa.Column("broker_cash", sa.Numeric(19, 4), nullable=True),
        sa.Column("local_cash", sa.Numeric(19, 4), nullable=True),
        sa.Column("broker_positions_json", postgresql.JSONB(), nullable=True),
        sa.Column("local_positions_json", postgresql.JSONB(), nullable=True),
        sa.Column("mismatch_details_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_broker_sync_logs_broker_name", "broker_sync_logs", ["broker_name"]
    )
    op.create_index(
        "ix_broker_sync_logs_execution_step_id",
        "broker_sync_logs",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_broker_sync_logs_experiment_id", "broker_sync_logs", ["experiment_id"]
    )
    op.create_index(
        "ix_broker_sync_logs_sync_status", "broker_sync_logs", ["sync_status"]
    )
    op.create_index("ix_broker_sync_logs_timestamp", "broker_sync_logs", ["timestamp"])

    op.create_table(
        "system_event_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_step_id", sa.BigInteger(), nullable=True),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("level", event_level, nullable=False),
        sa.Column("event_type", system_event_type, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_step_id"], ["execution_steps.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_system_event_logs_event_type", "system_event_logs", ["event_type"]
    )
    op.create_index(
        "ix_system_event_logs_execution_step_id",
        "system_event_logs",
        ["execution_step_id"],
    )
    op.create_index(
        "ix_system_event_logs_experiment_id", "system_event_logs", ["experiment_id"]
    )
    op.create_index("ix_system_event_logs_level", "system_event_logs", ["level"])
    op.create_index(
        "ix_system_event_logs_timestamp", "system_event_logs", ["timestamp"]
    )


def downgrade() -> None:
    op.drop_table("system_event_logs")
    op.drop_table("broker_sync_logs")
    op.drop_table("agent_decision_logs")
    op.drop_table("metric_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_table("trades")
    op.drop_table("orders")
    op.drop_table("risk_checks")
    op.drop_table("trading_decisions")
    op.drop_table("market_data_snapshots")
    op.drop_table("execution_steps")
    op.drop_table("portfolios")
    op.drop_table("strategy_configs")
    op.drop_table("experiments")

    bind = op.get_bind()
    for enum_type in reversed(ENUMS):
        enum_type.drop(bind, checkfirst=True)
