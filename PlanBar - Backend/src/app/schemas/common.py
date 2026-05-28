from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
