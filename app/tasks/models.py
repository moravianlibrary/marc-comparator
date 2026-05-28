from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from entities.settings import SettingsSchema


class TaskSettings(SettingsSchema):
    progress_update_interval: int = Field(
        100,
        description="Interval (in number of records) to update task progress.",
    )
    indexing_batch_size: int = Field(
        500,
        description="Number of records to index in a single batch operation.",
    )
    analytics_rebuild_interval: int = Field(
        5000,
        description=(
            "Interval (in number of records) to rebuild analytics and facet cube "
            "during long-running tasks. 0 to disable mid-task rebuilds."
        ),
    )


class TracebackLinesRequestParams(BaseModel):
    start_line: int | None = Field(default=None, alias="from", ge=0)
    end_line: int | None = Field(default=None, alias="to", ge=0)


class TaskFilter(BaseModel):
    type: list[str] | None = None
    status: list[str] | None = None
    severity: list[str] | None = None
    created_by: str | None = None


class SearchTasksRequest(BaseModel):
    filters: TaskFilter = TaskFilter()
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    sort_by: Literal["created_at", "started_at", "finished_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class TaskSummary(BaseModel):
    task_id: UUID
    name: str
    type: str
    status: str
    severity: str
    created_by: UUID
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: float
    traceback_lines: int


class SearchTasksResponse(BaseModel):
    items: list[TaskSummary]
    total: int
    page: int
    page_size: int
