
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.constants.auth import (
    ACCESS_TOKEN_TYPE,
    JWT_ALGORITHM,
    REFRESH_TOKEN_TYPE,
)
from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def _create_token(
    user_id: UUID,
    token_type: str,
    expires_delta: timedelta,
) -> tuple[str, UUID, datetime]:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + expires_delta
    token_id = uuid4()

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "jti": str(token_id),
        "iat": issued_at,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )

    return token, token_id, expires_at


def create_access_token(user_id: UUID) -> str:
    token, _, _ = _create_token(
        user_id=user_id,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes,
        ),
    )

    return token


def create_refresh_token(
    user_id: UUID,
) -> tuple[str, UUID, datetime]:
    return _create_token(
        user_id=user_id,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days,
        ),
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        options={
            "require": ["exp", "iat", "sub", "type", "jti"],
        },
    )
