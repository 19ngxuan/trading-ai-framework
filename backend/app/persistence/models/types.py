from sqlalchemy import Enum as SqlEnum

from app.domain.enums import (
    AgentMode,
    AgentStepName,
    BrokerName,
    BrokerSyncStatus,
    DecisionSourceType,
    EventLevel,
    EventDecisionStatus,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    FinalAction,
    ImpactDirection,
    NewsEventSeverity,
    NewsEventType,
    OrderMode,
    OrderSide,
    OrderStatus,
    OrderType,
    ParsingStatus,
    PrimaryDriver,
    StrategyType,
    SystemEventType,
    TradeAction,
    TradeIntent,
    TradingFrequency,
    TriggerType,
)


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


experiment_mode_enum = SqlEnum(
    ExperimentMode, name="experiment_mode", values_callable=enum_values
)
strategy_type_enum = SqlEnum(
    StrategyType, name="strategy_type", values_callable=enum_values
)
experiment_status_enum = SqlEnum(
    ExperimentStatus, name="experiment_status", values_callable=enum_values
)
trading_frequency_enum = SqlEnum(
    TradingFrequency, name="trading_frequency", values_callable=enum_values
)
fee_model_type_enum = SqlEnum(
    FeeModelType, name="fee_model_type", values_callable=enum_values
)
execution_step_status_enum = SqlEnum(
    ExecutionStepStatus, name="execution_step_status", values_callable=enum_values
)
trigger_type_enum = SqlEnum(
    TriggerType, name="trigger_type", values_callable=enum_values
)
decision_source_type_enum = SqlEnum(
    DecisionSourceType, name="decision_source_type", values_callable=enum_values
)
trade_action_enum = SqlEnum(
    TradeAction, name="trade_action", values_callable=enum_values
)
trade_intent_enum = SqlEnum(
    TradeIntent, name="trade_intent", values_callable=enum_values
)
primary_driver_enum = SqlEnum(
    PrimaryDriver, name="primary_driver", values_callable=enum_values
)
final_action_enum = SqlEnum(
    FinalAction, name="final_action", values_callable=enum_values
)
order_mode_enum = SqlEnum(OrderMode, name="order_mode", values_callable=enum_values)
broker_name_enum = SqlEnum(BrokerName, name="broker_name", values_callable=enum_values)
order_side_enum = SqlEnum(OrderSide, name="order_side", values_callable=enum_values)
order_type_enum = SqlEnum(OrderType, name="order_type", values_callable=enum_values)
order_status_enum = SqlEnum(
    OrderStatus, name="order_status", values_callable=enum_values
)
agent_mode_enum = SqlEnum(AgentMode, name="agent_mode", values_callable=enum_values)
agent_step_name_enum = SqlEnum(
    AgentStepName, name="agent_step_name", values_callable=enum_values
)
parsing_status_enum = SqlEnum(
    ParsingStatus, name="parsing_status", values_callable=enum_values
)
broker_sync_status_enum = SqlEnum(
    BrokerSyncStatus, name="broker_sync_status", values_callable=enum_values
)
event_level_enum = SqlEnum(EventLevel, name="event_level", values_callable=enum_values)
system_event_type_enum = SqlEnum(
    SystemEventType, name="system_event_type", values_callable=enum_values
)
news_event_type_enum = SqlEnum(
    NewsEventType, name="news_event_type", values_callable=enum_values
)
news_event_severity_enum = SqlEnum(
    NewsEventSeverity, name="news_event_severity", values_callable=enum_values
)
impact_direction_enum = SqlEnum(
    ImpactDirection, name="impact_direction", values_callable=enum_values
)
event_decision_status_enum = SqlEnum(
    EventDecisionStatus, name="event_decision_status", values_callable=enum_values
)
