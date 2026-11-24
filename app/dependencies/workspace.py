from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DbSession
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.repositories.sqlalchemy_workspace import (
    SQLAlchemyWorkspaceRepository,
)
from app.services.workspace import SQLAlchemyWorkspaceService


def get_workspace_service(session: DbSession) -> SQLAlchemyWorkspaceService:
    workspace_repository = SQLAlchemyWorkspaceRepository(session)
    user_repository = SQLAlchemyUserRepository(session)

    return SQLAlchemyWorkspaceService(
        workspace_repository,
        user_repository,
    )


WorkspaceServiceDep = Annotated[
    SQLAlchemyWorkspaceService,
    Depends(get_workspace_service),
]
