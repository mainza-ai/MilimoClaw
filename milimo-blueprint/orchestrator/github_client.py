# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
GitHub Client wrapping the `gh` CLI.

Provides all GitHub operations needed by the Build Claw:
- Issue fetching and creation
- Branch management
- File commits
- PR creation, listing, and merging
- Dependency auditing via `gh api`

All operations use the GitHub CLI (`gh`) which must be installed and
authenticated in the container environment.

Environment variables:
    GITHUB_REPO — Repository in owner/repo format (e.g., "owner/repo")
    GITHUB_TOKEN — Personal access token (used by gh CLI auth)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger("milimo.github_client")

DEFAULT_TIMEOUT = 60
GH_API_TIMEOUT = 30


class GitHubClient:
    """
    GitHub client wrapping the `gh` CLI.

    Usage:
        client = GitHubClient()
        issues = client.get_open_issues()
        client.create_branch("fix/issue-123")
        client.commit_file("fix/issue-123", "src/main.py", "print('hello')")
        pr_num, pr_url = client.create_pull_request("Fix #123", "Description", "fix/issue-123")
        client.merge_pull_request(pr_num)
    """

    def __init__(
        self,
        repo: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.repo = repo or os.environ.get("GITHUB_REPO", "")
        self.timeout = timeout
        self._ensure_gh_available()

    # ------------------------------------------------------------------
    # Repository context
    # ------------------------------------------------------------------

    def _gh(
        self, args: list[str], timeout: int | None = None
    ) -> subprocess.CompletedProcess:
        """Run a gh CLI command with the repo flag."""
        cmd = ["gh"]
        if self.repo:
            cmd.extend(["--repo", self.repo])
        cmd.extend(args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or self.timeout,
        )

    def _gh_api(
        self, endpoint: str, method: str = "GET", payload: dict | None = None
    ) -> Any:
        """Make a raw GitHub API call via gh CLI."""
        args = ["api", endpoint, "--method", method]
        if payload:
            args.extend(["-f"] + [f"{k}={v}" for k, v in payload.items()])
        result = self._gh(args, timeout=GH_API_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(f"gh api {endpoint} failed: {result.stderr.strip()}")
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None

    def _ensure_gh_available(self) -> None:
        """Verify gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("gh CLI returned non-zero exit code")
        except FileNotFoundError:
            raise RuntimeError(
                "gh CLI not found. Install with: brew install gh (macOS) or "
                "sudo apt install gh (Ubuntu). See https://cli.github.com/"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("gh CLI version check timed out")

        # Check authentication
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("gh CLI is not authenticated: %s", result.stderr.strip())
        except Exception:
            pass  # Non-fatal — may work with token env var

    # ------------------------------------------------------------------
    # Issue operations
    # ------------------------------------------------------------------

    def get_open_issues(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch open issues with labels, assignees, and body."""
        result = self._gh(
            [
                "issue",
                "list",
                "--state",
                "open",
                "--limit",
                str(limit),
                "--json",
                "number,title,body,labels,assignees,createdAt,updatedAt,author,url",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch issues: {result.stderr.strip()}")
        return json.loads(result.stdout) if result.stdout.strip() else []

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        """Fetch a single issue by number."""
        result = self._gh(
            [
                "issue",
                "view",
                str(issue_number),
                "--json",
                "number,title,body,labels,assignees,comments,createdAt,updatedAt,author,url",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to fetch issue #{issue_number}: {result.stderr.strip()}"
            )
        return json.loads(result.stdout)

    def create_issue(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> int:
        """Create a new GitHub issue. Returns the issue number."""
        args = ["issue", "create", "--title", title, "--body", body]
        if labels:
            args.extend(["--label", ",".join(labels)])
        result = self._gh(args)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create issue: {result.stderr.strip()}")
        # Parse issue number from URL in stdout
        output = result.stdout.strip()
        # gh outputs the URL, extract number from it
        if "issues/" in output:
            return int(output.split("issues/")[-1].rstrip("/"))
        # Fallback: try parsing from JSON if --json was used
        return 0

    def close_issue(self, issue_number: int) -> None:
        """Close an issue."""
        result = self._gh(["issue", "close", str(issue_number)])
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to close issue #{issue_number}: {result.stderr.strip()}"
            )

    def add_issue_comment(self, issue_number: int, comment: str) -> None:
        """Add a comment to an issue."""
        result = self._gh(["issue", "comment", str(issue_number), "--body", comment])
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to comment on issue #{issue_number}: {result.stderr.strip()}"
            )

    # ------------------------------------------------------------------
    # Branch operations
    # ------------------------------------------------------------------

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """Create a new branch from the specified base branch."""
        # Use git directly for local branch creation
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name, f"origin/{base_branch}"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            # Fallback: create branch via git push
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
        self._gh(["branch", "delete", branch_name, "--yes"])

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
        Commit a file to a branch using the GitHub API.

        Uses `gh api` to PUT the file content via the Contents API.
        Returns the commit SHA.
        """
        import base64

        commit_msg = message or f"Update {file_path}"
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # First, get the current SHA if file exists
        sha = ""
        try:
            existing = self._gh_api(
                f"/repos/{self.repo}/contents/{file_path}",
                payload={"ref": branch},
            )
            if existing and isinstance(existing, dict):
                sha = existing.get("sha", "")
        except Exception:
            pass  # File doesn't exist yet — new file

        payload: dict[str, str] = {
            "message": commit_msg,
            "content": encoded_content,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        result = self._gh_api(
            f"/repos/{self.repo}/contents/{file_path}",
            method="PUT",
            payload=payload,
        )

        if result and isinstance(result, dict):
            commit_sha = result.get("commit", {}).get("sha", "")
            return commit_sha
        return ""

    def get_file_content(self, file_path: str, branch: str = "main") -> str:
        """Get the content of a file from a branch."""
        result = self._gh_api(
            f"/repos/{self.repo}/contents/{file_path}",
            payload={"ref": branch},
        )
        if result and isinstance(result, dict):
            import base64

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

        Returns:
            Tuple of (PR number, PR URL).
        """
        args = [
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--head",
            branch,
            "--base",
            base,
        ]
        if draft:
            args.append("--draft")

        result = self._gh(args)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create PR: {result.stderr.strip()}")

        # Parse PR number and URL from output
        output = result.stdout.strip()
        pr_number = 0
        pr_url = output
        if "pull/" in output:
            pr_url = output
            try:
                pr_number = int(output.split("pull/")[-1].split("/")[0])
            except (ValueError, IndexError):
                pass
        return pr_number, pr_url

    def get_open_pull_requests(self) -> list[dict[str, Any]]:
        """List open pull requests."""
        result = self._gh(
            [
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,title,author,createdAt,updatedAt,labels,url,headRefName,baseRefName,files,mergeable",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to list PRs: {result.stderr.strip()}")
        return json.loads(result.stdout) if result.stdout.strip() else []

    def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Get the list of files changed in a PR."""
        result = self._gh(
            [
                "pr",
                "diff",
                str(pr_number),
                "--name-only",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get PR files: {result.stderr.strip()}")
        return [
            {"filename": line} for line in result.stdout.strip().split("\n") if line
        ]

    def merge_pull_request(
        self,
        pr_number: int,
        method: str = "squash",
        delete_branch: bool = True,
    ) -> None:
        """Merge a pull request."""
        args = ["pr", "merge", str(pr_number)]
        if method == "squash":
            args.append("--squash")
        elif method == "rebase":
            args.append("--rebase")
        else:
            args.append("--merge")
        if delete_branch:
            args.append("--delete-branch")

        result = self._gh(args)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to merge PR #{pr_number}: {result.stderr.strip()}"
            )

    def close_pull_request(self, pr_number: int) -> None:
        """Close a pull request without merging."""
        result = self._gh(["pr", "close", str(pr_number)])
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to close PR #{pr_number}: {result.stderr.strip()}"
            )

    def add_pr_review(
        self, pr_number: int, state: str = "APPROVE", body: str = ""
    ) -> None:
        """Add a review to a PR."""
        args = ["pr", "review", str(pr_number), f"--{state.lower()}"]
        if body:
            args.extend(["--body", body])
        result = self._gh(args)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to review PR #{pr_number}: {result.stderr.strip()}"
            )

    # ------------------------------------------------------------------
    # Dependency auditing
    # ------------------------------------------------------------------

    def get_dependabot_alerts(self) -> list[dict[str, Any]]:
        """Fetch Dependabot security alerts via the API."""
        try:
            return (
                self._gh_api(
                    f"/repos/{self.repo}/dependabot/alerts",
                )
                or []
            )
        except Exception as exc:
            logger.warning("Failed to fetch Dependabot alerts: %s", exc)
            return []

    def get_code_scanning_alerts(self) -> list[dict[str, Any]]:
        """Fetch CodeQL scanning alerts via the API."""
        try:
            return (
                self._gh_api(
                    f"/repos/{self.repo}/code-scanning/alerts",
                )
                or []
            )
        except Exception as exc:
            logger.warning("Failed to fetch CodeQL alerts: %s", exc)
            return []

    def run_dependency_graph(self) -> dict[str, Any]:
        """Get repository dependency graph summary."""
        try:
            return (
                self._gh_api(
                    f"/repos/{self.repo}/dependency-graph/snapshots",
                )
                or {}
            )
        except Exception as exc:
            logger.warning("Failed to fetch dependency graph: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_repo_info(self) -> dict[str, Any]:
        """Get repository metadata."""
        return self._gh_api(f"/repos/{self.repo}") or {}

    def check_rate_limit(self) -> dict[str, Any]:
        """Check current GitHub API rate limit status."""
        return self._gh_api("/rate_limit") or {}
