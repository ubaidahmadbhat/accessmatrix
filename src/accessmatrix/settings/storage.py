"""Secure persistence for application settings."""

import json
import os
from contextlib import suppress
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import ValidationError

from accessmatrix.settings.models import (
    ApplicationSettings,
)

DEFAULT_MAX_SETTINGS_BYTES = 1024 * 1024

_WRITE_LOCK = Lock()


class SettingsStorageError(RuntimeError):
    """Raised when settings cannot be read or stored safely."""


class ApplicationSettingsRepository:
    """Persist one application-wide settings document."""

    def __init__(
        self,
        storage_root: Path,
        *,
        max_settings_bytes: int = (DEFAULT_MAX_SETTINGS_BYTES),
    ) -> None:
        """Initialize the settings repository."""

        if max_settings_bytes < 1:
            raise ValueError("The settings size limit must be positive.")

        self._directory = storage_root / "settings"

        self._path = self._directory / "application.json"

        self._max_settings_bytes = max_settings_bytes

    def load(
        self,
    ) -> ApplicationSettings:
        """Load stored settings or return secure defaults."""

        if not self._path.is_file():
            return ApplicationSettings()

        try:
            file_size = self._path.stat().st_size

            if file_size > self._max_settings_bytes:
                raise SettingsStorageError(
                    "The application settings exceed the configured size limit."
                )

            raw_content = self._path.read_text(encoding="utf-8")

            parsed_content = json.loads(raw_content)

            return ApplicationSettings.model_validate(parsed_content)

        except SettingsStorageError:
            raise

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise SettingsStorageError(
                "The application settings are corrupted or invalid."
            ) from exc

    def save(
        self,
        settings: ApplicationSettings,
    ) -> ApplicationSettings:
        """Atomically persist application settings."""

        serialized = json.dumps(
            settings.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        encoded_content = serialized.encode("utf-8")

        if len(encoded_content) > self._max_settings_bytes:
            raise SettingsStorageError("The application settings exceed the configured size limit.")

        temporary_path = self._path.with_name(f".{self._path.name}.{uuid4().hex}.tmp")

        try:
            self._directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            with _WRITE_LOCK:
                temporary_path.write_bytes(encoded_content)

                os.replace(
                    temporary_path,
                    self._path,
                )

        except OSError as exc:
            raise SettingsStorageError("The application settings could not be saved.") from exc

        finally:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)

        return settings

    def reset(
        self,
    ) -> ApplicationSettings:
        """Replace stored settings with secure defaults."""

        return self.save(ApplicationSettings())
