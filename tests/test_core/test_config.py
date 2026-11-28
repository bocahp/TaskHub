import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def create_settings(secret: str) -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:password@localhost/taskhub",
        jwt_secret_key=secret,
    )


def test_settings_accepts_valid_jwt_secret() -> None:
    secret = secrets.token_urlsafe(32)

    settings = create_settings(secret)

    assert settings.jwt_secret_key.get_secret_value() == secret


def test_settings_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        create_settings("a" * 31)


def test_settings_rejects_empty_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        create_settings("")


def test_settings_rejects_low_variety_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        create_settings("a" * 32)


def test_settings_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        create_settings("replace-with-a-generated-secret-before-running")
