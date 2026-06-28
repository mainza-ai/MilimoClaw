from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MonitoringClientProtocol(ABC):
    @abstractmethod
    def get_recent_errors(self, since_hours: int = 24) -> list[dict[str, Any]]: ...
