from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    test_database_url: str | None = None
    debug: bool = False

    jwt_secret_key: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        normalized_secret = secret.strip().lower()

        placeholders = {
            "secret",
            "changeme",
            "change-me",
            "your-secret-key",
            "your-jwt-secret-key",
            "replace-with-a-generated-secret-before-running",
        }

        if normalized_secret in placeholders or normalized_secret.startswith(
            ("replace-", "change-me", "your-")
        ):
            raise ValueError("JWT_SECRET_KEY must not be a placeholder value")

        if len(set(secret)) < 12:
            raise ValueError("JWT_SECRET_KEY must contain sufficient character variety")

        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
