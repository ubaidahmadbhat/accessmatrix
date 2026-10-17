"""Controlled HTTP request execution for AccessMatrix."""

from accessmatrix.execution.executor import (
    ControlledRequestExecutor,
    ExecutionResult,
    RequestBodyTooLargeError,
    RequestExecutionError,
    RequestExecutionTimeoutError,
    RequestTransportError,
    SensitiveHeaderError,
    UnsafeMethodConfirmationError,
)
from accessmatrix.execution.rate_limit import (
    RequestRateLimitError,
    SlidingWindowRateLimiter,
)
from accessmatrix.execution.safety import (
    PreparedTarget,
    TargetSafetyError,
    prepare_operation_target,
)

__all__ = [
    "ControlledRequestExecutor",
    "ExecutionResult",
    "PreparedTarget",
    "RequestBodyTooLargeError",
    "RequestExecutionError",
    "RequestExecutionTimeoutError",
    "RequestRateLimitError",
    "RequestTransportError",
    "SensitiveHeaderError",
    "SlidingWindowRateLimiter",
    "TargetSafetyError",
    "UnsafeMethodConfirmationError",
    "prepare_operation_target",
]
