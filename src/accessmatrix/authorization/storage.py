"""Local persistence for authorization datasets."""

import json
import os
import re
from contextlib import suppress
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import ValidationError

from accessmatrix.authorization.models import (
    AuthorizationDataset,
)

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

DEFAULT_MAX_DATASET_BYTES = 2 * 1024 * 1024

_WRITE_LOCK = Lock()


class AuthorizationDatasetStorageError(RuntimeError):
    """Raised when a dataset cannot be safely stored or read."""


class AuthorizationDatasetRepository:
    """Store one authorization dataset per project."""

    def __init__(
        self,
        storage_root: Path,
        *,
        max_dataset_bytes: int = (DEFAULT_MAX_DATASET_BYTES),
    ) -> None:
        """Initialize the repository."""

        if max_dataset_bytes < 1:
            raise ValueError("The dataset size limit must be positive.")

        self._directory = storage_root / "authorization-datasets"

        self._max_dataset_bytes = max_dataset_bytes

    def _validate_project_id(
        self,
        project_id: str,
    ) -> None:
        """Reject unsafe project identifiers."""

        if PROJECT_ID_PATTERN.fullmatch(project_id) is None:
            raise AuthorizationDatasetStorageError("The project identifier is invalid.")

    def _dataset_path(
        self,
        project_id: str,
    ) -> Path:
        """Return the dataset path for a project."""

        self._validate_project_id(project_id)

        return self._directory / f"{project_id}.json"

    def load(
        self,
        project_id: str,
    ) -> AuthorizationDataset:
        """Load a project dataset or return an empty dataset."""

        dataset_path = self._dataset_path(project_id)

        if not dataset_path.exists():
            return AuthorizationDataset()

        try:
            file_size = dataset_path.stat().st_size
        except OSError as exc:
            raise AuthorizationDatasetStorageError(
                "The authorization dataset metadata could not be read."
            ) from exc

        if file_size > self._max_dataset_bytes:
            raise AuthorizationDatasetStorageError(
                "The authorization dataset exceeds the configured size limit."
            )

        try:
            raw_content = dataset_path.read_text(encoding="utf-8")

            parsed_content = json.loads(raw_content)

            return AuthorizationDataset.model_validate(parsed_content)

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise AuthorizationDatasetStorageError(
                "The authorization dataset is missing, corrupted, or invalid."
            ) from exc

    def save(
        self,
        project_id: str,
        dataset: AuthorizationDataset,
    ) -> AuthorizationDataset:
        """Atomically save a project dataset."""

        dataset_path = self._dataset_path(project_id)

        serialized = json.dumps(
            dataset.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        encoded_content = serialized.encode("utf-8")

        if len(encoded_content) > self._max_dataset_bytes:
            raise AuthorizationDatasetStorageError(
                "The authorization dataset exceeds the configured size limit."
            )

        temporary_path = dataset_path.with_name(f".{dataset_path.name}.{uuid4().hex}.tmp")

        try:
            self._directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            with _WRITE_LOCK:
                temporary_path.write_bytes(encoded_content)

                os.replace(
                    temporary_path,
                    dataset_path,
                )

        except OSError as exc:
            raise AuthorizationDatasetStorageError(
                "The authorization dataset could not be saved."
            ) from exc

        finally:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)

        return dataset
