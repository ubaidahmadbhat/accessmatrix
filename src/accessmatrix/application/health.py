"""Application health information."""

import platform

from accessmatrix import __version__
from accessmatrix.core.settings import get_settings


def build_health() -> dict[str, str]:
    """Build health information shared by all interfaces."""

    settings = get_settings()

    return {
        "status": "ok",
        "application": settings.app_name,
        "version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "data_directory": str(settings.data_dir),
    }
