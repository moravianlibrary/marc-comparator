from typing import Self

from adapters.database import DatabaseSession


class BaseOperationsMixin:
    def save(self: Self, db_session: DatabaseSession, *, commit: bool = True) -> Self:
        db_session.add(self)
        if commit:
            db_session.commit()
            db_session.refresh(self)
        else:
            db_session.flush()
        return self

    def delete(self: Self, db_session: DatabaseSession, *, commit: bool = True) -> Self:
        db_session.delete(self)
        if commit:
            db_session.commit()
        return self


class RetrievalOperationsMixin:
    @classmethod
    def get(cls, db_session: DatabaseSession, entity_id) -> Self:
        entity = db_session.get(cls, entity_id)
        if entity is None:
            raise ValueError(f"{cls.__name__} with ID {entity_id} not found")
        return entity

    @classmethod
    def find(cls, db_session: DatabaseSession, entity_id) -> Self | None:
        return db_session.get(cls, entity_id)
