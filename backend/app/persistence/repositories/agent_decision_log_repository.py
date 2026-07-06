from sqlalchemy import func, select

from app.persistence.models import AgentDecisionLogModel
from app.persistence.repositories.base import BaseRepository


class AgentDecisionLogRepository(BaseRepository[AgentDecisionLogModel]):
    model = AgentDecisionLogModel

    def latest_for_experiment(self, experiment_id: int) -> list[AgentDecisionLogModel]:
        latest_execution_step_id = self.session.scalar(
            select(self.model.execution_step_id)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(1)
        )
        if latest_execution_step_id is None:
            return []
        statement = (
            select(self.model)
            .where(
                self.model.experiment_id == experiment_id,
                self.model.execution_step_id == latest_execution_step_id,
            )
            .order_by(self.model.created_at.asc(), self.model.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_by_experiment_paginated(
        self,
        experiment_id: int,
        limit: int,
        offset: int,
    ) -> list[AgentDecisionLogModel]:
        statement = (
            select(self.model)
            .where(self.model.experiment_id == experiment_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count_by_experiment(self, experiment_id: int) -> int:
        statement = select(func.count(self.model.id)).where(
            self.model.experiment_id == experiment_id
        )
        return int(self.session.scalar(statement) or 0)
