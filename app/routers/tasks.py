from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies.auth import CurrentUser
from app.dependencies.task import TaskServiceDep
from app.domain.task import TaskEntity
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"],
)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    payload: TaskCreate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> TaskEntity:
    return await service.create_task(
        created_by=current_user.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
    )


@router.get(
    "",
    response_model=list[TaskResponse],
)
async def list_tasks(
    current_user: CurrentUser,
    service: TaskServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TaskEntity]:
    return await service.list_tasks(
        skip=skip,
        limit=limit,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> TaskEntity:
    return await service.get_task(
        task_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> TaskEntity:
    changes = payload.model_dump(exclude_unset=True)

    return await service.update_task(
        task_id,
        changes,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: UUID,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> None:
    await service.delete_task(
        task_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )
