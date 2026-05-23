from pydantic import BaseModel, ConfigDict


class RunNextStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    triggerReason: str | None = None


class RunNextStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experimentId: int
    executionStepId: int | None
    status: str
    message: str
