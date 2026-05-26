from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.enums import BrokerName, BrokerSyncStatus


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return float(value)
        return value


class BrokerSyncLogResponse(CamelModel):
    id: int
    execution_step_id: int = Field(alias="executionStepId")
    experiment_id: int = Field(alias="experimentId")
    timestamp: datetime
    broker_name: BrokerName = Field(alias="brokerName")
    sync_status: BrokerSyncStatus = Field(alias="syncStatus")
    broker_cash: Decimal | None = Field(alias="brokerCash")
    local_cash: Decimal | None = Field(alias="localCash")
    broker_positions_json: dict[str, Any] | None = Field(alias="brokerPositionsJson")
    local_positions_json: dict[str, Any] | None = Field(alias="localPositionsJson")
    mismatch_details_json: dict[str, Any] | None = Field(alias="mismatchDetailsJson")
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")


class PaginatedBrokerSyncLogResponse(CamelModel):
    items: list[BrokerSyncLogResponse]
    limit: int
    offset: int
    total: int
