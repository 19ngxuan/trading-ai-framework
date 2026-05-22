from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        return instance

    def get(self, id_: int) -> ModelT | None:
        return self.session.get(self.model, id_)

    def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        statement = select(self.model).limit(limit).offset(offset)
        return list(self.session.scalars(statement))
