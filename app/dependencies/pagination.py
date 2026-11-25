from typing import Annotated

from fastapi import Depends, Query

from app.constants.database import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)
from app.domain.pagination import PaginationParams


def get_pagination(
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE),
    ] = DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    return PaginationParams(
        page=page,
        limit=limit,
    )


PaginationDep = Annotated[
    PaginationParams,
    Depends(get_pagination),
]
