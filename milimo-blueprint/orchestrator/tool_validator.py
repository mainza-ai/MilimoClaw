#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Validator

Performs static analysis and security validation on generated tool code.
Ensures tools comply with sandbox policies before deployment.

Usage:
    from tool_validator import ToolValidator

    validator = ToolValidator()
    result = validator.validate(code, policy)

    if result.passed:
        print("Tool is safe to deploy")
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("milimo.tool_validator")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Issue severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: Severity
    code: str
    message: str
    line: int = 0
    column: int = 0
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of tool validation."""

    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 0.0
    safe_to_deploy: bool = False


@dataclass
class PolicyConstraints:
    """Policy constraints for tool validation."""

    allow_network: bool = False
    allow_filesystem_write: bool = False
    allow_subprocess: bool = False
    allow_dynamic_exec: bool = False
    allowed_imports: set[str] | None = None
    max_code_length: int = 10000
    max_complexity: int = 20
    require_type_hints: bool = True
    require_docstrings: bool = True


# ---------------------------------------------------------------------------
# Security Rules
# ---------------------------------------------------------------------------


# Modules that are always forbidden
FORBIDDEN_MODULES = {
    # Network access
    "socket",
    "ssl",
    "http.client",
    "urllib.request",
    "urllib.error",
    "urllib.parse",
    "requests",
    "httpx",
    "aiohttp",
    "websocket",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "nntplib",
    "telnetlib",

    # Code execution
    "subprocess",
    "commands",
    "popen2",

    # Serialization exploits
    "pickle",
    "shelve",
    "marshal",
    "dill",
    "cloudpickle",

    # System access
    "ctypes",
    "multiprocessing",
    "threading",

    # File system low-level
    "os",  # Partial - some functions allowed
}

# Functions within 'os' that are forbidden
FORBIDDEN_OS_FUNCTIONS = {
    "system",
    "popen",
    "spawn",
    "exec",
    "fork",
    "kill",
    "chmod",
    "chown",
    "remove",
    "unlink",
    "rmdir",
    "mkdir",
    "makedirs",
    "rename",
    "renames",
    "replace",
}

# Dangerous built-in functions
FORBIDDEN_BUILTINS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",  # Handled separately for write mode
    "input",
    "breakpoint",
}

# Patterns that indicate security issues
DANGEROUS_PATTERNS = [
    (r"__import__\s*\(", "Dynamic import"),
    (r"getattr\s*\([^)]*['\"]__", "Attribute access to dunder methods"),
    (r"setattr\s*\([^)]*['\"]__", "Attribute modification of dunder methods"),
    (r"globals\s*\(\s*\)", "Global namespace access"),
    (r"locals\s*\(\s*\)", "Local namespace access"),
    (r"vars\s*\(\s*\)", "Object __dict__ access"),
    (r"\.__code__", "Code object access"),
    (r"\.__globals__", "Globals access"),
    (r"\.__builtins__", "Builtins access"),
    (r"\.func_globals", "Function globals access"),
    (r"base64\.b64decode", "Potential obfuscated code"),
    (r"codecs\.decode", "Potential obfuscated code"),
    (r"\\x[0-9a-fA-F]{2}", "Hex encoded strings"),
]


# ---------------------------------------------------------------------------
# AST Analyzer
# ---------------------------------------------------------------------------


class ASTAnalyzer(ast.NodeVisitor):
    """
    Analyzes Python AST for security issues.

    Visits all nodes in the AST and checks for:
    - Forbidden imports
    - Forbidden function calls
    - Dangerous patterns
    """

    def __init__(self, constraints: PolicyConstraints):
        self.constraints = constraints
        self.issues: list[ValidationIssue] = []
        self.imports: set[str] = set()
        self.function_calls: list[str] = []
        self._current_function: str = ""

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements."""
        for alias in node.names:
            module = alias.name.split(".")[0]
            self.imports.add(module)

            if module in FORBIDDEN_MODULES:
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.CRITICAL,
                        code="FORBIDDEN_IMPORT",
                        message=f"Forbidden import: {module}",
                        line=node.lineno,
                        column=node.col_offset,
                        suggestion=f"Remove import of {module}",
                    )
                )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from ... import statements."""
        if node.module:
            module = node.module.split(".")[0]
            self.imports.add(module)

            if module in FORBIDDEN_MODULES:
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.CRITICAL,
                        code="FORBIDDEN_IMPORT",
                        message=f"Forbidden import: {module}",
                        line=node.lineno,
                        column=node.col_offset,
                        suggestion=f"Remove import from {module}",
                    )
                )

            # Check for os submodule imports
            if module == "os":
                for alias in node.names:
                    if alias.name in FORBIDDEN_OS_FUNCTIONS:
                        self.issues.append(
                            ValidationIssue(
                                severity=Severity.CRITICAL,
                                code="FORBIDDEN_FUNCTION",
                                message=f"Forbidden os function: {alias.name}",
                                line=node.lineno,
                                column=node.col_offset,
                                suggestion=f"Remove os.{alias.name}",
                            )
                        )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls."""
        call_name = self._get_call_name(node)
        if call_name:
            self.function_calls.append(call_name)

            # Check forbidden builtins
            if call_name in FORBIDDEN_BUILTINS:
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.CRITICAL,
                        code="FORBIDDEN_BUILTIN",
                        message=f"Forbidden builtin: {call_name}",
                        line=node.lineno,
                        column=node.col_offset,
                        suggestion=f"Remove call to {call_name}",
                    )
                )

            # Check os functions
            if call_name.startswith("os.") and call_name.split(".")[1] in FORBIDDEN_OS_FUNCTIONS:
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.CRITICAL,
                        code="FORBIDDEN_FUNCTION",
                        message=f"Forbidden os function: {call_name}",
                        line=node.lineno,
                        column=node.col_offset,
                        suggestion=f"Remove {call_name}",
                    )
                )

            # Check for open with write mode
            if call_name == "open" and not self.constraints.allow_filesystem_write:
                self._check_write_mode(node)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions."""
        self._current_function = node.name

        # Check for type hints
        if self.constraints.require_type_hints:
            if not node.returns and node.name == "run":
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="MISSING_TYPE_HINT",
                        message=f"Function '{node.name}' missing return type hint",
                        line=node.lineno,
                        suggestion="Add return type annotation",
                    )
                )

        # Check for docstring
        if self.constraints.require_docstrings:
            if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str)):
                if node.name == "run":
                    self.issues.append(
                        ValidationIssue(
                            severity=Severity.WARNING,
                            code="MISSING_DOCSTRING",
                            message=f"Function '{node.name}' missing docstring",
                            line=node.lineno,
                            suggestion="Add docstring",
                        )
                    )

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Check for dangerous name references."""
        if node.id == "__import__":
            self.issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="DYNAMIC_IMPORT",
                    message="Dynamic import via __import__",
                    line=node.lineno,
                    column=node.col_offset,
                    suggestion="Remove __import__ usage",
                )
            )
        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str:
        """Get the full name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _check_write_mode(self, node: ast.Call) -> None:
        """Check if open() is called with write mode."""
        # Check keyword arguments
        for keyword in node.keywords:
            if keyword.arg == "mode":
                if isinstance(keyword.value, ast.Constant):
                    mode = keyword.value.value
                    if "w" in mode or "a" in mode:
                        self.issues.append(
                            ValidationIssue(
                                severity=Severity.ERROR,
                                code="FILE_WRITE",
                                message="File write operation not allowed",
                                line=node.lineno,
                                column=node.col_offset,
                                suggestion="Remove file write operation",
                            )
                        )

        # Check positional arguments
        if len(node.args) >= 2:
            if isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
                if "w" in mode or "a" in mode:
                    self.issues.append(
                        ValidationIssue(
                            severity=Severity.ERROR,
                            code="FILE_WRITE",
                            message="File write operation not allowed",
                            line=node.lineno,
                            column=node.col_offset,
                            suggestion="Remove file write operation",
                        )
                    )


# ---------------------------------------------------------------------------
# Complexity Analyzer
# ---------------------------------------------------------------------------


class ComplexityAnalyzer:
    """Analyze code complexity."""

    def compute_complexity(self, code: str) -> int:
        """
        Compute cyclomatic complexity of the code.

        Returns an integer complexity score.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 999

        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # Each decision point adds to complexity
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.With):
                complexity += 1
            elif isinstance(node, ast.Assert):
                complexity += 1
            elif isinstance(node, ast.comprehension):
                complexity += 1
                if node.ifs:
                    complexity += len(node.ifs)
            elif isinstance(node, ast.BoolOp):
                # and/or operators add branches
                complexity += len(node.values) - 1
            elif isinstance(node, ast.IfExp):  # Ternary operator
                complexity += 1

        return complexity


