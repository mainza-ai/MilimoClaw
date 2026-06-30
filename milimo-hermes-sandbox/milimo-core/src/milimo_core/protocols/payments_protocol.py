from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaymentsClientProtocol(ABC):
    @abstractmethod
    def create_invoice(self, data: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def send_invoice(self, invoice_id: str) -> bool: ...

    @abstractmethod
    def get_invoice(self, invoice_id: str) -> dict[str, Any] | None: ...
