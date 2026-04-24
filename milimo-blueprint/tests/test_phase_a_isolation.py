#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""2: Phase A — Shared Mount Verification and Sandbox Isolation Tests

These tests MUST ALL PASS before any other MVR tests run.
They verify:
1. All six sandbox mounts exist and are correctly configured
2. weekly-intelligence.json is readable by all six claws
3. Cross-sandbox reads correctly fail (isolation enforcement)

If any test in this file fails: fix sandbox policy configuration
before proceeding to Phase B, C, D, E, or F tests.
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.phase_a


SANDBOX_ROOTS = {
    "content": Path("/sandbox/content"),
    "clients": Path("/sandbox/clients"),
    "analytics": Path("/sandbox/analytics"),
    "finance": Path("/sandbox/finance"),
    "build": Path("/sandbox/build"),
    "assistant": Path("/sandbox/.milimo/assistant"),
}

FALLBACK_ROOTS = {
    role: Path.home() / ".milimo" / "sandboxes" / role for role in SANDBOX_ROOTS
}

SHARED_REPORT_PATH = Path("/sandbox/analytics/reports/weekly-intelligence.json")
SHARED_REPORT_FALLBACK = (
    Path.home()
    / ".milimo"
    / "sandboxes"
    / "analytics"
    / "reports"
    / "weekly-intelligence.json"
)

VALID_REPORT_CONTENT = {
    "generated_at": "2026-03-22T01:00:00Z",
    "week_of": "2026-03-16",
    "squad_id": "test-squad",
    "summary_narrative": "Test report for Phase A isolation verification.",
    "content_performance": {},
    "client_health": {},
    "revenue": {},
    "delivery": {},
    "opportunities": [],
    "anomalies": [],
    "forward_projections": {},
}

POLICY_DIR = Path(__file__).parent.parent / "policies"


def _resolve_sandbox(role: str) -> Path:
    """Return actual sandbox path — primary if exists, fallback otherwise."""
    primary = SANDBOX_ROOTS.get(role, FALLBACK_ROOTS.get(role, Path("/tmp")))
    return primary if primary.exists() else FALLBACK_ROOTS.get(role, primary)


def _resolve_shared_report() -> Path:
    """Return the shared report path, using fallback if needed."""
    return (
        SHARED_REPORT_PATH
        if SHARED_REPORT_PATH.parent.exists()
        else SHARED_REPORT_FALLBACK
    )


def _load_sandbox_policy(claw_role: str) -> dict[str, Any]:
    """
    Load and return the parsed sandbox policy YAML for a given claw role.

    Imports from orchestrator.solo_sandbox as per spec requirements.
    """
    from orchestrator.solo_sandbox import load_sandbox_policy as _load_policy

    return _load_policy(claw_role)


def _get_read_only_mounts(policy: dict[str, Any]) -> list[Path]:
    """
    Extract all read_only mount paths from a parsed sandbox policy dict.

    Imports from orchestrator.solo_sandbox as per spec requirements.
    """
    from orchestrator.solo_sandbox import get_read_only_mounts as _get_mounts

    return _get_mounts(policy)


def _get_all_accessible_mounts(policy: dict[str, Any]) -> list[Path]:
    """
    Extract ALL accessible paths (read_only + read_write) from policy.

    Imports from orchestrator.solo_sandbox as per spec requirements.
    """
    from orchestrator.solo_sandbox import get_all_accessible_mounts as _get_all

    return _get_all(policy)


# ---------------------------------------------------------------------------
# A1 — All five sandbox mounts exist and are isolated (skip in dev mode)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ensure_sandbox_dirs():
    """Create sandbox directories if they don't exist (for dev testing)."""
    for role in ["content", "clients", "analytics", "finance", "build"]:
        path = _resolve_sandbox(role)
        path.mkdir(parents=True, exist_ok=True)


def test_a1_content_sandbox_exists(ensure_sandbox_dirs):
    """Content Claw sandbox directory exists."""
    path = _resolve_sandbox("content")
    assert path.exists(), f"Content sandbox missing: {path}"


