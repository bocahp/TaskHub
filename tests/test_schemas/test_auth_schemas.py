
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import UserRole
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, RegisterRequest
from app.schemas.user import (
    ChangePasswordRequest,
    UserProfileUpdate,
    UserResponse,
)


def test_register_normalizes_email_and_name_preserves_password() -> None:
    payload = RegisterRequest(
        email="  Test@Example.com ",
        full_name="  Test User  ",
        password="  TestPassword123!  ",
    )

    assert payload.email == "test@example.com"
    assert payload.full_name == "Test User"
    assert payload.password == "  TestPassword123!  "


def test_register_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="invalid-email",
            full_name="Test User",
            password="TestPassword123!",
        )


def test_register_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="test@example.com",
            full_name="Test User",
            password="short",
        )


def test_refresh_token_strips_whitespace() -> None:
    payload = RefreshTokenRequest(
        refresh_token=" token-value ",
    )

    assert payload.refresh_token == "token-value"


def test_user_profile_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        UserProfileUpdate(full_name="   ")


def test_change_password_preserves_whitespace() -> None:
    payload = ChangePasswordRequest(
        current_password=" old password ",
        new_password=" new password 123 ",
    )

    assert payload.current_password == " old password "
    assert payload.new_password == " new password 123 "


def test_user_response_does_not_expose_password_hash() -> None:
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password="secret-hash",
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )

    response = UserResponse.model_validate(user)

    assert response.email == user.email
    assert response.role == UserRole.MEMBER
    assert not hasattr(response, "hashed_password")
