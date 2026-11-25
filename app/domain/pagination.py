from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PaginationParams:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


@dataclass(frozen=True, slots=True)
class PaginatedResult[T]:
    items: list[T]
    total: int
    page: int
    limit: int
