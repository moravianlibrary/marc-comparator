from pydantic import BaseModel, Field


class TracebackLinesRequestParams(BaseModel):
    start_line: int | None = Field(default=None, alias="from")
    end_line: int | None = Field(default=None, alias="to")
