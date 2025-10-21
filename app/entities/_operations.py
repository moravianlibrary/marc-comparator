from typing import List, Self, Type

from adapters.database import DatabaseSession
from adapters.indexer import IndexerSchema


class BaseOperationsMixin:
    __indexer_schema__: Type[IndexerSchema] = IndexerSchema

    @classmethod
    def get(cls, db_session: DatabaseSession, entity_id) -> Self:
        """
        Retrieve an entity by its ID.

        Parameters
        ----------
        db_session : DatabaseSession
            The database session to use for the query.
        entity_id : Any
            The ID of the entity to retrieve.

        Returns
        -------
        DatabaseEntityType | None
            The entity if found, otherwise None.
        """
        entity = db_session.get(cls, entity_id)
        if entity is None:
            raise ValueError(f"{cls.__name__} with ID {entity_id} not found")
        return entity

    @classmethod
    def find(cls, db_session: DatabaseSession, entity_id) -> Self | None:
        """
        Retrieve an entity by its ID.

        Parameters
        ----------
        db_session : DatabaseSession
            The database session to use for the query.
        entity_id : Any
            The ID of the entity to retrieve.

        Returns
        -------
        DatabaseEntityType | None
            The entity if found, otherwise None.
        """
        return db_session.get(cls, entity_id)

    def save(self: Self, db_session: DatabaseSession) -> Self:
        """
        Persist the entity to the database.

        Parameters
        ----------
        entity : DatabaseEntityType
            The entity to save.

        Returns
        -------
        DatabaseEntityType
            The saved entity with refreshed state.
        """
        db_session.add(self)
        db_session.commit()
        db_session.refresh(self)
        return self

    async def index(self: Self) -> Self:
        """
        Index the entity using the indexer model.

        Returns
        -------
        DatabaseEntityType
            The indexed entity.
        """
        await self.__indexer_schema__.model_validate(
            self, from_attributes=True
        ).save()
        return self

    @classmethod
    async def bulk_index(cls, entities: List[Self]) -> None:
        """
        Bulk index a list of entities using the indexer model.

        Parameters
        ----------
        entities : List[DatabaseEntityType]
            The list of entities to index.
        """
        id_field = cls.__indexer_schema__.ESConfig.id_field
        operations = []
        for entity in entities:
            if entity is None:
                raise ValueError("Cannot index None entity")
            schema: type[IndexerSchema] = (
                cls.__indexer_schema__.model_validate(
                    entity, from_attributes=True
                )
            )
            operations.append({"index": {"_id": schema.__id__}})
            operations.append(schema.model_dump(exclude={id_field}))
        await cls.__indexer_schema__.call(
            "bulk",
            operations=operations,
            refresh="wait_for",
        )
