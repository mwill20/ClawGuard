"""ASI05 unexpected code execution runtime detector."""

from .detector import (
    ASI05CodeExecutionDetector,
    detect_code_execution,
)

__all__ = [
    "ASI05CodeExecutionDetector",
    "detect_code_execution",
]
