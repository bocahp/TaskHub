
from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DbSession
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.services.user import UserService


def get_user_service(session: DbSession) -> UserService:
    user_repository = SQLAlchemyUserRepository(session)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(session)

    return UserService(
        user_repository,
        refresh_token_repository,
    )


UserServiceDep = Annotated[
    UserService,
    Depends(get_user_service),
]
