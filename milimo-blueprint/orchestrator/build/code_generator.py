"""
Build Claw code generator.

Handles:
- Codebase context reading with secret file exclusion
- Implementation generation via inference
- Branch creation and file writing
- Test execution and fix iteration
- Hash-anchored code generation (from OmO)

Enhancement: Hash-anchored edits for edit safety, category-based model selection.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from .approval_handler import BuildApprovalHandler
from .issue_manager import ComplexityScore

logger = logging.getLogger(__name__)

# Secret files to exclude from context
SECRET_FILES = {
    ".env", ".env.local", ".env.production",
    "secrets.json", "credentials.json",
}

# Enhancement: Hash-anchored line tagging (from OmO)
HASH_LINE_SEPARATOR = "#"


@dataclass
class ResolutionResult:
    issue_number: int
    branch_name: str
    files_changed: list[str]
    test_result: str
    tests_passing: int
    tests_failing: int
    attempts: int
    status: str  # "ready_for_pr", "failed_after_max_attempts"
    failure_summary: str | None = None


class CodeGenerator:
    """Generates code implementations for scored issues."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        repo_path: Path,
    ) -> None:
        self._fs = fs
        self._inference = inference_client
        self._github = github_client
        self._approval = approval_handler
        self._log = operational_log
        self._repo_path = repo_path
        self._max_fix_attempts = 3

    # ------------------------------------------------------------------
    # Codebase context reading
    # ------------------------------------------------------------------

    def read_codebase_context(self, issue: dict[str, Any]) -> str:
        """Read relevant files from the repo, excluding secrets."""
        title = issue.get("title", "").lower()
        title_words = [w.strip(".") for w in title.split()]
        # Also split by dots for compound names like "normal.py"
        expanded_words = []
        for w in title_words:
            expanded_words.extend(w.split("."))
        title_words = list(set(w for w in expanded_words if len(w) > 3))

        context_parts: list[str] = []

        if self._repo_path.exists():
            for file_path in self._repo_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.name in SECRET_FILES:
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except (OSError, UnicodeDecodeError):
                    continue

                # Check if any title word appears in content
                if title_words and any(word in content.lower() for word in title_words):
                    rel_path = file_path.relative_to(self._repo_path)
                    context_parts.append(f"--- {rel_path} ---\n{content}")

        if not context_parts:
            return "No relevant context found."

        return "\n\n".join(context_parts)

    # ------------------------------------------------------------------
    # Implementation generation
    # ------------------------------------------------------------------

    def generate_implementation(
        self,
        issue: dict[str, Any],
        context: str,
    ) -> str:
        """Generate code implementation using inference."""
        prompt = f"""Implement the following issue:

Title: {issue.get('title', '')}
Description: {issue.get('body', '')}

Context:
{context}

Provide the implementation with file paths and content."""

        response = self._inference.complete(
            prompt=prompt,
            data_type="source_code_generation",
            temperature=0.1,
        )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="code_generated",
            entity_id=str(issue.get("number", 0)),
            outcome="success",
            details={
                "data_type": "source_code_generation",
                "response_length": len(str(response)),
            },
        ))
        return str(response)

    # ------------------------------------------------------------------
    # Branch management
    # ------------------------------------------------------------------

    def _create_branch_name(self, issue_number: int) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"fix/issue-{issue_number}-{ts}"

    def write_to_branch(
        self,
        branch_name: str,
        implementation: str,
    ) -> list[str]:
        """Parse implementation and write files to branch."""
        files_changed: list[str] = []
        # Simple parsing: look for filepath markers
        lines = implementation.split("\n")
        current_file: str | None = None
        current_content: list[str] = []

        for line in lines:
            if line.startswith("--- filepath:") or line.startswith("--- end ---"):
                if current_file and current_content:
                    files_changed.append(current_file)
                if line.startswith("--- filepath:"):
                    current_file = line.split(":", 1)[1].strip()
                    current_content = []
                elif line.startswith("--- end ---"):
                    current_file = None
                    current_content = []
            elif current_file:
                current_content.append(line)

        # If no file markers found, write as a single file
        if not files_changed:
            current_file = f"fix_{datetime.now(timezone.utc).strftime('%Y%m%d')}.py"
            files_changed.append(current_file)

        self._github.create_branch(branch_name)
        for fname in files_changed:
            self._github.commit_file(
                branch=branch_name,
                file_path=fname,
                content=implementation,
            )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="branch_created",
            entity_id=branch_name,
            outcome="success",
            details={"files_changed": files_changed},
        ))
        return files_changed

    # ------------------------------------------------------------------
    # Test execution
    # ------------------------------------------------------------------

    def run_tests(self) -> tuple[str, int, int]:
        """Run tests and return (status, passing, failing)."""
        import subprocess

        # Try running pytest in the repo directory
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-q", "--json", "--json-file=/tmp/test_results.json"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # Parse pytest-json output for counts
                try:
                    import json
                    json_path = Path("/tmp/test_results.json")
                    if json_path.exists():
                        data = json.loads(json_path.read_text())
                        summary = data.get("summary", {})
                        passing = summary.get("passed", 0)
                        failing = summary.get("failed", 0)
                        return ("passing", passing, failing)
                except Exception:
                    pass
                return ("passing", 0, 0)
            else:
                # Count failures from output
                failing = 0
                for line in result.stdout.split("\n") + result.stderr.split("\n"):
                    if "FAILED" in line or "ERROR" in line:
                        failing += 1
                return ("failing", 0, failing)

        except FileNotFoundError:
            # pytest not installed — try running tests with unittest
            try:
                result = subprocess.run(
                    ["python", "-m", "unittest", "discover", "-s", "test"],
                    cwd=str(self._repo_path),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    return ("passing", 0, 0)
                else:
                    failing = result.stdout.count("FAIL") + result.stdout.count("ERROR")
                    return ("failing", 0, failing)
            except Exception:
                return ("skipped", 0, 0)

        except subprocess.TimeoutExpired:
            logger.warning("Test execution timed out after 300 seconds")
            return ("timeout", 0, 0)

        except Exception as e:
            logger.warning("Test execution failed: %s", e)
            return ("error", 0, 0)

    def analyze_failure_and_fix(
        self,
        issue: dict[str, Any],
        context: str,
        failure_output: str,
    ) -> Any:
        """Analyze test failure and generate fix."""
        prompt = f"""The following test failed:

Issue: {issue.get('title', '')}
Context: {context[:1000]}
Failure: {failure_output[:500]}

Provide a fix."""

        response = self._inference.complete(
            prompt=prompt,
            data_type="source_code_generation",
            temperature=0.1,
        )

        return type("FixResult", (), {"fix_applied": str(response)})()

    # ------------------------------------------------------------------
    # Issue resolution
    # ------------------------------------------------------------------

    def resolve_issue(self, score: ComplexityScore) -> ResolutionResult:
        """Resolve an issue through code generation and testing."""
        issue = {"number": score.issue_number, "title": score.issue_title}
        context = self.read_codebase_context(issue)
        branch_name = self._create_branch_name(score.issue_number)

        for attempt in range(1, self._max_fix_attempts + 1):
            implementation = self.generate_implementation(issue, context)
            files_changed = self.write_to_branch(branch_name, implementation)
            test_status, passing, failing = self.run_tests()

            if test_status == "passing":
                return ResolutionResult(
                    issue_number=score.issue_number,
                    branch_name=branch_name,
                    files_changed=files_changed,
                    test_result="passing",
                    tests_passing=passing,
                    tests_failing=failing,
                    attempts=attempt,
                    status="ready_for_pr",
                )

            if attempt < self._max_fix_attempts:
                fix_result = self.analyze_failure_and_fix(
                    issue, context, f"{failing} tests failing"
                )
                if fix_result.fix_applied:
                    self.write_to_branch(branch_name, fix_result.fix_applied)

        return ResolutionResult(
            issue_number=score.issue_number,
            branch_name=branch_name,
            files_changed=[],
            test_result="failing",
            tests_passing=0,
            tests_failing=failing,
            attempts=self._max_fix_attempts,
            status="failed_after_max_attempts",
            failure_summary=f"Failed after {self._max_fix_attempts} attempts",
        )

    # ------------------------------------------------------------------
    # Enhancement: Hash-anchored code generation (from OmO)
    # ------------------------------------------------------------------

    def hash_anchor_line(self, line_number: int, content: str) -> str:
        """Create a hash-anchored line for edit safety."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:6]
        return f"{line_number}{HASH_LINE_SEPARATOR}{content_hash}| {content}"

    def verify_hash_anchor(self, anchored_line: str, actual_content: str) -> bool:
        """Verify that a hash-anchored line matches actual content."""
        try:
            parts = anchored_line.split("|", 1)
            if len(parts) != 2:
                return False
            hash_part = parts[0].split(HASH_LINE_SEPARATOR, 1)[1]
            actual_hash = hashlib.md5(actual_content.strip().encode()).hexdigest()[:6]
            return hash_part == actual_hash
        except (IndexError, ValueError):
            return False
