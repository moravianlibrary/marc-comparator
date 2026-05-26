import logging
from typing import Annotated, Literal, Union

import redis.asyncio as aioredis
from pydantic import BaseModel, Field, TypeAdapter

from config import config

logger = logging.getLogger(__name__)

CHANNEL = "ws:events"


class TaskStatusEvent(BaseModel):
    type: Literal["task_status"] = "task_status"
    task_id: str
    task_type: str
    name: str
    status: str
    severity: str
    created_by: str


class TaskProgressEvent(BaseModel):
    type: Literal["task_progress"] = "task_progress"
    task_id: str
    progress: float
    created_by: str


class LockAcquiredEvent(BaseModel):
    type: Literal["lock_acquired"] = "lock_acquired"
    lock_name: str


class LockReleasedEvent(BaseModel):
    type: Literal["lock_released"] = "lock_released"
    lock_name: str


Event = Annotated[
    Union[TaskStatusEvent, TaskProgressEvent, LockAcquiredEvent, LockReleasedEvent],
    Field(discriminator="type"),
]

_event_adapter = TypeAdapter(Event)


def parse_event(raw: str) -> Event:
    return _event_adapter.validate_json(raw)


def publish_event(event: Event) -> None:
    """Publish an event to Redis Pub/Sub. Sync -- safe to call from Celery worker."""
    from adapters.lock_server import lock_server_client

    try:
        lock_server_client.publish(CHANNEL, event.model_dump_json())
    except Exception:
        logger.warning("Failed to publish event to Redis", exc_info=True)


async def subscribe_events(on_event) -> None:
    """Subscribe to Redis Pub/Sub and call on_event for each message.

    Runs forever -- meant to be launched as an asyncio background task.
    Reconnects on failure with a 1-second backoff.
    """
    import asyncio

    while True:
        client = None
        pubsub = None
        try:
            client = aioredis.Redis(
                host=config.broker.host,
                port=config.broker.port,
                db=config.broker.db,
            )
            pubsub = client.pubsub()
            await pubsub.subscribe(CHANNEL)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = parse_event(message["data"])
                    await on_event(event)
                except Exception:
                    logger.warning("Failed to handle event", exc_info=True)
        except Exception:
            logger.warning("Redis subscriber disconnected, reconnecting...", exc_info=True)
            await asyncio.sleep(1)
        finally:
            try:
                if pubsub:
                    await pubsub.close()
                if client:
                    await client.close()
            except Exception:
                pass
