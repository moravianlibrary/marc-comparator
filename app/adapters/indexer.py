import asyncio
import logging
from enum import Enum
from typing import Any, Dict, Generic, List, TypeVar, Union

from aiohttp import ClientSession
from elasticsearch import AsyncElasticsearch
from esorm import ESBaseModel, ESModel, es
from esorm.fields import Keyword
from pydantic import BaseModel, Field

from config import config

logger = logging.getLogger(__name__)

IndexerSchema = ESModel
IndexerNestedModel = ESBaseModel
IndexerSession = AsyncElasticsearch


class IndexerQuery(BaseModel):
    class Config:
        extra = "allow"


class IndexerRequest(IndexerQuery):
    pass


class Hit(BaseModel):
    """
    Represents a single hit (result) from Elasticsearch.
    """

    index: str = Field(..., alias="_index")
    """ The index the hit is from. """
    id: str = Field(..., alias="_id")
    """ The id of the hit. """
    score: float | None = Field(..., alias="_score")
    """ The score of the hit. """
    source: Any = Field(..., alias="_source")
    """ The source of the hit. """

    class Config:
        populate_by_name = True


class HitsTotal(BaseModel):
    value: int
    relation: str


class Hits(BaseModel):
    """
    Represents the hits section of the Elasticsearch response.
    """

    total: int | HitsTotal
    """ The total number of hits. """
    max_score: float | None
    """ The maximum score of the hits. """
    hits: List[Hit]
    """ List of hits. """


class IndexerResponse(BaseModel):
    """
    Represents the overall structure of an Elasticsearch response.
    """

    took: int
    """ The time in milliseconds it took to execute the query. """
    timed_out: bool
    """ Whether the query timed out. """
    shards: Dict[str, int] = Field(..., alias="_shards")
    """ The number of shards the query was executed on. """
    hits: Hits
    """ The hits section of the response. """
    aggregations: Any | None = None
    """ The aggregations section of the response. """


IndexerSchemaType = TypeVar("IndexerSchemaType", bound=IndexerSchema)


EnumType = TypeVar("EnumType", bound=Enum)


class EnumList(Generic[EnumType]):
    __type__: type

    def __class_getitem__(cls, item):
        return Union[Keyword, List[item]]


class EnumUnion(Generic[EnumType]):
    __type__: type

    def __class_getitem__(cls, item):
        if isinstance(item, tuple):
            inner = Union[item]
        else:
            inner = item
        return Union[Keyword, inner]


def _patch_es_meta():
    original_put_mapping = es.indices.put_mapping

    async def patched_put_mapping(*args, **kwargs):
        kwargs.setdefault("dynamic", "strict")
        kwargs.setdefault("meta", {"index.version": "1.0.0"})
        return await original_put_mapping(*args, **kwargs)

    es.indices.put_mapping = patched_put_mapping


async def connect():
    es.set_client(
        AsyncElasticsearch(
            hosts=config.elasticsearch.url,
            basic_auth=(
                config.elasticsearch.username,
                config.elasticsearch.password,
            ),
            request_timeout=config.elasticsearch.request_timeout,
            max_retries=5,
            retry_on_timeout=True,
        )
    )
    _patch_es_meta()


class IndexIsNotAvailableException(Exception):
    def __init__(self):
        super().__init__(
            "Elasticsearch index is not available "
            f"({config.elasticsearch.url})",
        )


async def is_indexer_available() -> bool:
    try:
        async with ClientSession() as session:
            async with session.get(config.elasticsearch.url) as resp:
                return resp.status in [200, 401]
    except Exception as e:
        logger.error(f"Elasticsearch is not available: {str(e)}")
        return False


async def startup_indexer(retries: int = 5, backoff: int = 2) -> bool:
    """
    Try to start ES client with retries and exponential backoff.
    Returns True if ES is available, False otherwise.
    """
    attempt = 0
    while attempt < retries:
        if await is_indexer_available():
            try:
                await connect()
                if es is not None and await es.ping():
                    return True
            except Exception as e:
                logger.error(f"Elasticsearch ping failed: {e}")
        attempt += 1
        wait_time = backoff**attempt
        logger.info(
            f"Retrying Elasticsearch in {wait_time}s "
            f"(attempt {attempt}/{retries})"
        )
        await asyncio.sleep(wait_time)
    return False


async def shutdown_indexer() -> None:
    await es.close()
