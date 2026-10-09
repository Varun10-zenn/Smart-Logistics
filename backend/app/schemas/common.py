"""
Common Pydantic schemas: pagination, error envelopes, and shared utilities.
"""
from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class Page(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMeta


def make_page(items: List[Any], total: int, page: int, page_size: int) -> dict:
    """Helper to build a Page-compatible dict."""
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


# ---------------------------------------------------------------------------
# Error envelope
# ---------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = {}
    request_id: str = ""


class ErrorResponse(BaseModel):
    error: ErrorBody
