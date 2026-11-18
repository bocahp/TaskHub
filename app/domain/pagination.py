from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PaginatedResult[T]:
    items: list[T]
    total: int
    page: int
    limit: int
