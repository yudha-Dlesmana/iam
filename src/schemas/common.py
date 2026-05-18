from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    data: T | None = None

    @classmethod
    def ok(cls, data: T, message: str = "success") -> "ApiResponse[T]":
        return cls(code=200, message=message, data=data)
    
    @classmethod
    def fail(cls, code:int, message:str) -> "ApiResponse[None]":
        return cls(code=code, message=message, data=None)

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int