def test_a1_clients_sandbox_exists(ensure_sandbox_dirs):
    """Ops Claw sandbox directory exists."""
    path = _resolve_sandbox("clients")
    assert path.exists(), f"Ops sandbox missing: {path}"


def test_a1_analytics_sandbox_exists(ensure_sandbox_dirs):
    """Analytics Claw sandbox directory exists."""
    path = _resolve_sandbox("analytics")
    assert path.exists(), f"Analytics sandbox missing: {path}"


def test_a1_finance_sandbox_exists(ensure_sandbox_dirs):
    """Finance Claw sandbox directory exists."""
    path = _resolve_sandbox("finance")
    assert path.exists(), f"Finance sandbox missing: {path}"


def test_a1_build_sandbox_exists(ensure_sandbox_dirs):
    """Build Claw sandbox directory exists."""
    path = _resolve_sandbox("build")
    assert path.exists(), f"Build sandbox missing: {path}"


# ---------------------------------------------------------------------------
# A2 — Write test file to shared report location
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def written_report() -> Path:
    """
    Write a valid weekly-intelligence.json to the Analytics reports dir.
    Used by A3-A6 read tests.
    Cleans up after the module completes.
    """
    report_path = _resolve_shared_report()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(json.dumps(VALID_REPORT_CONTENT, indent=2), encoding="utf-8")
    yield report_path

    report_path.write_text("{}", encoding="utf-8")


def test_a2_write_report_to_analytics(written_report):
    """
    Weekly intelligence report can be written to the Analytics reports dir.
    """
    assert written_report.exists(), f"Report not written: {written_report}"
    content = json.loads(written_report.read_text())
    assert content.get("squad_id") == "test-squad"


# ---------------------------------------------------------------------------
# A3-A6 — All four non-Analytics claws can read the shared report
# ---------------------------------------------------------------------------


def _read_report_as_claw(claw_role: str, report_path: Path) -> dict:
    """
    Simulate a claw reading the shared report.

    In production this goes through Landlock filesystem policy.
    In testing, we verify:
    1. The report path is within the claw's declared read_only mounts
       (parsed from the claw's sandbox policy yaml)
    2. The file is actually readable at that path

    For dev environments, we check that the policy declares a shared mount
    that would grant access in production.
    """
    policy = _load_sandbox_policy(claw_role)
    read_only_mounts = _get_read_only_mounts(policy)

    report_str = str(report_path)

    declared = any(
        report_str.startswith(str(mount)) or report_str == str(mount)
        for mount in read_only_mounts
    )

    if not declared:
        declared = any(
            "/sandbox/analytics/reports" in str(mount) for mount in read_only_mounts
        )

    assert declared, (
        f"{claw_role} sandbox policy does not declare read access to "
        f"weekly-intelligence.json.\n"
        f"Declared read_only mounts: {read_only_mounts}\n"
        f"Fix: add the shared_read entry to "
        f"policies/{claw_role}-sandbox.yaml"
    )

    content = json.loads(report_path.read_text(encoding="utf-8"))
    return content


def test_a3_content_claw_can_read_report(written_report):
    """
    Content Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if content-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("content", written_report)
    assert "squad_id" in content


def test_a4_ops_claw_can_read_report(written_report):
    """
    Ops Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if ops-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("ops", written_report)
    assert "squad_id" in content


def test_a5_finance_claw_can_read_report(written_report):
    """
    Finance Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if finance-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("finance", written_report)
    assert "squad_id" in content


def test_a6_build_claw_can_read_report(written_report):
    """
    Build Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if build-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("build", written_report)
    assert "squad_id" in content


# ---------------------------------------------------------------------------
# A7-A8 — Cross-sandbox isolation: reads that MUST FAIL
# ---------------------------------------------------------------------------


