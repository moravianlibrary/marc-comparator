from typing import Generic, List, TypeVar

from pydantic import BaseModel


class PageRequestParams(BaseModel):
    page: int = 1
    page_size: int = 20


Item = TypeVar("Item", bound=BaseModel)


class Page(BaseModel, Generic[Item]):
    items: List[Item]
    num_found: int
