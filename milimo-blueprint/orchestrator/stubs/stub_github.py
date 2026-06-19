import logging
from typing import Any

from orchestrator.protocols.github_protocol import GitHubClientProtocol

logger = logging.getLogger("milimo.stubs.github")


class StubGitHubClient(GitHubClientProtocol):
    def get_open_issues(self, limit: int = 50) -> list[dict[str, Any]]:
        logger.info("[stub] GitHub not configured — returning empty issue list")
        return []

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        logger.warning(
            f"[stub] GitHub not configured — cannot fetch issue #{issue_number}"
        )
        return {}

    def create_issue(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> int:
        logger.info(f"[stub] GitHub not configured — would create issue: {title}")
        return 0

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        logger.info(
            f"[stub] GitHub not configured — would create branch: {branch_name}"
        )

    def commit_file(
        self, branch_name: str, file_path: str, content: str, commit_message: str
    ) -> None:
        logger.info(
            f"[stub] GitHub not configured — would commit to {branch_name}: {file_path}"
        )

    def create_pull_request(
        self, title: str, body: str, head_branch: str, base_branch: str = "main"
    ) -> tuple[int, str]:
        logger.info(f"[stub] GitHub not configured — would create PR: {title}")
        return 0, ""

    def get_open_pull_requests(self) -> list[dict[str, Any]]:
        logger.info("[stub] GitHub not configured — returning empty PR list")
        return []

    def merge_pull_request(self, pr_number: int) -> None:
        logger.info(f"[stub] GitHub not configured — would merge PR #{pr_number}")

    def get_dependabot_alerts(self) -> list[dict[str, Any]]:
        logger.info("[stub] GitHub not configured — returning empty alert list")
        return []

    def get_code_scanning_alerts(self) -> list[dict[str, Any]]:
        logger.info("[stub] GitHub not configured — returning empty alert list")
        return []
