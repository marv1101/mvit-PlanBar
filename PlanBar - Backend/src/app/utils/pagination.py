import math

from sqlalchemy.orm import Query

from app.schemas.common import PaginationResponse


def paginate(query: Query, page: int = 1, page_size: int = 20) -> tuple[list, PaginationResponse]:
    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))

    items = query.offset((page - 1) * page_size).limit(page_size).all()

    pagination = PaginationResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    return items, pagination
