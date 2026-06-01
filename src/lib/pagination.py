from typing import Annotated
from fastapi import Query
from pydantic import BaseModel, Field

MAX_PAGE_LIMIT = 100


class PageParams(BaseModel):
    limit: int = Field(default=10, ge=1, le=MAX_PAGE_LIMIT)
    offset: int = Field(default=0, ge=0)


class SearchParams(BaseModel):
    q: str | None = Field(default=None, min_length=1, max_length=255)


PageDep = Annotated[PageParams, Query()]
SearchDep = Annotated[SearchParams, Query()]
