"""Runtime construction of settings-aware request executors."""

from pathlib import Path
from threading import Lock

from accessmatrix.execution.executor import ControlledRequestExecutor
from accessmatrix.execution.policy import SettingsAwareRequestExecutor
from accessmatrix.execution.protocols import RequestExecutor
from accessmatrix.execution.rate_limit import SlidingWindowRateLimiter
from accessmatrix.security.credentials import CredentialResolver
from accessmatrix.settings.models import ApplicationSettings
from accessmatrix.settings.storage import ApplicationSettingsRepository

_RUNTIME_LOCK = Lock()

_CACHED_SIGNATURE: str | None = None
_CACHED_EXECUTOR: RequestExecutor | None = None


def settings_signature(
    storage_root: Path,
) -> tuple[str, ApplicationSettings]:
    """Load settings and return a stable cache signature."""

    settings = ApplicationSettingsRepository(storage_root).load()

    return (
        settings.model_dump_json(),
        settings,
    )


def build_runtime_request_executor(
    storage_root: Path,
) -> RequestExecutor:
    """Return an executor matching the latest application settings."""

    global _CACHED_EXECUTOR
    global _CACHED_SIGNATURE

    signature, settings = settings_signature(storage_root)

    with _RUNTIME_LOCK:
        if _CACHED_EXECUTOR is not None and signature == _CACHED_SIGNATURE:
            return _CACHED_EXECUTOR

        rate_limiter = SlidingWindowRateLimiter(
            limit=(settings.execution.rate_limit_requests),
            window_seconds=(settings.execution.rate_limit_window_seconds),
        )

        base_executor = ControlledRequestExecutor(
            resolver=CredentialResolver(),
            rate_limiter=rate_limiter,
        )

        runtime_executor = SettingsAwareRequestExecutor(
            inner=base_executor,
            settings=settings,
            storage_root=storage_root,
        )

        _CACHED_SIGNATURE = signature
        _CACHED_EXECUTOR = runtime_executor

        return runtime_executor


def clear_runtime_executor_cache() -> None:
    """Clear the cached runtime request executor."""

    global _CACHED_EXECUTOR
    global _CACHED_SIGNATURE

    with _RUNTIME_LOCK:
        _CACHED_EXECUTOR = None
        _CACHED_SIGNATURE = None
