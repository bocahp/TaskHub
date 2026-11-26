
from fastapi import APIRouter, status

from app.dependencies.auth import CurrentUser
from app.dependencies.user import UserServiceDep
from app.schemas.user import (
    ChangePasswordRequest,
    UserProfileUpdate,
    UserResponse,
)

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_my_profile(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserResponse:
    user = await service.update_profile(
        current_user,
        full_name=payload.full_name,
    )

    return UserResponse.model_validate(user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> None:
    await service.change_password(
        current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
