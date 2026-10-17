"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AccessMatrix runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="ACCESSMATRIX_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "AccessMatrix"
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    data_dir: Path = Field(default_factory=lambda: Path(user_data_dir("AccessMatrix")))


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()