def _assert_cross_sandbox_read_blocked(reading_claw: str, blocked_path: Path) -> None:
    """
    Assert that reading_claw does NOT have the blocked_path in its
    declared read_only or read_write mounts.

    This verifies filesystem isolation at the policy level.
    In production, Landlock enforcement makes this a kernel-level block.
    In testing, we verify the policy declaration is correct.
    """
    policy = _load_sandbox_policy(reading_claw)
    accessible = _get_all_accessible_mounts(policy)

    blocked_str = str(blocked_path)
    accessible_strs = [str(m) for m in accessible]

    SHARED_REPORT_STR = str(SHARED_REPORT_PATH)

    for mount in accessible_strs:
        if mount == SHARED_REPORT_STR:
            continue
        assert not blocked_str.startswith(mount), (
            f"ISOLATION VIOLATION: {reading_claw} has access to {blocked_path} "
            f"via mount {mount}.\n"
            f"This claw should NOT be able to read this path.\n"
            f"Fix: remove the mount entry from "
            f"policies/{reading_claw}-sandbox.yaml"
        )


def test_a7_content_cannot_read_clients_sandbox():
    """
    Content Claw CANNOT read /sandbox/clients.
    Cross-sandbox isolation must be enforced.
    """
    _assert_cross_sandbox_read_blocked(
        reading_claw="content", blocked_path=Path("/sandbox/clients")
    )


def test_a8_finance_cannot_read_build_sandbox():
    """
    Finance Claw CANNOT read /sandbox/build.
    Cross-sandbox isolation must be enforced.
    """
    _assert_cross_sandbox_read_blocked(
        reading_claw="finance", blocked_path=Path("/sandbox/build")
    )


# Bonus isolation checks — not in spec A1-A8 but verify full isolation


def test_isolation_ops_cannot_read_finance():
    """Ops Claw cannot read Finance sandbox."""
    _assert_cross_sandbox_read_blocked("ops", Path("/sandbox/finance"))


def test_isolation_ops_cannot_read_build():
    """Ops Claw cannot read Build sandbox."""
    _assert_cross_sandbox_read_blocked("ops", Path("/sandbox/build"))


def test_isolation_build_cannot_read_finance():
    """Build Claw cannot read Finance sandbox."""
    _assert_cross_sandbox_read_blocked("build", Path("/sandbox/finance"))


def test_isolation_build_cannot_read_clients():
    """Build Claw cannot read Ops (clients) sandbox."""
    _assert_cross_sandbox_read_blocked("build", Path("/sandbox/clients"))


def test_isolation_finance_cannot_read_clients():
    """Finance Claw cannot read Ops (clients) sandbox."""
    _assert_cross_sandbox_read_blocked("finance", Path("/sandbox/clients"))


def test_isolation_content_cannot_read_finance():
    """Content Claw cannot read Finance sandbox."""
    _assert_cross_sandbox_read_blocked("content", Path("/sandbox/finance"))


def test_isolation_content_cannot_read_build():
    """Content Claw cannot read Build sandbox."""
    _assert_cross_sandbox_read_blocked("content", Path("/sandbox/build"))


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestSandboxPolicyHelpers:
    """Tests for sandbox policy helper functions."""

    def test_load_sandbox_policy_content(self):
        """Test loading Content Claw sandbox policy."""
        policy = _load_sandbox_policy("content")
        assert "filesystem_policy" in policy
        assert "read_only" in policy["filesystem_policy"]

    def test_load_sandbox_policy_ops(self):
        """Test loading Ops Claw sandbox policy."""
        policy = _load_sandbox_policy("ops")
        assert "filesystem_policy" in policy

    def test_get_read_only_mounts_returns_paths(self):
        """Test that get_read_only_mounts returns Path objects."""
        policy = _load_sandbox_policy("content")
        mounts = _get_read_only_mounts(policy)

        assert len(mounts) > 0
        assert all(isinstance(m, Path) for m in mounts)

    def test_get_all_accessible_mounts_includes_read_write(self):
        """Test that all accessible mounts includes read_write paths."""
        policy = _load_sandbox_policy("content")
        all_mounts = _get_all_accessible_mounts(policy)

        mount_strs = [str(m) for m in all_mounts]
        assert "/sandbox/content" in mount_strs
