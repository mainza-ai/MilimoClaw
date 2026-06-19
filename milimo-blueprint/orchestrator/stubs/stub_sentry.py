import logging
from typing import Any

from orchestrator.protocols.monitoring_protocol import MonitoringClientProtocol

logger = logging.getLogger("milimo.stubs.sentry")


class StubSentryClient(MonitoringClientProtocol):
    def get_recent_errors(self, since_hours: int = 24) -> list[dict[str, Any]]:
        logger.info("[stub] Sentry not configured — returning empty error list")
        return []
