"""Local application storage paths."""

from pathlib import Path

from accessmatrix.core.settings import get_settings


def get_storage_root() -> Path:
    """Return the AccessMatrix data directory."""

    storage_root = get_settings().data_dir
    storage_root.mkdir(parents=True, exist_ok=True)

    return storage_root
