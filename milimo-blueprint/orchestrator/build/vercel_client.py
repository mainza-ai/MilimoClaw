"""
Build Claw — Vercel Client

Real Vercel API client for deployments.
Supports:
- Trigger deployments
- Check deployment status
- Get deployment URL
- Rollback deployments
- List deployments

API Reference: https://vercel.com/docs/rest-api
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("milimo.build.vercel")


@dataclass
class VercelDeployment:
    """Represents a Vercel deployment."""

    deployment_id: str
    url: str
    status: str
    created_at: str
    target: str = "production"
    ready_at: str | None = None
    error: str | None = None


class VercelClient:
    """
    Real Vercel API client.

    Usage:
        client = VercelClient(api_token=os.environ["VERCEL_API_TOKEN"])
        result = client.trigger_deployment(project_id="my-project")
        status = client.get_deployment_status(result["deployment_id"])
    """

    API_BASE = "https://api.vercel.com"

    def __init__(
        self,
        api_token: str | None = None,
        team_id: str | None = None,
        project_id: str | None = None,
        timeout: int = 30,
    ):
        self._api_token = api_token or os.environ.get("VERCEL_API_TOKEN")
        self._team_id = team_id or os.environ.get("VERCEL_TEAM_ID")
        self._project_id = project_id or os.environ.get("VERCEL_PROJECT_ID")
        self._timeout = timeout
        self._last_deployment: VercelDeployment | None = None

        if not self._api_token:
            logger.warning("VercelClient: no API token provided")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        if httpx is None:
            raise RuntimeError("httpx not installed. Run: pip install httpx")

        url = f"{self.API_BASE}{endpoint}"
        if self._team_id:
            url += f"?teamId={self._team_id}"

        resp = httpx.request(
            method,
            url,
            headers=self._headers(),
            timeout=self._timeout,
            **kwargs,
        )

        if resp.status_code >= 400:
            error_msg = resp.text[:200]
            logger.error("VercelClient: API error %d: %s", resp.status_code, error_msg)
            raise RuntimeError(f"Vercel API error {resp.status_code}: {error_msg}")

        return resp.json()

    def health_check(self) -> bool:
        """Check if the Vercel API is accessible with valid credentials."""
        if not self._api_token:
            return False

        try:
            self._request("GET", "/v2/user")
            return True
        except Exception as e:
            logger.warning("VercelClient: health check failed: %s", e)
            return False

    def trigger_deployment(
        self,
        project_id: str | None = None,
        branch: str = "main",
        target: str = "production",
    ) -> dict[str, Any]:
        """
        Trigger a new deployment.

        Args:
            project_id: Vercel project ID (uses default if not provided)
            branch: Git branch to deploy
            target: Deployment target (production, preview, staging)

        Returns:
            Dict with deployment_id and url
        """
        project = project_id or self._project_id
        if not project:
            raise ValueError(
                "project_id required (set VERCEL_PROJECT_ID or pass explicitly)"
            )

        payload = {
            "gitSource": {
                "type": "github",
                "ref": branch,
            },
            "target": target,
        }

        result = self._request(
            "POST",
            f"/v13/deployments",
            json=payload,
        )

        deployment = VercelDeployment(
            deployment_id=result.get("id", ""),
            url=result.get("url", ""),
            status=result.get("readyState", "queued"),
            created_at=result.get("created", ""),
            target=target,
        )

        self._last_deployment = deployment

        logger.info(
            "VercelClient: triggered deployment %s for project %s",
            deployment.deployment_id,
            project,
        )

        return {
            "deployment_id": deployment.deployment_id,
            "url": f"https://{deployment.url}",
            "status": deployment.status,
        }

    def get_deployment_status(self, deployment_id: str | None = None) -> str:
        """
        Get deployment status.

        Returns one of: "queued", "building", "ready", "error", "cancelled"
        """
        dep_id = deployment_id or (
            self._last_deployment.deployment_id if self._last_deployment else None
        )
        if not dep_id:
            logger.warning("VercelClient: no deployment_id to check")
            return "unknown"

        result = self._request("GET", f"/v13/deployments/{dep_id}")
        status = result.get("readyState", "unknown")

        if self._last_deployment:
            self._last_deployment.status = status

        return status

    def get_deployment_url(self, deployment_id: str | None = None) -> str:
        """Get the URL for a deployment."""
        dep_id = deployment_id or (
            self._last_deployment.deployment_id if self._last_deployment else None
        )
        if not dep_id:
            return ""

        result = self._request("GET", f"/v13/deployments/{dep_id}")
        url = result.get("url", "")

        if url and not url.startswith("http"):
            url = f"https://{url}"

        return url

    def wait_for_deployment(
        self,
        deployment_id: str | None = None,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> dict[str, Any]:
        """
        Wait for deployment to complete.

        Args:
            deployment_id: Deployment to wait for
            timeout: Max seconds to wait
            poll_interval: Seconds between status checks

        Returns:
            Dict with final status and url
        """
        dep_id = deployment_id or (
            self._last_deployment.deployment_id if self._last_deployment else None
        )
        if not dep_id:
            return {"status": "error", "error": "no deployment_id"}

        start = time.time()
        while time.time() - start < timeout:
            status = self.get_deployment_status(dep_id)

            if status in ("ready", "error", "cancelled"):
                url = self.get_deployment_url(dep_id) if status == "ready" else ""
                return {
                    "deployment_id": dep_id,
                    "status": status,
                    "url": url,
                }

            time.sleep(poll_interval)

        return {
            "deployment_id": dep_id,
            "status": "timeout",
            "error": f"Deployment did not complete within {timeout}s",
        }

    def rollback(self, deployment_id: str) -> dict[str, Any]:
        """
        Rollback to a previous deployment.

        Creates a new deployment that's a copy of the specified one.
        """
        result = self._request(
            "POST",
            f"/v13/deployments/{deployment_id}/events",
            json={"type": "rollback"},
        )

        logger.info("VercelClient: rolled back to deployment %s", deployment_id)

        return {
            "deployment_id": result.get("id", ""),
            "url": f"https://{result.get('url', '')}",
        }

    def list_deployments(
        self,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent deployments for a project."""
        project = project_id or self._project_id
        if not project:
            return []

        result = self._request(
            "GET",
            f"/v13/deployments?projectId={project}&limit={limit}",
        )

        deployments = []
        for dep in result.get("deployments", []):
            deployments.append(
                {
                    "deployment_id": dep.get("id", ""),
                    "url": f"https://{dep.get('url', '')}",
                    "status": dep.get("readyState", "unknown"),
                    "created_at": dep.get("created", ""),
                    "target": dep.get("target", "production"),
                }
            )

        return deployments
