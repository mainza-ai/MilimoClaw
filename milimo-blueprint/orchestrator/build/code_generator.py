#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Code Generator

Autonomously resolves GitHub issues by generating and testing code.

Resolution flow:
1. Read issue details from GitHub API
2. Read relevant codebase context
3. Create working branch
4. Generate implementation via inference (source_code_generation)
5. Write code to working branch
6. Run test suite
7. If tests fail: analyze failure, attempt fix (max 3 attempts)
8. After 3 failures: escalate to War Room REVIEW
9. If tests pass: hand off to PRManager

IMPORTANT: source code always uses data_type="source_code_generation"
This routes to local NIM in production — never cloud for real code.
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .issue_manager import ComplexityScore

logger = logging.getLogger("milimo.build")

MAX_FIX_ATTEMPTS = 3
TEST_TIMEOUT_SECONDS = 120

FORBIDDEN_PATHS = [
    ".env",
    ".env.local",
    ".env.production",
    "secrets",
    "credentials",
    "credentials.json",
    "api_keys",
    "private",
    ".pem",
    ".key",
]


@dataclass
class ResolutionResult:
    """Result of attempting to resolve an issue."""

    issue_number: int
    branch_name: str
    files_changed: list[str]
    test_result: str
    tests_passing: int
    tests_failing: int
    attempts: int
    status: str
    failure_summary: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_number": self.issue_number,
            "branch_name": self.branch_name,
            "files_changed": self.files_changed,
            "test_result": self.test_result,
            "tests_passing": self.tests_passing,
            "tests_failing": self.tests_failing,
            "attempts": self.attempts,
            "status": self.status,
            "failure_summary": self.failure_summary,
        }


@dataclass
class FixAttempt:
    """Record of a test fix attempt."""

    attempt_number: int
    failure_output: str
    analysis: str
    fix_applied: str
    timestamp: str


