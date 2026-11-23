
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.constants.auth import (
    AUTH_PASSWORD_MAX_LENGTH,
    AUTH_PASSWORD_MIN_LENGTH,
)
from app.constants.database import FULL_NAME_MAX_LENGTH
from app.domain.enums import UserRole
from app.schemas.base import AuthInputSchema, BaseSchema


class UserResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseSchema):
    full_name: str = Field(
        min_length=1,
        max_length=FULL_NAME_MAX_LENGTH,
    )


class ChangePasswordRequest(AuthInputSchema):
    current_password: str = Field(
        min_length=1,
        max_length=AUTH_PASSWORD_MAX_LENGTH,
    )

    new_password: str = Field(
        min_length=AUTH_PASSWORD_MIN_LENGTH,
        max_length=AUTH_PASSWORD_MAX_LENGTH,
    )
