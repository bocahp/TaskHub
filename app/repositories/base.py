from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.constants.database import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.db.base import Base
from app.domain.pagination import PaginatedResult


class BaseRepository[ModelT: Base]:
    def __init__(
        self,
        session: AsyncSession,
        model: type[ModelT],
    ) -> None:
        self.session = session
        self.model = model

    async def create(
        self,
        values: Mapping[str, object],
    ) -> ModelT:
        entity = self.model(**dict(values))

        self.session.add(entity)

        await self.session.flush()
        await self.session.refresh(entity)

        return entity

    async def get_by_id(
        self,
        entity_id: UUID,
    ) -> ModelT | None:
        id_column = self.model.__table__.c.id

        statement = select(self.model).where(id_column == entity_id)

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        order_by: Sequence[ColumnElement[Any]],
    ) -> list[ModelT]:
        statement = select(self.model).order_by(*order_by).offset(offset).limit(limit)

        result = await self.session.scalars(statement)

        return list(result.all())

    async def paginate(
        self,
        *,
        page: int = DEFAULT_PAGE,
        limit: int = DEFAULT_PAGE_SIZE,
        order_by: Sequence[ColumnElement[Any]],
    ) -> PaginatedResult[ModelT]:
        count_statement = select(func.count()).select_from(self.model)

        total = await self.session.scalar(count_statement)

        items = await self.list_all(
            offset=(page - 1) * limit,
            limit=limit,
            order_by=order_by,
        )

        return PaginatedResult(
            items=items,
            total=total or 0,
            page=page,
            limit=limit,
        )

    async def update(
        self,
        entity: ModelT,
    ) -> ModelT:
        await self.session.flush()
        await self.session.refresh(entity)

        return entity

    async def delete(
        self,
        entity: ModelT,
    ) -> None:
        await self.session.delete(entity)
        await self.session.flush()
