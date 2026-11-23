
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.constants.auth import ACCESS_TOKEN_TYPE
from app.constants.messages import INVALID_TOKEN
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.dependencies.database import DbSession
from app.models.user import User
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.services.auth import AuthService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)


def get_auth_service(session: DbSession) -> AuthService:
    user_repository = SQLAlchemyUserRepository(session)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(session)

    return AuthService(
        user_repository,
        refresh_token_repository,
    )


AuthServiceDep = Annotated[
    AuthService,
    Depends(get_auth_service),
]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DbSession,
) -> User:
    try:
        payload = decode_token(token)

        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise UnauthorizedException(INVALID_TOKEN)

        user_id = UUID(str(payload["sub"]))

    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedException(INVALID_TOKEN) from exc

    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise UnauthorizedException(INVALID_TOKEN)

    return user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]
