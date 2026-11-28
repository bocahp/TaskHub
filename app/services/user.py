from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.constants.messages import (
    DATABASE_CONFLICT,
    INVALID_CREDENTIALS,
)
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository


class UserService:
    def __init__(
        self,
        user_repository: SQLAlchemyUserRepository,
        refresh_token_repository: SQLAlchemyRefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.session: AsyncSession = user_repository.session

    async def update_profile(
        self,
        user: User,
        *,
        full_name: str,
    ) -> User:
        user.full_name = full_name

        try:
            await self.user_repository.update(user)
            await self.session.commit()

            return user

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(DATABASE_CONFLICT) from exc

        except Exception:
            await self.session.rollback()
            raise

    async def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        password_is_valid = await run_in_threadpool(
            verify_password,
            current_password,
            user.hashed_password,
        )

        if not password_is_valid:
            raise UnauthorizedException(INVALID_CREDENTIALS)

        new_hashed_password = await run_in_threadpool(
            hash_password,
            new_password,
        )

        try:
            user.hashed_password = new_hashed_password
            user.token_version += 1

            await self.user_repository.update(user)

            await self.refresh_token_repository.revoke_all_for_user(
                user.id,
            )

            await self.session.commit()

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(DATABASE_CONFLICT) from exc

        except Exception:
            await self.session.rollback()
            raise
