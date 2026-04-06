"""
Build Claw — Sentry Client

Real Sentry API client for error monitoring and release management.
Supports:
- List error events
- Get event details
- Create releases
- Upload sourcemaps
- List projects

API Reference: https://docs.sentry.io/api/
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("milimo.build.sentry")


@dataclass
class SentryEvent:
    """Represents a Sentry error event."""

    event_id: str
    title: str
    message: str
    platform: str
    environment: str
    release: str | None
    timestamp: str
    level: str = "error"
    culprit: str = ""
    project: str = ""
    url: str = ""


@dataclass
class SentryRelease:
    """Represents a Sentry release."""

    version: str
    date_created: str
    date_released: str | None = None
    deploy_count: int = 0
    url: str = ""


class SentryClient:
    """
    Real Sentry API client.

    Usage:
        client = SentryClient(auth_token=os.environ["SENTRY_AUTH_TOKEN"])
        events = client.list_events(project="my-project")
        client.create_release(version="1.0.0", project="my-project")
    """

    API_BASE = "https://sentry.io/api/0"

    def __init__(
        self,
        auth_token: str | None = None,
        org_slug: str | None = None,
        project_slug: str | None = None,
        timeout: int = 30,
    ):
        self._auth_token = auth_token or os.environ.get("SENTRY_AUTH_TOKEN")
        self._org_slug = org_slug or os.environ.get("SENTRY_ORG_SLUG")
        self._project_slug = project_slug or os.environ.get("SENTRY_PROJECT_SLUG")
        self._timeout = timeout

        if not self._auth_token:
            logger.warning("SentryClient: no auth token provided")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any] | list[Any]:
        if httpx is None:
            raise RuntimeError("httpx not installed. Run: pip install httpx")

        url = f"{self.API_BASE}{endpoint}"

        resp = httpx.request(
            method,
            url,
            headers=self._headers(),
            timeout=self._timeout,
            **kwargs,
        )

        if resp.status_code >= 400:
            error_msg = resp.text[:200]
            logger.error("SentryClient: API error %d: %s", resp.status_code, error_msg)
            raise RuntimeError(f"Sentry API error {resp.status_code}: {error_msg}")

        return resp.json()

    def health_check(self) -> bool:
        """Check if the Sentry API is accessible with valid credentials."""
        if not self._auth_token:
            return False

        try:
            self._request("GET", "/organizations/")
            return True
        except Exception as e:
            logger.warning("SentryClient: health check failed: %s", e)
            return False

    def get_recent_errors(
        self,
        project: str | None = None,
        hours: int = 24,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get recent errors for error monitoring.

        Args:
            project: Project slug
            hours: Look back period in hours
            limit: Max errors to return

        Returns:
            List of error dicts with event_id, title, timestamp, level
        """
        events = self.list_events(
            project=project,
            query="is:unresolved",
            limit=limit,
        )

        # Filter to recent timeframe
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        recent = []
        for event in events:
            try:
                event_time = datetime.fromisoformat(
                    event.timestamp.replace("Z", "+00:00")
                ).timestamp()
                if event_time >= cutoff:
                    recent.append(
                        {
                            "event_id": event.event_id,
                            "title": event.title,
                            "message": event.message,
                            "timestamp": event.timestamp,
                            "level": event.level,
                            "url": event.url,
                        }
                    )
            except (ValueError, AttributeError):
                pass

        return recent

    def list_events(
        self,
        project: str | None = None,
        environment: str | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> list[SentryEvent]:
        """
        List error events for a project.

        Args:
            project: Project slug (uses default if not provided)
            environment: Filter by environment (production, staging, etc.)
            query: Search query (e.g., "is:unresolved")
            limit: Max events to return

        Returns:
            List of SentryEvent objects
        """
        proj = project or self._project_slug
        if not proj:
            logger.warning("SentryClient: no project specified")
            return []

        org = self._org_slug
        if not org:
            logger.warning("SentryClient: no org specified")
            return []

        params = [f"project={proj}"]
        if environment:
            params.append(f"environment={environment}")
        if query:
            params.append(f"query={query}")

        params.append(f"limit={limit}")

        result = self._request(
            "GET",
            f"/organizations/{org}/issues/?{'&'.join(params)}",
        )

        events = []
        for item in result if isinstance(result, list) else []:
            events.append(
                SentryEvent(
                    event_id=item.get("id", ""),
                    title=item.get("title", ""),
                    message=item.get("metadata", {}).get("value", ""),
                    platform=item.get("platform", ""),
                    environment=item.get("environment", ""),
                    release=item.get("release"),
                    timestamp=item.get("lastSeen", ""),
                    level=item.get("level", "error"),
                    culprit=item.get("culprit", ""),
                    project=proj,
                    url=item.get("permalink", ""),
                )
            )

        return events

    def get_event(
        self, event_id: str, project: str | None = None
    ) -> SentryEvent | None:
        """Get details for a specific event."""
        org = self._org_slug
        if not org:
            return None

        result = self._request(
            "GET",
            f"/organizations/{org}/issues/{event_id}/",
        )

        if not result:
            return None

        return SentryEvent(
            event_id=result.get("id", ""),
            title=result.get("title", ""),
            message=result.get("metadata", {}).get("value", ""),
            platform=result.get("platform", ""),
            environment=result.get("environment", ""),
            release=result.get("release"),
            timestamp=result.get("lastSeen", ""),
            level=result.get("level", "error"),
            culprit=result.get("culprit", ""),
            url=result.get("permalink", ""),
        )

    def create_release(
        self,
        version: str,
        project: str | None = None,
        environment: str = "production",
    ) -> SentryRelease:
        """
        Create a new release.

        Args:
            version: Release version (e.g., "1.0.0" or commit SHA)
            project: Project slug
            environment: Deployment environment

        Returns:
            SentryRelease object
        """
        org = self._org_slug
        proj = project or self._project_slug

        if not org:
            raise ValueError("SENTRY_ORG_SLUG required")
        if not proj:
            raise ValueError("SENTRY_PROJECT_SLUG required")

        payload = {
            "version": version,
            "projects": [proj],
            "refs": [],
        }

        result = self._request(
            "POST",
            f"/organizations/{org}/releases/",
            json=payload,
        )

        release = SentryRelease(
            version=result.get("version", version),
            date_created=result.get("dateCreated", ""),
            date_released=result.get("dateReleased"),
            deploy_count=result.get("deployCount", 0),
            url=result.get("url", ""),
        )

        logger.info(
            "SentryClient: created release %s for project %s",
            release.version,
            proj,
        )

        return release

    def upload_sourcemap(
        self,
        version: str,
        sourcemap_path: str,
        url_prefix: str = "~/",
        project: str | None = None,
    ) -> bool:
        """
        Upload a sourcemap for a release.

        Args:
            version: Release version
            sourcemap_path: Path to sourcemap file
            url_prefix: URL prefix for the sourcemap
            project: Project slug

        Returns:
            True if upload successful
        """
        org = self._org_slug
        proj = project or self._project_slug

        if not org or not proj:
            logger.warning(
                "SentryClient: org and project required for sourcemap upload"
            )
            return False

        try:
            with open(sourcemap_path, "rb") as f:
                sourcemap_data = f.read()

            files = {
                "file": (sourcemap_path, sourcemap_data, "application/json"),
            }

            data = {
                "release": version,
                "dist": hashlib.sha256(sourcemap_data).hexdigest()[:12],
            }

            resp = httpx.post(
                f"{self.API_BASE}/projects/{org}/{proj}/releases/{version}/files/",
                headers={"Authorization": f"Bearer {self._auth_token}"},
                data=data,
                files=files,
                timeout=self._timeout,
            )

            if resp.status_code >= 400:
                logger.error(
                    "SentryClient: sourcemap upload failed: %s",
                    resp.text[:200],
                )
                return False

            logger.info(
                "SentryClient: uploaded sourcemap %s for release %s",
                sourcemap_path,
                version,
            )
            return True

        except Exception as e:
            logger.error("SentryClient: sourcemap upload error: %s", e)
            return False

    def deploy_release(
        self,
        version: str,
        environment: str = "production",
        project: str | None = None,
    ) -> dict[str, Any]:
        """
        Mark a release as deployed.

        Args:
            version: Release version
            environment: Deployment environment
            project: Project slug

        Returns:
            Dict with deployment info
        """
        org = self._org_slug
        if not org:
            raise ValueError("SENTRY_ORG_SLUG required")

        payload = {
            "environment": environment,
        }

        result = self._request(
            "POST",
            f"/organizations/{org}/releases/{version}/deploys/",
            json=payload,
        )

        logger.info(
            "SentryClient: deployed release %s to %s",
            version,
            environment,
        )

        return {
            "version": version,
            "environment": environment,
            "deploy_id": result.get("id", ""),
        }

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects in the organization."""
        org = self._org_slug
        if not org:
            return []

        result = self._request(
            "GET",
            f"/organizations/{org}/projects/",
        )

        projects = []
        for proj in result if isinstance(result, list) else []:
            projects.append(
                {
                    "slug": proj.get("slug", ""),
                    "name": proj.get("name", ""),
                    "platform": proj.get("platform", ""),
                    "status": proj.get("status", ""),
                }
            )

        return projects

    def get_release_stats(
        self,
        version: str,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Get error statistics for a release."""
        org = self._org_slug
        proj = project or self._project_slug

        if not org or not proj:
            return {}

        events = self.list_events(
            project=proj,
            query=f"release:{version}",
            limit=100,
        )

        return {
            "version": version,
            "total_events": len(events),
            "error_count": sum(1 for e in events if e.level == "error"),
            "warning_count": sum(1 for e in events if e.level == "warning"),
            "events": [
                {
                    "event_id": e.event_id,
                    "title": e.title,
                    "timestamp": e.timestamp,
                }
                for e in events[:10]
            ],
        }
