
from datetime import UTC, datetime
from uuid import UUID

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.constants.auth import REFRESH_TOKEN_TYPE
from app.constants.messages import (
    ACCOUNT_INACTIVE,
    DATABASE_CONFLICT,
    EMAIL_ALREADY_REGISTERED,
    INVALID_CREDENTIALS,
    INVALID_REFRESH_TOKEN,
)
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository


class AuthService:
    def __init__(
        self,
        user_repository: SQLAlchemyUserRepository,
        refresh_token_repository: SQLAlchemyRefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.session: AsyncSession = user_repository.session

    def _decode_refresh_token(self, token: str) -> tuple[UUID, UUID]:
        try:
            payload = decode_token(token)

            if payload.get("type") != REFRESH_TOKEN_TYPE:
                raise UnauthorizedException(INVALID_REFRESH_TOKEN)

            user_id = UUID(str(payload["sub"]))
            jti = UUID(str(payload["jti"]))

            return user_id, jti

        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise UnauthorizedException(INVALID_REFRESH_TOKEN) from exc

    async def register(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
    ) -> User:
        normalized_email = email.strip().lower()

        existing_user = await self.user_repository.get_by_email(
            normalized_email,
        )

        if existing_user is not None:
            raise ConflictException(EMAIL_ALREADY_REGISTERED)

        hashed_password = await run_in_threadpool(
            hash_password,
            password,
        )

        try:
            user = await self.user_repository.create_user(
                email=normalized_email,
                full_name=full_name,
                hashed_password=hashed_password,
            )

            await self.session.commit()

            return user

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(EMAIL_ALREADY_REGISTERED) from exc

        except Exception:
            await self.session.rollback()
            raise

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> tuple[str, str]:
        user = await self.user_repository.get_by_email(
            email.strip().lower(),
        )

        if user is None:
            raise UnauthorizedException(INVALID_CREDENTIALS)

        password_is_valid = await run_in_threadpool(
            verify_password,
            password,
            user.hashed_password,
        )

        if not password_is_valid:
            raise UnauthorizedException(INVALID_CREDENTIALS)

        if not user.is_active:
            raise UnauthorizedException(ACCOUNT_INACTIVE)

        access_token = create_access_token(user.id)

        refresh_token, jti, expires_at = create_refresh_token(user.id)

        try:
            await self.refresh_token_repository.create_refresh_token(
                user_id=user.id,
                jti=jti,
                expires_at=expires_at,
            )

            await self.session.commit()

            return access_token, refresh_token

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(DATABASE_CONFLICT) from exc

        except Exception:
            await self.session.rollback()
            raise

    async def refresh(
        self,
        *,
        refresh_token: str,
    ) -> tuple[str, str]:
        user_id, jti = self._decode_refresh_token(refresh_token)

        try:
            stored_token = (
                await self.refresh_token_repository.get_by_jti_for_update(jti)
            )

            if (
                stored_token is None
                or stored_token.user_id != user_id
                or stored_token.revoked_at is not None
                or stored_token.expires_at <= datetime.now(UTC)
            ):
                raise UnauthorizedException(INVALID_REFRESH_TOKEN)

            user = await self.user_repository.get_by_id(user_id)

            if user is None or not user.is_active:
                raise UnauthorizedException(INVALID_REFRESH_TOKEN)

            await self.refresh_token_repository.revoke(stored_token)

            new_access_token = create_access_token(user.id)

            new_refresh_token, new_jti, new_expires_at = (
                create_refresh_token(user.id)
            )

            await self.refresh_token_repository.create_refresh_token(
                user_id=user.id,
                jti=new_jti,
                expires_at=new_expires_at,
            )

            await self.session.commit()

            return new_access_token, new_refresh_token

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(DATABASE_CONFLICT) from exc

        except Exception:
            await self.session.rollback()
            raise

    async def logout(self, *, refresh_token: str) -> None:
        user_id, jti = self._decode_refresh_token(refresh_token)

        try:
            stored_token = (
                await self.refresh_token_repository.get_by_jti_for_update(jti)
            )

            if (
                stored_token is None
                or stored_token.user_id != user_id
                or stored_token.expires_at <= datetime.now(UTC)
            ):
                raise UnauthorizedException(INVALID_REFRESH_TOKEN)

            if stored_token.revoked_at is None:
                await self.refresh_token_repository.revoke(stored_token)

            await self.session.commit()

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(DATABASE_CONFLICT) from exc

        except Exception:
            await self.session.rollback()
            raise
