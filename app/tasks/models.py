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


class TracebackLinesRequestParams(BaseModel):
    start_line: int | None = Field(default=None, alias="from")
    end_line: int | None = Field(default=None, alias="to")
