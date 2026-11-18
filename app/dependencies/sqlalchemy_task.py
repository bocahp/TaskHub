from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DbSession
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository
from app.services.sqlalchemy_task import SQLAlchemyTaskService


def get_sqlalchemy_task_repository(
    session: DbSession,
) -> SQLAlchemyTaskRepository:
    return SQLAlchemyTaskRepository(session)


def get_sqlalchemy_task_service(
    repository: Annotated[
        SQLAlchemyTaskRepository,
        Depends(get_sqlalchemy_task_repository),
    ],
) -> SQLAlchemyTaskService:
    return SQLAlchemyTaskService(repository)


SQLAlchemyTaskServiceDep = Annotated[
    SQLAlchemyTaskService,
    Depends(get_sqlalchemy_task_service),
]
