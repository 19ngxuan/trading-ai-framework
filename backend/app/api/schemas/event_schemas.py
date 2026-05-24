from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EventLevel, SystemEventType


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SystemEventResponse(CamelModel):
    id: int
    experiment_id: int = Field(alias="experimentId")
    execution_step_id: int | None = Field(alias="executionStepId")
    timestamp: datetime
    level: EventLevel
    event_type: SystemEventType = Field(alias="eventType")
    message: str
    details_json: dict[str, Any] | None = Field(alias="detailsJson")
    created_at: datetime = Field(alias="createdAt")


class PaginatedSystemEventResponse(CamelModel):
    items: list[SystemEventResponse]
    limit: int
    offset: int
    total: int
