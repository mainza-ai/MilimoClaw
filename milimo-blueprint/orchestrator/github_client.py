# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
GitHub Client using direct REST API via httpx.

Provides all GitHub operations needed by the Build Claw:
- Issue fetching and creation
- PR creation, listing, merging
- File commits via Contents API
- Dependency auditing
- Repository metadata

All operations use the GitHub REST API directly via httpx (same HTTP stack
as the inference client). No external CLI dependency.

Environment variables:
    GITHUB_REPO — Repository in owner/repo format (e.g., "owner/repo")
    GITHUB_TOKEN — Personal access token
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger("milimo.github_client")

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_TIMEOUT = 60


class GitHubClient:
    """
    GitHub client using direct REST API via httpx.

    Usage:
        client = GitHubClient()
        issues = client.get_open_issues()
        pr_num = client.create_pull_request("Fix #123", "Body", "fix/issue-123")
        client.merge_pull_request(pr_num)
    """

    def __init__(
        self,
        repo: str | None = None,
        token: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.repo = repo or os.environ.get("GITHUB_REPO", "")
        self.token = (
            token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        )
        self.timeout = timeout

        if not self.token:
            logger.warning("GITHUB_TOKEN not set — GitHub API calls will fail")
        if not self.repo:
            logger.warning("GITHUB_REPO not set — API calls need owner/repo format")

    # ------------------------------------------------------------------
    # HTTP core
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "milimo-claw/2.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request to the GitHub REST API via httpx."""
        url = f"{GITHUB_API_BASE}{path}"
        try:
            import httpx
        except ImportError:
            return self._request_urllib(method, path, params, json_body)

        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                resp = client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                )
                if resp.status_code in (204, 202):
                    return None
                if resp.status_code >= 400:
                    detail = ""
                    try:
                        detail = resp.json().get("message", resp.text[:200])
                    except Exception:
                        detail = resp.text[:200]
                    logger.warning(
                        "GitHub API %s %s: %s — %s",
                        method,
                        path,
                        resp.status_code,
                        detail,
                    )
                    return None
                text = resp.text
                return json.loads(text) if text else None
        except Exception as exc:
            logger.warning(
                "GitHub API %s %s unavailable (sandbox proxy blocked): %s",
                method,
                path,
                exc,
            )
            return None

    def _request_urllib(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Fallback HTTP via stdlib urllib."""
        import urllib.request

        url = f"{GITHUB_API_BASE}{path}"
        data = json.dumps(json_body).encode("utf-8") if json_body else None
        if params:
            import urllib.parse

            url += "?" + urllib.parse.urlencode(params)

        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8")
                return json.loads(text) if text else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8")[:200] if e.fp else str(e)
            logger.warning("GitHub API %s %s: %s — %s", method, path, e.code, detail)
            return None
        except Exception as exc:
            logger.warning(
                "GitHub API %s %s unavailable (sandbox proxy blocked): %s",
                method,
                path,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Repository context helpers
    # ------------------------------------------------------------------

    def _repo_path(self, endpoint: str) -> str:
        return f"/repos/{self.repo}{endpoint}" if self.repo else endpoint

    # ------------------------------------------------------------------
    # Issue operations
    # ------------------------------------------------------------------

    def get_open_issues(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch open issues with labels, assignees, and body."""
        result = self._request(
            "GET",
            self._repo_path("/issues"),
            params={
                "state": "open",
                "per_page": str(limit),
                "sort": "updated",
                "direction": "desc",
            },
        )
        # Normalise to match gh CLI output format
        return [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "body": i.get("body", ""),
                "labels": i.get("labels", []),
                "assignees": i.get("assignees", []),
                "createdAt": i.get("created_at"),
                "updatedAt": i.get("updated_at"),
                "author": {"login": i.get("user", {}).get("login")},
                "url": i.get("html_url"),
            }
            for i in (result or [])
        ]

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        """Fetch a single issue by number."""
        result = self._request(
            "GET",
            self._repo_path(f"/issues/{issue_number}"),
        )
        return {
            "number": result.get("number"),
            "title": result.get("title"),
            "body": result.get("body", ""),
            "labels": result.get("labels", []),
            "assignees": result.get("assignees", []),
            "comments": result.get("comments", 0),
            "createdAt": result.get("created_at"),
            "updatedAt": result.get("updated_at"),
            "author": {"login": result.get("user", {}).get("login")},
            "url": result.get("html_url"),
        }

    def create_issue(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> int:
        """Create a new GitHub issue. Returns the issue number."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        result = self._request(
            "POST",
            self._repo_path("/issues"),
            json_body=payload,
        )
        return result.get("number", 0)

    def close_issue(self, issue_number: int) -> None:
        """Close an issue."""
        self._request(
            "PATCH",
            self._repo_path(f"/issues/{issue_number}"),
            json_body={"state": "closed"},
        )

    def add_issue_comment(self, issue_number: int, comment: str) -> None:
        """Add a comment to an issue."""
        self._request(
            "POST",
            self._repo_path(f"/issues/{issue_number}/comments"),
            json_body={"body": comment},
        )

    # ------------------------------------------------------------------
    # Branch operations
    # ------------------------------------------------------------------

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """Create a new branch from the specified base branch."""
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name, f"origin/{base_branch}"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "branch", branch_name],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to create branch {branch_name}: {result.stderr.strip()}"
                )

    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch locally and remotely."""
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        self._request(
            "DELETE",
            self._repo_path(f"/git/refs/heads/{branch_name}"),
        )

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def commit_file(
        self,
        branch: str,
        file_path: str,
        content: str,
        message: str | None = None,
    ) -> str:
        """
        Commit a file to a branch using the GitHub Contents API.
        Returns the commit SHA.
        """
        commit_msg = message or f"Update {file_path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        sha = ""
        try:
            existing = self._request(
                "GET",
                self._repo_path(f"/contents/{file_path}"),
                params={"ref": branch},
            )
            if existing and isinstance(existing, dict):
                sha = existing.get("sha", "")
        except RuntimeError:
            pass

        payload: dict[str, str] = {
            "message": commit_msg,
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        result = self._request(
            "PUT",
            self._repo_path(f"/contents/{file_path}"),
            json_body=payload,
        )
        return result.get("commit", {}).get("sha", "") if result else ""

    def get_file_content(self, file_path: str, branch: str = "main") -> str:
        """Get the content of a file from a branch."""
        result = self._request(
            "GET",
            self._repo_path(f"/contents/{file_path}"),
            params={"ref": branch},
        )
        if result and isinstance(result, dict):
            return base64.b64decode(result.get("content", "")).decode("utf-8")
        return ""

    # ------------------------------------------------------------------
    # Pull Request operations
    # ------------------------------------------------------------------

    def create_pull_request(
        self,
        title: str,
        body: str,
        branch: str,
        base: str = "main",
        draft: bool = False,
    ) -> tuple[int, str]:
        """
        Create a pull request.
        Returns tuple of (PR number, PR URL).
        """
        payload = {
            "title": title,
            "body": body,
            "head": branch,
            "base": base,
            "draft": draft,
        }
        result = self._request(
            "POST",
            self._repo_path("/pulls"),
            json_body=payload,
        )
        return result.get("number", 0), result.get("html_url", "")

    def get_open_pull_requests(self) -> list[dict[str, Any]]:
        """List open pull requests."""
        result = self._request(
            "GET",
            self._repo_path("/pulls"),
            params={"state": "open", "per_page": "50", "sort": "updated"},
        )
        return [
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "author": {"login": pr.get("user", {}).get("login")},
                "createdAt": pr.get("created_at"),
                "updatedAt": pr.get("updated_at"),
                "labels": pr.get("labels", []),
                "url": pr.get("html_url"),
                "headRefName": pr.get("head", {}).get("ref"),
                "baseRefName": pr.get("base", {}).get("ref"),
                "mergeable": pr.get("mergeable"),
            }
            for pr in (result or [])
        ]

    def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Get the list of files changed in a PR."""
        result = self._request(
            "GET",
            self._repo_path(f"/pulls/{pr_number}/files"),
        )
        return [
            {"filename": f.get("filename")} for f in (result or []) if f.get("filename")
        ]

    def merge_pull_request(
        self,
        pr_number: int,
        method: str = "squash",
        delete_branch: bool = True,
    ) -> None:
        """Merge a pull request."""
        payload = {
            "merge_method": method,
        }
        self._request(
            "PUT",
            self._repo_path(f"/pulls/{pr_number}/merge"),
            json_body=payload,
        )

    def close_pull_request(self, pr_number: int) -> None:
        """Close a pull request without merging."""
        self._request(
            "PATCH",
            self._repo_path(f"/pulls/{pr_number}"),
            json_body={"state": "closed"},
        )

    def add_pr_review(
        self, pr_number: int, state: str = "APPROVE", body: str = ""
    ) -> None:
        """Add a review to a PR."""
        payload: dict[str, Any] = {
            "event": state,
            "body": body or "",
        }
        self._request(
            "POST",
            self._repo_path(f"/pulls/{pr_number}/reviews"),
            json_body=payload,
        )

    # ------------------------------------------------------------------
    # Dependency auditing
    # ------------------------------------------------------------------

    def get_dependabot_alerts(self) -> list[dict[str, Any]]:
        """Fetch Dependabot security alerts via the API."""
        try:
            return self._request("GET", self._repo_path("/dependabot/alerts")) or []
        except RuntimeError as exc:
            logger.warning("Failed to fetch Dependabot alerts: %s", exc)
            return []

    def get_code_scanning_alerts(self) -> list[dict[str, Any]]:
        """Fetch CodeQL scanning alerts via the API."""
        try:
            return self._request("GET", self._repo_path("/code-scanning/alerts")) or []
        except RuntimeError as exc:
            logger.warning("Failed to fetch CodeQL alerts: %s", exc)
            return []

    def run_dependency_graph(self) -> dict[str, Any]:
        """Get repository dependency graph summary."""
        try:
            return (
                self._request("GET", self._repo_path("/dependency-graph/snapshots"))
                or {}
            )
        except RuntimeError as exc:
            logger.warning("Failed to fetch dependency graph: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_repo_info(self) -> dict[str, Any]:
        """Get repository metadata."""
        return self._request("GET", self._repo_path("")) or {}

    def check_rate_limit(self) -> dict[str, Any]:
        """Check current GitHub API rate limit status."""
        return self._request("GET", "/rate_limit") or {}
