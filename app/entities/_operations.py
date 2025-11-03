from typing import AsyncGenerator, List, Self, Type

from esorm import es
from sqlalchemy import inspect

from adapters.database import DatabaseSession
from adapters.indexer import (
    IndexerQuery,
    IndexerRequest,
    IndexerResponse,
    IndexerSchema,
)


class BaseOperationsMixin:
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

    def delete(self: Self, db_session: DatabaseSession) -> Self:
        """
        Delete the entity from the database.

        Parameters
        ----------
        db_session : DatabaseSession
            The database session to use for the query.

        Returns
        -------
        DatabaseEntityType
            The deleted entity.
        """
        db_session.delete(self)
        db_session.commit()
        return self


class RetrievalOperationsMixin:
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


class IndexerOperationsMixin:
    __indexer_schema__: Type[IndexerSchema] = IndexerSchema

    async def index(self: Self, wait_for: bool = False) -> Self:
        """
        Index the entity using the indexer model.

        Returns
        -------
        DatabaseEntityType
            The indexed entity.
        """
        await self.__indexer_schema__.model_validate(
            self, from_attributes=True
        ).save(wait_for=wait_for)
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

    @classmethod
    async def get_by_query(
        cls, db_session: DatabaseSession, query: IndexerQuery
    ) -> AsyncGenerator[Self, None]:
        """
        Yield database entities by running an indexer scroll query.

        Parameters
        ----------
        db_session : DatabaseSession
            The database session to use for retrieving entities.
        query : IndexerQuery
            Indexer query body to perform.

        Yields
        ------
        AsyncGenerator[Self, None]
            An async generator yielding database entities.
        """
        index_name = cls.__indexer_schema__.ESConfig.index
        id_field = cls.__indexer_schema__.ESConfig.id_field
        id_column = inspect(cls).c[id_field]
        query_body = query.model_dump(mode="python")

        scroll_id = None

        while True:
            response = (
                await es.scroll(scroll_id=scroll_id, scroll="1m")
                if scroll_id
                else await es.search(
                    index=index_name,
                    body=query_body,
                    scroll="1m",
                    fields=[id_field],
                )
            )

            for hit in response["hits"]["hits"]:
                yield db_session.query(cls).filter(
                    id_column == hit["_id"]
                ).one()

            scroll_id = response.get("_scroll_id")
            if not scroll_id or not response["hits"]["hits"]:
                break

        await es.clear_scroll(scroll_id=scroll_id)

    @classmethod
    async def search(cls, request: IndexerRequest) -> IndexerResponse:
        """
        Search the indexer for entities matching the request.

        Parameters
        ----------
        request : IndexerRequest
            The indexer request containing query parameters.

        Returns
        -------
        IndexerResponse
            The response containing the search results.
        """
        index_name = cls.__indexer_schema__.ESConfig.index_name
        return (
            await es.search(index=index_name, body=request.model_dump())
        ).body