class CodeGenerator:
    """
    Autonomously resolves GitHub issues by generating and testing code.

    Resolution flow:
    1. Read issue details from GitHub API
    2. Read relevant codebase context
    3. Create working branch
    4. Generate implementation via inference (source_code_generation)
    5. Write code to working branch
    6. Run test suite
    7. If tests fail: analyze failure, attempt fix (max 3 attempts)
    8. After 3 failures: escalate to War Room REVIEW
    9. If tests pass: hand off to PRManager

    IMPORTANT: source code always uses data_type="source_code_generation"
    This routes to local NIM in production — never cloud for real code.
    """

    MAX_FIX_ATTEMPTS = 3

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        repo_path: Path | None = None,
    ):
        self._fs = fs
        self._inference = inference_client
        self._github = github_client
        self._approval = approval_handler
        self._log = operational_log
        self._repo_path = repo_path or Path("/sandbox/build/repo")

    def resolve_issue(self, issue: ComplexityScore) -> ResolutionResult:
        branch_name = self._create_branch_name(issue.issue_number)
        self._log.append(self._create_log_entry(
            "issue_resolution_started",
            str(issue.issue_number),
            "in_progress",
            {"branch": branch_name, "tier": issue.complexity_tier},
        ))

        codebase_context = self.read_codebase_context({
            "number": issue.issue_number,
            "title": issue.issue_title,
        })

        attempt = 0
        max_attempts = self.MAX_FIX_ATTEMPTS
        test_result = "not_run"
        tests_passing = 0
        tests_failing = 0
        files_changed: list[str] = []
        failure_summary: str | None = None

        while attempt <= max_attempts:
            attempt += 1

            if attempt == 1:
                implementation = self.generate_implementation(
                    {"number": issue.issue_number, "title": issue.issue_title},
                    codebase_context,
                )
            else:
                fix_result = self.analyze_failure_and_fix(
                    branch_name,
                    failure_summary or "",
                    attempt,
                )
                implementation = fix_result.fix_applied

            files_changed = self.write_to_branch(branch_name, implementation, issue.issue_number)

            test_result, tests_passing, tests_failing = self.run_tests()

            if test_result == "passing":
                self._log.append(self._create_log_entry(
                    "issue_tests_passed",
                    str(issue.issue_number),
                    "success",
                    {"attempt": attempt, "tests_passing": tests_passing},
                ))
                return ResolutionResult(
                    issue_number=issue.issue_number,
                    branch_name=branch_name,
                    files_changed=files_changed,
                    test_result="passing",
                    tests_passing=tests_passing,
                    tests_failing=0,
                    attempts=attempt,
                    status="ready_for_pr",
                    failure_summary=None,
                )

            failure_summary = f"{tests_failing} tests failing"

            self._log.append(self._create_log_entry(
                "issue_tests_failed",
                str(issue.issue_number),
                "retrying" if attempt < max_attempts else "escalating",
                {
                    "attempt": attempt,
                    "tests_failing": tests_failing,
                    "tests_passing": tests_passing,
                },
            ))

        self._approval.queue_error_pattern_review(
            error_id=f"issue-{issue.issue_number}-tests",
            error_summary=f"Tests failing after {max_attempts} attempts for issue #{issue.issue_number}",
            occurrence_count=max_attempts,
            is_known_pattern=False,
            auto_patch_available=False,
        )

        return ResolutionResult(
            issue_number=issue.issue_number,
            branch_name=branch_name,
            files_changed=files_changed,
            test_result="failing",
            tests_passing=tests_passing,
            tests_failing=tests_failing,
            attempts=attempt,
            status="failed_after_max_attempts",
            failure_summary=f"Tests failing after {max_attempts} fix attempts",
        )

    def read_codebase_context(self, issue: dict) -> str:
        context_parts: list[str] = []
        repo = self._repo_path

        if not repo.exists():
            return "Repository not available"

        title = issue.get("title", "")
        number = issue.get("number", 0)

        mentioned_files = self._extract_file_paths(title)
        for file_path in mentioned_files:
            full_path = repo / file_path
            if self._is_safe_path(full_path) and full_path.exists():
                try:
                    content = full_path.read_text()
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (truncated)"
                    context_parts.append(f"\n--- {file_path} ---\n{content}")
                except Exception:
                    pass

        for pattern in ["*.py", "src/**/*.py", "lib/**/*.py", "app/**/*.py"]:
            for file_path in list(repo.glob(pattern))[:5]:
                if self._is_safe_path(file_path) and file_path.is_file():
                    try:
                        content = file_path.read_text()
                        relative_path = file_path.relative_to(repo)
                        if len(content) > 1000:
                            content = content[:1000] + "\n... (truncated)"
                        context_parts.append(f"\n--- {relative_path} ---\n{content}")
                    except Exception:
                        pass

        return "\n".join(context_parts) if context_parts else "No context available"

    def generate_implementation(self, issue: dict, codebase_context: str) -> str:
        prompt = f"""You are a senior software engineer. Generate code to resolve this GitHub issue.

Issue #{issue.get('number', 'unknown')}: {issue.get('title', 'Unknown')}

Existing codebase context:
{codebase_context}

Requirements:
1. Write clean, well-documented code
2. Follow existing code patterns and conventions
3. Include appropriate error handling
4. Add tests if applicable

Output the complete implementation with file paths marked as:
--- filepath: path/to/file.py ---
[content]
--- end ---

Generate the implementation:"""

        try:
            response = self._inference.complete(
                prompt=prompt,
                data_type="source_code_generation",
                max_tokens=4000,
            )
            return response
        except Exception as e:
            logger.error("Inference failed: %s", e)
            return ""

    def write_to_branch(
        self,
        branch_name: str,
        implementation: str,
        issue_number: int,
    ) -> list[str]:
        files_changed: list[str] = []

        self._github.create_branch(branch_name)

        sections = implementation.split("--- filepath:")
        for section in sections[1:]:
            lines = section.strip().split("\n")
            if not lines:
                continue

            filepath = lines[0].strip().rstrip("---").strip()
            content_start = 1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "--- end ---":
                    content = "\n".join(lines[content_start:i])
                    break
            else:
                content = "\n".join(lines[1:])

            if filepath and content:
                full_path = self._repo_path / filepath
                if self._is_safe_path(full_path):
                    try:
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content)
                        self._github.commit_file(branch_name, filepath, content)
                        files_changed.append(filepath)
                    except Exception as e:
                        logger.error("Failed to write %s: %s", filepath, e)

        self._log.append(self._create_log_entry(
            "files_written",
            str(issue_number),
            "success",
            {"files": files_changed, "branch": branch_name},
        ))

        return files_changed

    def run_tests(self) -> tuple[str, int, int]:
        repo = self._repo_path
        if not repo.exists():
            return ("no_tests", 0, 0)

        test_commands = [
            ["pytest", "-x", "-q", "--tb=short"],
            ["npm", "test", "--", "--passWithNoTests"],
            ["python", "-m", "pytest", "-x", "-q"],
        ]

        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    timeout=TEST_TIMEOUT_SECONDS,
                )

                output = result.stdout + result.stderr

                if "pytest" in cmd[0] or "pytest" in " ".join(cmd):
                    if result.returncode == 0:
                        passing = self._parse_pytest_passing(output)
                        return ("passing", passing, 0)
                    else:
                        passing, failing = self._parse_pytest_results(output)
                        return ("failing", passing, failing)
                elif "npm" in cmd[0]:
                    if result.returncode == 0:
                        return ("passing", 1, 0)
                    else:
                        return ("failing", 0, 1)

            except subprocess.TimeoutExpired:
                return ("timeout", 0, 0)
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning("Test command failed: %s", e)
                continue

        return ("no_tests", 0, 0)

    def analyze_failure_and_fix(
        self,
        branch_name: str,
        failure_output: str,
        attempt_number: int,
    ) -> FixAttempt:
        prompt = f"""Analyze this test failure and propose a fix.

Test failure output:
{failure_output[:3000]}

Propose:
1. Root cause of the failure
2. Specific code changes needed
3. Expected outcome after fix

Output the fix as:
--- analysis ---
[root cause and fix explanation]
--- fix ---
[complete file content with fix applied, marked with --- filepath: and --- end ---]"""

        try:
            response = self._inference.complete(
                prompt=prompt,
                data_type="code_review",
                max_tokens=3000,
            )

            analysis_lines = []
            fix_content = ""
            in_analysis = False
            in_fix = False

            for line in response.split("\n"):
                if "--- analysis ---" in line:
                    in_analysis = True
                    in_fix = False
                elif "--- fix ---" in line:
                    in_analysis = False
                    in_fix = True
                elif in_analysis:
                    analysis_lines.append(line)
                elif in_fix:
                    fix_content += line + "\n"

            return FixAttempt(
                attempt_number=attempt_number,
                failure_output=failure_output[:500],
                analysis="\n".join(analysis_lines),
                fix_applied=fix_content,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.error("Failure analysis failed: %s", e)
            return FixAttempt(
                attempt_number=attempt_number,
                failure_output=failure_output[:500],
                analysis=f"Analysis failed: {e}",
                fix_applied="",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def _create_branch_name(self, issue_number: int) -> str:
        return f"fix/issue-{issue_number}-{uuid.uuid4().hex[:6]}"

    def _is_safe_path(self, path: Path) -> bool:
        path_str = str(path).lower()
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in path_str:
                return False
        return True

    def _extract_file_paths(self, text: str) -> list[str]:
        import re

        patterns = [
            r"[\w/]+\.py",
            r"[\w/]+\.js",
            r"[\w/]+\.ts",
            r"[\w/]+\.tsx",
            r"[\w/]+\.jsx",
        ]

        paths = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            paths.extend(matches)

        return list(set(paths))[:10]

    def _parse_pytest_passing(self, output: str) -> int:
        import re

        match = re.search(r"(\d+) passed", output)
        if match:
            return int(match.group(1))
        return 1

    def _parse_pytest_results(self, output: str) -> tuple[int, int]:
        import re

        passing_match = re.search(r"(\d+) passed", output)
        failing_match = re.search(r"(\d+) failed", output)

        passing = int(passing_match.group(1)) if passing_match else 0
        failing = int(failing_match.group(1)) if failing_match else 1

        return (passing, failing)

    def _create_log_entry(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        details: dict[str, Any],
    ):
        from .build_init import BuildLogEntry

        return BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )
