import logging
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver import Client

from config import config

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_clickhouse_client() -> Client:
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            database=config.clickhouse.database,
            username=config.clickhouse.user,
            password=config.clickhouse.password,
        )
    return _client


def close_clickhouse_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def query(sql: str, parameters: dict[str, Any] | None = None) -> list[dict]:
    """Execute a ClickHouse query and return rows as dicts."""
    client = get_clickhouse_client()
    result = client.query(sql, parameters=parameters or {})
    columns = result.column_names
    return [dict(zip(columns, row)) for row in result.result_rows]


def insert(table: str, data: list[list], column_names: list[str]) -> None:
    """Batch insert rows into a ClickHouse table."""
    client = get_clickhouse_client()
    client.insert(table, data, column_names=column_names)


def command(sql: str) -> None:
    """Execute a ClickHouse command (DDL, etc.)."""
    client = get_clickhouse_client()
    client.command(sql)
