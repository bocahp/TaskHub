from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)


def test_workspace_create_normalizes_name() -> None:
    payload = WorkspaceCreate(name="  Engineering Team  ")

    assert payload.name == "Engineering Team"


def test_workspace_create_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreate(name="   ")


def test_workspace_create_rejects_name_exceeding_max_length() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreate(name="a" * 201)


def test_workspace_update_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        WorkspaceUpdate(name=" ")


def test_workspace_member_create_defaults_to_viewer() -> None:
    payload = WorkspaceMemberCreate(
        email="member@example.com",
    )

    assert payload.email == "member@example.com"
    assert payload.role == WorkspaceRole.VIEWER


def test_workspace_member_create_accepts_editor_role() -> None:
    payload = WorkspaceMemberCreate(
        email="editor@example.com",
        role=WorkspaceRole.EDITOR,
    )

    assert payload.role == WorkspaceRole.EDITOR


def test_workspace_member_create_rejects_owner_role() -> None:
    with pytest.raises(ValidationError):
        WorkspaceMemberCreate(
            email="owner@example.com",
            role=WorkspaceRole.OWNER,
        )


def test_workspace_member_role_update_rejects_owner_role() -> None:
    with pytest.raises(ValidationError):
        WorkspaceMemberRoleUpdate(role=WorkspaceRole.OWNER)


def test_workspace_schemas_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreate(
            name="Engineering",
            owner_id=uuid4(),
        )


def test_workspace_response_validates_data() -> None:
    workspace_id = uuid4()
    owner_id = uuid4()

    response = WorkspaceResponse(
        id=workspace_id,
        name="Engineering",
        owner_id=owner_id,
    )

    assert response.id == workspace_id
    assert response.owner_id == owner_id


def test_workspace_member_response_validates_data() -> None:
    user_id = uuid4()

    response = WorkspaceMemberResponse(
        user_id=user_id,
        email="member@example.com",
        full_name="Test Member",
        role=WorkspaceRole.EDITOR,
    )

    assert response.user_id == user_id
    assert response.email == "member@example.com"
    assert response.full_name == "Test Member"
    assert response.role == WorkspaceRole.EDITOR
