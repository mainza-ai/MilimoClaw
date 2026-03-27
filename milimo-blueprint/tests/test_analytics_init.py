#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Analytics Filesystem Initialization.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
    InitResult,
    ValidationResult,
    BASE,
    REQUIRED_DIRS,
    REQUIRED_FILES,
)


@pytest.fixture
def temp_sandbox() -> Path:
    """Create a temporary sandbox directory for testing."""
    sandbox = Path(tempfile.mkdtemp(prefix="analytics_init_test_"))
    yield sandbox
    shutil.rmtree(sandbox, ignore_errors=True)


@pytest.fixture
def fs(temp_sandbox: Path) -> AnalyticsFilesystemInit:
    """Create filesystem init with temp sandbox."""
    return AnalyticsFilesystemInit(temp_sandbox)


class TestAnalyticsFilesystemInit:
    """Tests for AnalyticsFilesystemInit class."""

    def test_initialize_creates_all_directories(self, fs: AnalyticsFilesystemInit):
        """Test that initialize creates all required directories."""
        result = fs.initialize()

        assert result.success
        assert len(result.created_dirs) > 0 or len(result.already_existed) > 0

        for rel_dir in REQUIRED_DIRS:
            dir_path = fs.base / rel_dir
            assert dir_path.is_dir(), f"Directory not created: {rel_dir}"

    def test_initialize_creates_all_files(self, fs: AnalyticsFilesystemInit):
        """Test that initialize creates all required files."""
        result = fs.initialize()

        assert result.success

        for rel_file in REQUIRED_FILES:
            file_path = fs.base / rel_file
            assert file_path.is_file(), f"File not created: {rel_file}"

    def test_initialize_is_idempotent(self, fs: AnalyticsFilesystemInit):
        """Test that calling initialize multiple times doesn't fail."""
        result1 = fs.initialize()
        result2 = fs.initialize()

        assert result1.success
        assert result2.success

        assert len(result2.created_dirs) == 0
        assert len(result2.created_files) == 0
        assert len(result2.already_existed) > 0

    def test_initialize_creates_valid_json_files(self, fs: AnalyticsFilesystemInit):
        """Test that JSON files are valid."""
        fs.initialize()

        for rel_file in REQUIRED_FILES:
            if rel_file.endswith(".json"):
                file_path = fs.base / rel_file
                content = file_path.read_text()
                try:
                    data = json.loads(content)
                    assert isinstance(data, dict)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON in {rel_file}")

    def test_validate_returns_valid_when_structure_exists(self, fs: AnalyticsFilesystemInit):
        """Test that validate passes when structure is correct."""
        fs.initialize()
        result = fs.validate()

        assert result.valid
        assert len(result.missing_dirs) == 0
        assert len(result.missing_files) == 0

    def test_validate_returns_invalid_when_directories_missing(self, fs: AnalyticsFilesystemInit):
        """Test that validate fails when directories are missing."""
        result = fs.validate()

        assert not result.valid
        assert len(result.missing_dirs) > 0

    def test_validate_returns_invalid_when_files_missing(self, fs: AnalyticsFilesystemInit):
        """Test that validate fails when files are missing."""
        fs.initialize()

        some_file = fs.base / REQUIRED_FILES[0]
        if some_file.exists():
            some_file.unlink()

        result = fs.validate()

        assert not result.valid
        assert len(result.missing_files) > 0

    def test_validate_never_creates_directories(self, fs: AnalyticsFilesystemInit):
        """Test that validate never creates directories."""
        result = fs.validate()

        assert not result.valid

        for rel_dir in REQUIRED_DIRS:
            dir_path = fs.base / rel_dir
            assert not dir_path.exists(), f"Validate should not create: {rel_dir}"

    def test_get_signal_path_returns_correct_path(self, fs: AnalyticsFilesystemInit):
        """Test that get_signal_path returns expected path."""
        path = fs.get_signal_path("anomalies", "test-signal-123")

        assert path == fs.base / "signals" / "anomalies" / "test-signal-123.json"

    def test_get_data_path_returns_correct_path(self, fs: AnalyticsFilesystemInit):
        """Test that get_data_path returns expected path."""
        path = fs.get_data_path("content-performance")

        assert path == fs.base / "data" / "content-performance"

    def test_get_data_path_with_sub_path(self, fs: AnalyticsFilesystemInit):
        """Test that get_data_path with sub_path returns correct path."""
        path = fs.get_data_path("content-performance", "linkedin/2024-01/performance.jsonl")

        assert path == fs.base / "data" / "content-performance" / "linkedin" / "2024-01" / "performance.jsonl"

    def test_get_report_path_returns_correct_path(self, fs: AnalyticsFilesystemInit):
        """Test that get_report_path returns expected path."""
        path = fs.get_report_path()

        assert path == fs.base / "reports" / "weekly-intelligence.json"

    def test_get_baseline_path_returns_correct_path(self, fs: AnalyticsFilesystemInit):
        """Test that get_baseline_path returns expected path."""
        path = fs.get_baseline_path("content")

        assert path == fs.base / "baselines" / "content-baseline.json"

    def test_get_log_path_returns_correct_path(self, fs: AnalyticsFilesystemInit):
        """Test that get_log_path returns expected path."""
        path = fs.get_log_path("operational.log")

        assert path == fs.base / "logs" / "operational.log"


