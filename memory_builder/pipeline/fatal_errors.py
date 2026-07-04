from __future__ import annotations

import re
from dataclasses import dataclass, field

CONSECUTIVE_FATAL_THRESHOLD = 5

FATAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("server_disconnected", re.compile(r"server disconnected", re.I)),
    ("connection", re.compile(r"connection (?:reset|refused|aborted|error|closed)", re.I)),
    ("timeout", re.compile(r"(?:read |connect )?timeout", re.I)),
    ("auth", re.compile(r"(?:api[_ ]?key|unauthorized|401|403|permission denied)", re.I)),
    ("quota", re.compile(r"quota (?:exceeded|limit)", re.I)),
]

IMMEDIATE_FATAL_CATEGORIES = frozenset({"auth", "quota"})
TRANSIENT_FATAL_CATEGORIES = frozenset({"server_disconnected", "connection", "timeout"})


class PipelineFatalError(Exception):
    """Raised when consecutive infrastructure errors make further processing pointless."""


class PipelineCancelledError(Exception):
    """Raised when a run stop was requested through the dashboard or API."""


def classify_fatal_error(message: str) -> str | None:
    for name, pattern in FATAL_PATTERNS:
        if pattern.search(message):
            return name
    return None


def is_transient_error(exc: BaseException) -> bool:
    category = classify_fatal_error(str(exc))
    return category in TRANSIENT_FATAL_CATEGORIES


@dataclass
class FatalErrorTracker:
    threshold: int = CONSECUTIVE_FATAL_THRESHOLD
    _consecutive_category: str | None = field(default=None, init=False)
    _consecutive_count: int = field(default=0, init=False)

    def record(self, exc: BaseException) -> bool:
        """Return True when the pipeline should abort."""
        category = classify_fatal_error(str(exc))
        if category is None:
            self.reset()
            return False
        if category in IMMEDIATE_FATAL_CATEGORIES:
            return True
        if category in TRANSIENT_FATAL_CATEGORIES:
            # Transient network/API errors should fail the source, not stop the whole batch.
            self.reset()
            return False
        if category == self._consecutive_category:
            self._consecutive_count += 1
        else:
            self._consecutive_category = category
            self._consecutive_count = 1
        return self._consecutive_count >= self.threshold

    def reset(self) -> None:
        self._consecutive_category = None
        self._consecutive_count = 0
