
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.constants.auth import (
    AUTH_PASSWORD_MAX_LENGTH,
    AUTH_PASSWORD_MIN_LENGTH,
)
from app.constants.database import EMAIL_MAX_LENGTH, FULL_NAME_MAX_LENGTH
from app.schemas.base import AuthInputSchema, BaseSchema


class RegisterRequest(AuthInputSchema):
    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)

    full_name: str = Field(
        min_length=1,
        max_length=FULL_NAME_MAX_LENGTH,
    )

    password: str = Field(
        min_length=AUTH_PASSWORD_MIN_LENGTH,
        max_length=AUTH_PASSWORD_MAX_LENGTH,
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()

        return value

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class RefreshTokenRequest(AuthInputSchema):
    refresh_token: str = Field(
        min_length=1,
        max_length=4096,
    )

    @field_validator("refresh_token")
    @classmethod
    def normalize_refresh_token(cls, value: str) -> str:
        return value.strip()