# ---------------------------------------------------------------------------
# Tool Validator
# ---------------------------------------------------------------------------


class ToolValidator:
    """
    Validates generated tool code for security and quality.

    Performs:
    1. Syntax validation
    2. Security analysis (AST-based)
    3. Pattern matching for dangerous code
    4. Complexity analysis
    5. Policy compliance check
    """

    def __init__(self, constraints: PolicyConstraints | None = None):
        self.constraints = constraints or PolicyConstraints()
        self._complexity_analyzer = ComplexityAnalyzer()

    def validate(self, code: str) -> ValidationResult:
        """
        Validate tool code.

        Args:
            code: Python source code to validate

        Returns:
            ValidationResult with pass/fail and issues
        """
        issues: list[ValidationIssue] = []

        # 1. Check code length
        if len(code) > self.constraints.max_code_length:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code="CODE_TOO_LONG",
                    message=f"Code length {len(code)} exceeds maximum {self.constraints.max_code_length}",
                    suggestion="Reduce code size",
                )
            )

        # 2. Parse and validate syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="SYNTAX_ERROR",
                    message=f"Syntax error: {e.msg}",
                    line=e.lineno or 0,
                    suggestion="Fix syntax errors",
                )
            )
            return ValidationResult(passed=False, issues=issues)

        # 3. AST-based security analysis
        analyzer = ASTAnalyzer(self.constraints)
        analyzer.visit(tree)
        issues.extend(analyzer.issues)

        # 4. Pattern-based checks
        pattern_issues = self._check_patterns(code)
        issues.extend(pattern_issues)

        # 5. Complexity check
        complexity = self._complexity_analyzer.compute_complexity(code)
        if complexity > self.constraints.max_complexity:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="HIGH_COMPLEXITY",
                    message=f"Complexity {complexity} exceeds threshold {self.constraints.max_complexity}",
                    suggestion="Reduce code complexity",
                )
            )

        # 6. Check for 'run' function
        has_run = any(
            isinstance(node, ast.FunctionDef) and node.name == "run"
            for node in ast.walk(tree)
        )
        if not has_run:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code="MISSING_RUN",
                    message="Tool must have a 'run' function",
                    suggestion="Add run(input_data) function",
                )
            )

        # Compute score
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)

        # Score: 100 - (critical * 30) - (error * 10) - (warning * 2)
        score = max(0, 100 - (critical_count * 30) - (error_count * 10) - (warning_count * 2))

        # Determine if passed
        passed = critical_count == 0 and error_count == 0
        safe_to_deploy = passed and error_count == 0 and critical_count == 0

        return ValidationResult(
            passed=passed,
            issues=issues,
            score=score,
            safe_to_deploy=safe_to_deploy,
        )

    def _check_patterns(self, code: str) -> list[ValidationIssue]:
        """Check for dangerous patterns using regex."""
        issues: list[ValidationIssue] = []

        for pattern, description in DANGEROUS_PATTERNS:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count("\n") + 1
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="DANGEROUS_PATTERN",
                        message=f"Potential security issue: {description}",
                        line=line_num,
                        suggestion=f"Review and remove: {description}",
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def validate_tool(code: str, constraints: PolicyConstraints | None = None) -> ValidationResult:
    """
    Validate tool code for security and quality.

    Args:
        code: Python source code
        constraints: Optional policy constraints

    Returns:
        ValidationResult
    """
    validator = ToolValidator(constraints)
    return validator.validate(code)
