from typing import Annotated
from fastapi import Query
from pydantic import BaseModel, Field


class PageParams(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchParams(BaseModel):
    q: str | None = Field(default=None, min_length=1, max_length=255)


PageDep = Annotated[PageParams, Query()]
SearchDep = Annotated[SearchParams, Query()]
