"""ASI06 job-description content detection module."""

from .detector import (
    ASI06JobContentDetector,
    DetectionFinding,
    JobContent,
    detect_job_content,
)

__all__ = [
    "ASI06JobContentDetector",
    "DetectionFinding",
    "JobContent",
    "detect_job_content",
]
