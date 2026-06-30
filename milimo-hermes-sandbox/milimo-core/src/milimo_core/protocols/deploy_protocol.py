from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DeployClientProtocol(ABC):
    @abstractmethod
    def trigger_deployment(self, options: dict[str, Any] | None = None) -> str: ...

    @abstractmethod
    def get_deployment_status(self, deployment_id: str | None = None) -> str: ...
