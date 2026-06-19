import logging
from typing import Any

from orchestrator.protocols.payments_protocol import PaymentsClientProtocol

logger = logging.getLogger("milimo.stubs.stripe")


class StubStripeClient(PaymentsClientProtocol):
    def create_invoice(self, data: dict[str, Any]) -> dict[str, Any]:
        logger.info(
            f"[stub] Stripe not configured — would create invoice: {data.get('description', 'N/A')}"
        )
        return {"id": "stub_invoice", "status": "stub", "amount_due": 0}

    def send_invoice(self, invoice_id: str) -> bool:
        logger.info(f"[stub] Stripe not configured — would send invoice {invoice_id}")
        return True

    def get_invoice(self, invoice_id: str) -> dict[str, Any] | None:
        logger.info(f"[stub] Stripe not configured — cannot fetch invoice {invoice_id}")
        return None
