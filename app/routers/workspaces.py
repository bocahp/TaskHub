from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.dependencies.auth import CurrentUser
from app.dependencies.workspace import WorkspaceServiceDep
from app.models.workspace import Workspace
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["Workspaces"],
)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Workspace:
    return await service.create_workspace(
        name=payload.name,
        owner_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[WorkspaceResponse],
)
async def list_workspaces(
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Workspace]:
    return await service.list_workspaces(
        current_user.id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def get_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Workspace:
    return await service.get_workspace(
        workspace_id,
        current_user.id,
    )


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Workspace:
    return await service.update_workspace(
        workspace_id,
        current_user.id,
        name=payload.name,
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Response:
    await service.delete_workspace(
        workspace_id,
        current_user.id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
)
async def list_workspace_members(
    workspace_id: UUID,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> list[WorkspaceMemberResponse]:
    members = await service.list_members(
        workspace_id,
        current_user.id,
    )

    return [
        WorkspaceMemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
        )
        for membership, user in members
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: UUID,
    payload: WorkspaceMemberCreate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    membership, user = await service.add_member(
        workspace_id,
        current_user.id,
        email=str(payload.email),
        role=payload.role,
    )

    return WorkspaceMemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
    )


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
)
async def update_workspace_member_role(
    workspace_id: UUID,
    user_id: UUID,
    payload: WorkspaceMemberRoleUpdate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    membership, user = await service.update_member_role(
        workspace_id,
        current_user.id,
        user_id,
        role=payload.role,
    )

    return WorkspaceMemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Response:
    await service.remove_member(
        workspace_id,
        current_user.id,
        user_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
