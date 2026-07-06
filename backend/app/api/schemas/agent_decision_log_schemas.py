from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AgentMode, AgentStepName, ParsingStatus, TriggerType


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentDecisionLogResponse(CamelModel):
    id: int
    execution_step_id: int = Field(alias="executionStepId")
    experiment_id: int = Field(alias="experimentId")
    trading_decision_id: int | None = Field(alias="tradingDecisionId")
    agent_mode: AgentMode = Field(alias="agentMode")
    agent_step_name: AgentStepName = Field(alias="agentStepName")
    agent_name: str | None = Field(alias="agentName")
    prompt_version: str | None = Field(alias="promptVersion")
    model_name: str | None = Field(alias="modelName")
    model_version: str | None = Field(alias="modelVersion")
    input_json: dict[str, Any] | None = Field(alias="inputJson")
    prompt_text: str | None = Field(alias="promptText")
    raw_output_text: str | None = Field(alias="rawOutputText")
    parsed_output_json: dict[str, Any] | None = Field(alias="parsedOutputJson")
    parsing_status: ParsingStatus = Field(alias="parsingStatus")
    repair_prompt_text: str | None = Field(alias="repairPromptText")
    repair_raw_output_text: str | None = Field(alias="repairRawOutputText")
    trigger_type: TriggerType | None = Field(default=None, alias="triggerType")
    execution_step_sequence_number: int | None = Field(
        default=None,
        alias="executionStepSequenceNumber",
    )
    created_at: datetime = Field(alias="createdAt")


class PaginatedAgentDecisionLogResponse(CamelModel):
    items: list[AgentDecisionLogResponse]
    limit: int
    offset: int
    total: int
