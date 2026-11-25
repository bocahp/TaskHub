from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, field_validator

from app.constants.database import (
    EMAIL_MAX_LENGTH,
    WORKSPACE_NAME_MAX_LENGTH,
)
from app.domain.enums import WorkspaceRole
from app.schemas.base import BaseSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(
        min_length=1,
        max_length=WORKSPACE_NAME_MAX_LENGTH,
    )


class WorkspaceUpdate(BaseSchema):
    name: str = Field(
        min_length=1,
        max_length=WORKSPACE_NAME_MAX_LENGTH,
    )


class WorkspaceResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID


class WorkspaceMemberCreate(BaseSchema):
    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    role: WorkspaceRole = WorkspaceRole.VIEWER

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value == WorkspaceRole.OWNER:
            raise ValueError(
                "The OWNER role cannot be assigned through member management"
            )

        return value


class WorkspaceMemberRoleUpdate(BaseSchema):
    role: WorkspaceRole

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value == WorkspaceRole.OWNER:
            raise ValueError(
                "The OWNER role cannot be assigned through member management"
            )

        return value


class WorkspaceMemberResponse(BaseSchema):
    user_id: UUID
    email: EmailStr
    full_name: str
    role: WorkspaceRole


class WorkspaceListResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    items: list[WorkspaceResponse]
    total: int
    page: int
    limit: int


class WorkspaceMemberListResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    items: list[WorkspaceMemberResponse]
    total: int
    page: int
    limit: int
