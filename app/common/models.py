from typing import TypeVar

from pydantic import BaseModel


class PageRequestParams(BaseModel):
    page: int = 1
    page_size: int = 20


Item = TypeVar("Item", bound=BaseModel)


class Page[Item: BaseModel](BaseModel):
    items: list[Item]
    num_found: int