class TestAnalyticsLogEntry:
    """Tests for AnalyticsLogEntry dataclass."""

    def test_to_json_returns_valid_json(self):
        """Test that to_json returns valid JSON string."""
        entry = AnalyticsLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            action_type="test_action",
            entity_id="test-entity",
            source_claw="content",
            outcome="success",
            details={"key": "value"},
        )

        json_str = entry.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["action_type"] == "test_action"
        assert data["entity_id"] == "test-entity"

    def test_to_json_handles_none_source_claw(self):
        """Test that to_json handles None source_claw."""
        entry = AnalyticsLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            action_type="test_action",
            entity_id="test-entity",
            source_claw=None,
            outcome="success",
            details={},
        )

        json_str = entry.to_json()
        data = json.loads(json_str)

        assert data["source_claw"] is None


class TestAnalyticsOperationalLog:
    """Tests for AnalyticsOperationalLog class."""

    def test_append_writes_to_log_file(self, temp_sandbox: Path):
        """Test that append writes entry to log file."""
        log_path = temp_sandbox / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        op_log = AnalyticsOperationalLog(log_path)

        entry = AnalyticsLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="test_action",
            entity_id="test-entity",
            source_claw="content",
            outcome="success",
            details={"test": True},
        )

        op_log.append(entry)

        assert log_path.exists()
        content = log_path.read_text()
        assert "test_action" in content
        assert "test-entity" in content

    def test_append_is_thread_safe(self, temp_sandbox: Path):
        """Test that concurrent appends are thread-safe."""
        log_path = temp_sandbox / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        op_log = AnalyticsOperationalLog(log_path)

        num_threads = 10
        entries_per_thread = 100
        threads = []

        def write_entries(thread_id: int) -> None:
            for i in range(entries_per_thread):
                entry = AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type=f"thread_{thread_id}_entry_{i}",
                    entity_id=f"entity_{thread_id}_{i}",
                    source_claw=None,
                    outcome="success",
                    details={},
                )
                op_log.append(entry)

        for i in range(num_threads):
            t = threading.Thread(target=write_entries, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        content = log_path.read_text()
        lines = [l for l in content.strip().split("\n") if l]

        assert len(lines) == num_threads * entries_per_thread

        unique_actions = set()
        for line in lines:
            data = json.loads(line)
            unique_actions.add(data["action_type"])

        assert len(unique_actions) == num_threads * entries_per_thread

    def test_read_recent_returns_entries_within_days(self, temp_sandbox: Path):
        """Test that read_recent filters by days."""
        log_path = temp_sandbox / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        op_log = AnalyticsOperationalLog(log_path)

        now = datetime.now(timezone.utc)

        for i in range(10):
            days_ago = i
            timestamp = (now - __import__("datetime").timedelta(days=days_ago)).isoformat()
            entry = AnalyticsLogEntry(
                timestamp=timestamp,
                action_type=f"action_{i}",
                entity_id=f"entity_{i}",
                source_claw=None,
                outcome="success",
                details={},
            )
            op_log.append(entry)

        recent = op_log.read_recent(days=3)

        assert len(recent) == 4

    def test_read_recent_filters_by_action_type(self, temp_sandbox: Path):
        """Test that read_recent filters by action_type."""
        log_path = temp_sandbox / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        op_log = AnalyticsOperationalLog(log_path)

        for i in range(5):
            entry = AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="type_a" if i < 3 else "type_b",
                entity_id=f"entity_{i}",
                source_claw=None,
                outcome="success",
                details={},
            )
            op_log.append(entry)

        type_a = op_log.read_recent(days=1, action_type="type_a")
        type_b = op_log.read_recent(days=1, action_type="type_b")

        assert len(type_a) == 3
        assert len(type_b) == 2

    def test_count_by_type_returns_correct_count(self, temp_sandbox: Path):
        """Test that count_by_type returns correct count."""
        log_path = temp_sandbox / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        op_log = AnalyticsOperationalLog(log_path)

        for i in range(7):
            entry = AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="test_action",
                entity_id=f"entity_{i}",
                source_claw=None,
                outcome="success",
                details={},
            )
            op_log.append(entry)

        count = op_log.count_by_type("test_action", days=1)

        assert count == 7

    def test_read_recent_returns_empty_when_file_not_exists(self, temp_sandbox: Path):
        """Test that read_recent returns empty list when file doesn't exist."""
        log_path = temp_sandbox / "logs" / "nonexistent.log"

        op_log = AnalyticsOperationalLog(log_path)

        entries = op_log.read_recent(days=7)

        assert entries == []
