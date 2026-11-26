
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies.auth import AuthServiceDep
from app.schemas.auth import (
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    service: AuthServiceDep,
) -> UserResponse:
    user = await service.register(
        email=str(payload.email),
        full_name=payload.full_name,
        password=payload.password,
    )

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> TokenResponse:
    access_token, refresh_token = await service.login(
        email=form_data.username,
        password=form_data.password,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    access_token, refresh_token = await service.refresh(
        refresh_token=payload.refresh_token,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    payload: RefreshTokenRequest,
    service: AuthServiceDep,
) -> None:
    await service.logout(
        refresh_token=payload.refresh_token,
    )
