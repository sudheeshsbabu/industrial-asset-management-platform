from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel
from yarl import URL

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    next: Optional[str]
    prev: Optional[str]
    results: List[T]

    @classmethod
    def build_paginated_response(
        cls,
        results: List[T],
        total_count: int,
        page: int,
        page_size: int,
        url: URL
    ):
        next_url = None
        if (page * page_size) < total_count:
            next_url = str(url.with_query({"page": page + 1, "page_size": page_size}))
        prev_url = None
        if page > 1:
            prev_url = str(url.with_query({"page": page - 1, "page_size": page_size}))
        
        return cls(
            count=total_count,
            next=next_url,
            prev=prev_url,
            results=results
        )