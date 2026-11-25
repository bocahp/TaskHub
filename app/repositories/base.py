from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.base import Base
from app.domain.pagination import PaginatedResult, PaginationParams


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
        values: dict[str, object],
    ) -> ModelT:
        entity = self.model(**values)

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
        pagination: PaginationParams,
        order_by: Sequence[ColumnElement[Any]],
        filters: Sequence[ColumnElement[bool]] = (),
    ) -> list[ModelT]:
        statement = (
            select(self.model)
            .where(*filters)
            .order_by(*order_by)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )

        result = await self.session.scalars(statement)

        return list(result.all())

    async def paginate(
        self,
        *,
        pagination: PaginationParams,
        order_by: Sequence[ColumnElement[Any]],
        filters: Sequence[ColumnElement[bool]] = (),
    ) -> PaginatedResult[ModelT]:
        count_statement = select(func.count()).select_from(self.model).where(*filters)

        total = await self.session.scalar(count_statement)

        items = await self.list_all(
            pagination=pagination,
            order_by=order_by,
            filters=filters,
        )

        return PaginatedResult(
            items=items,
            total=total or 0,
            page=pagination.page,
            limit=pagination.limit,
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
