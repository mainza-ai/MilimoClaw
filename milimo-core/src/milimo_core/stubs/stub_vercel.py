import logging
from typing import Any

from milimo_core.protocols.deploy_protocol import DeployClientProtocol

logger = logging.getLogger("milimo.stubs.vercel")


class StubVercelClient(DeployClientProtocol):
    def trigger_deployment(self, options: dict[str, Any] | None = None) -> str:
        logger.info("[stub] Vercel not configured — deployment skipped")
        return ""

    def get_deployment_status(self, deployment_id: str | None = None) -> str:
        logger.info("[stub] Vercel not configured — returning 'unknown'")
        return "unknown"
