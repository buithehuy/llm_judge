from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationParams(BaseModel):
    """
    Standard pagination query parameters.

    Attributes:
        page: 1-indexed current page number.
        page_size: Number of items per page (max 100 to prevent abuse).
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )

    @property
    def offset(self) -> int:
        """Calculate SQL OFFSET from page number."""
        return (self.page - 1) * self.page_size
    
class PagedResponse(BaseModel, Generic[DataT]):
    """
    Generic paginated response envelope.

    Wraps any list of items with metadata needed for frontend pagination.

    Example response::

        {
            "items": [...],
            "total": 42,
            "page": 1,
            "page_size": 20,
            "total_pages": 3
        }
    """

    items: List[DataT]
    total: int = Field(description="Total number of records matching the query")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")

class TokenResponse(BaseModel):
    """
    OAuth2-compatible token response.

    Attributes:
        access_token: The signed JWT string.
        token_type: Always "bearer" per OAuth2 spec.
    """

    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Simple success/status message response."""

    message: str
    success: bool = True