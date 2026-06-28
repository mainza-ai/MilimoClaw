from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GitHubClientProtocol(ABC):
    @abstractmethod
    def get_open_issues(self, limit: int = 50) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_issue(self, issue_number: int) -> dict[str, Any]: ...

    @abstractmethod
    def create_issue(
        self, title: str, body: str, labels: list[str] | None = None
    ) -> int: ...

    @abstractmethod
    def create_branch(self, branch_name: str, base_branch: str = "main") -> None: ...

    @abstractmethod
    def commit_file(
        self,
        branch_name: str,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> None: ...

    @abstractmethod
    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> tuple[int, str]: ...

    @abstractmethod
    def get_open_pull_requests(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def merge_pull_request(self, pr_number: int) -> None: ...

    @abstractmethod
    def get_dependabot_alerts(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_code_scanning_alerts(self) -> list[dict[str, Any]]: ...
