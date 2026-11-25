from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.dependencies.auth import CurrentUser
from app.dependencies.task import TaskServiceDep
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(
    tags=["Tasks"],
)


@router.post(
    "/api/v1/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: UUID,
    payload: TaskCreate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return await service.create_task(
        project_id=project_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
    )


@router.get(
    "/api/v1/projects/{project_id}/tasks",
    response_model=list[TaskResponse],
)
async def list_tasks(
    project_id: UUID,
    current_user: CurrentUser,
    service: TaskServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Task]:
    return await service.list_tasks(
        project_id,
        offset=offset,
        limit=limit,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.get(
    "/api/v1/tasks/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return await service.get_task(
        task_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.patch(
    "/api/v1/tasks/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    changes = payload.model_dump(exclude_unset=True)

    return await service.update_task(
        task_id,
        changes,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.delete(
    "/api/v1/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: UUID,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Response:
    await service.delete_task(
        task_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
