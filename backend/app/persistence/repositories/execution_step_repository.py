from app.persistence.models import ExecutionStepModel
from app.persistence.repositories.base import BaseRepository


class ExecutionStepRepository(BaseRepository[ExecutionStepModel]):
    model = ExecutionStepModel
