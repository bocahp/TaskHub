from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DbSession
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository
from app.services.sqlalchemy_task import SQLAlchemyTaskService


def get_task_service(session: DbSession) -> SQLAlchemyTaskService:
    repository = SQLAlchemyTaskRepository(session)

    return SQLAlchemyTaskService(repository)


TaskServiceDep = Annotated[
    SQLAlchemyTaskService,
    Depends(get_task_service),
]
