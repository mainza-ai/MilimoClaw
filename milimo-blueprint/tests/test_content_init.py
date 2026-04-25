# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Content Filesystem Initialization.

Tests cover:
- Directory creation
- Idempotent re-run (no errors on second call)
- Validation pass/fail
- Log append and read
- Thread-safe concurrent writes
"""

import json
import threading
from pathlib import Path


from orchestrator.content.content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
    generate_draft_id,
    generate_brief_id,
    generate_post_id,
)


class TestContentFilesystemInit:
    """Tests for ContentFilesystemInit class."""

    def test_initialize_creates_all_directories(self, tmp_path: Path):
        """All required directories are created."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        result = fs.initialize()

        assert result.success is True
        assert len(result.created) > 0

        # Check all required directories exist
        for dir_path in ContentFilesystemInit.REQUIRED_DIRS:
            full_path = tmp_path / dir_path
            assert full_path.is_dir(), f"Directory not created: {full_path}"

    def test_initialize_creates_log_files(self, tmp_path: Path):
        """All required log files are created."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        result = fs.initialize()

        assert result.success is True

        # Check all log files exist
        for log_file in ContentFilesystemInit.REQUIRED_LOG_FILES:
            full_path = tmp_path / log_file
            assert full_path.is_file(), f"Log file not created: {full_path}"

    def test_initialize_idempotent(self, tmp_path: Path):
        """Running initialize twice doesn't error or overwrite."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        # First run
        result1 = fs.initialize()
        assert result1.success is True
        assert len(result1.created) > 0

        # Second run
        result2 = fs.initialize()
        assert result2.success is True
        assert len(result2.created) == 0
        assert len(result2.already_existed) == len(result1.created) + len(
            result1.already_existed
        )

    def test_validate_returns_valid_on_complete_structure(self, tmp_path: Path):
        """Validation passes when all paths exist."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        result = fs.validate()

        assert result.valid is True
        assert len(result.missing_paths) == 0
        assert len(result.invalid_log_files) == 0

    def test_validate_returns_missing_paths(self, tmp_path: Path):
        """Validation reports missing directories."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        # Don't initialize - validate directly
        result = fs.validate()

        assert result.valid is False
        assert len(result.missing_paths) > 0

    def test_get_draft_path_returns_correct_path(self, tmp_path: Path):
        """Draft path is correctly constructed."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        path = fs.get_draft_path("pending", "draft-123")

        assert path == tmp_path / "drafts" / "pending" / "draft-123.json"

    def test_get_draft_path_all_statuses(self, tmp_path: Path):
        """Draft path works for all status values."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        for status in ["pending", "approved", "rejected", "published"]:
            path = fs.get_draft_path(status, "draft-123")  # type: ignore[arg-type]
            assert status in str(path)

    def test_get_brief_path_returns_correct_path(self, tmp_path: Path):
        """Brief path is correctly constructed."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        path = fs.get_brief_path("active", "brief-456")

        assert path == tmp_path / "briefs" / "active" / "brief-456.json"

    def test_get_brief_path_all_statuses(self, tmp_path: Path):
        """Brief path works for all status values."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        for status in ["active", "completed"]:
            path = fs.get_brief_path(status, "brief-123")  # type: ignore[arg-type]
            assert status in str(path)

    def test_get_voice_profile_path(self, tmp_path: Path):
        """Voice profile path is correctly constructed."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        path = fs.get_voice_profile_path("client-acme")

        assert path == tmp_path / "brand" / "voice-profiles" / "client-acme.json"

    def test_get_style_guide_path_default(self, tmp_path: Path):
        """Default style guide path is correctly constructed."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        path = fs.get_style_guide_path()

        assert path == tmp_path / "brand" / "style-guides" / "default.md"

    def test_get_style_guide_path_client_specific(self, tmp_path: Path):
        """Client-specific style guide path is correctly constructed."""
        fs = ContentFilesystemInit(base_path=tmp_path)

        path = fs.get_style_guide_path("client-acme")

        assert path == tmp_path / "brand" / "style-guides" / "client-acme.md"


class TestContentOperationalLog:
    """Tests for ContentOperationalLog class."""

    def test_append_creates_entry(self, tmp_path: Path):
        """Log entry is correctly written."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)
        entry = LogEntry(
            action_type="draft_generated",
            entity_id="draft-123",
            outcome="success",
            platform="twitter",
            client_id="client-acme",
            details={"content_length": 280},
        )

        op_log.append(entry)

        # Verify entry was written
        content = log_path.read_text()
        data = json.loads(content.strip())

        assert data["action_type"] == "draft_generated"
        assert data["entity_id"] == "draft-123"
        assert data["outcome"] == "success"
        assert data["platform"] == "twitter"
        assert data["client_id"] == "client-acme"
        assert data["details"]["content_length"] == 280

    def test_append_multiple_entries(self, tmp_path: Path):
        """Multiple log entries are correctly written."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)

        for i in range(5):
            entry = LogEntry(
                action_type=f"action_{i}",
                entity_id=f"entity-{i}",
                outcome="success",
            )
            op_log.append(entry)

        content = log_path.read_text()
        lines = [line for line in content.strip().split("\n") if line]

        assert len(lines) == 5

    def test_read_recent_returns_entries(self, tmp_path: Path):
        """read_recent returns recent entries."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)

        # Write entries
        for i in range(3):
            entry = LogEntry(
                action_type="test_action",
                entity_id=f"entity-{i}",
                outcome="success",
            )
            op_log.append(entry)

        entries = op_log.read_recent(days=1, action_type="test_action")

        assert len(entries) == 3

    def test_read_recent_filters_by_action_type(self, tmp_path: Path):
        """read_recent filters by action type."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)

        # Write different action types
        for action in ["draft_generated", "draft_approved", "draft_generated"]:
            entry = LogEntry(
                action_type=action,
                entity_id="test",
                outcome="success",
            )
            op_log.append(entry)

        entries = op_log.read_recent(days=1, action_type="draft_generated")

        assert len(entries) == 2
        for e in entries:
            assert e.action_type == "draft_generated"

    def test_count_by_type_returns_correct_count(self, tmp_path: Path):
        """count_by_type returns accurate count."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)

        # Write entries
        for _ in range(5):
            entry = LogEntry(
                action_type="draft_generated",
                entity_id="test",
                outcome="success",
            )
            op_log.append(entry)

        for _ in range(3):
            entry = LogEntry(
                action_type="draft_approved",
                entity_id="test",
                outcome="success",
            )
            op_log.append(entry)

        assert op_log.count_by_type("draft_generated", days=1) == 5
        assert op_log.count_by_type("draft_approved", days=1) == 3

    def test_count_by_outcome(self, tmp_path: Path):
        """count_by_outcome returns accurate count."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)

        # Write entries with different outcomes
        for _ in range(4):
            entry = LogEntry(
                action_type="draft_generated",
                entity_id="test",
                outcome="success",
            )
            op_log.append(entry)

        for _ in range(2):
            entry = LogEntry(
                action_type="draft_generated",
                entity_id="test",
                outcome="failed",
            )
            op_log.append(entry)

        assert op_log.count_by_outcome("success", days=1) == 4
        assert op_log.count_by_outcome("failed", days=1) == 2

    def test_concurrent_writes_are_thread_safe(self, tmp_path: Path):
        """Multiple threads can write concurrently without data loss."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)

        num_threads = 10
        entries_per_thread = 50
        threads = []

        def write_entries(thread_id: int):
            for i in range(entries_per_thread):
                entry = LogEntry(
                    action_type=f"thread_{thread_id}",
                    entity_id=f"entry-{thread_id}-{i}",
                    outcome="success",
                )
                op_log.append(entry)

        for t_id in range(num_threads):
            thread = threading.Thread(target=write_entries, args=(t_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All entries should be written
        op_log.count_by_type("", days=1)
        # Use read_recent without filter
        all_entries = op_log.read_recent(days=1)
        assert len(all_entries) == num_threads * entries_per_thread

    def test_clear_removes_log_file(self, tmp_path: Path):
        """clear() removes the log file."""
        log_path = tmp_path / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True)

        op_log = ContentOperationalLog(log_path)
        entry = LogEntry(action_type="test", entity_id="test", outcome="success")
        op_log.append(entry)

        assert log_path.exists()

        op_log.clear()

        assert not log_path.exists()


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_log_entry_created_with_defaults(self):
        """LogEntry is created with default timestamp."""
        entry = LogEntry(
            action_type="test_action",
            entity_id="test-entity",
            outcome="success",
        )

        assert entry.action_type == "test_action"
        assert entry.entity_id == "test-entity"
        assert entry.outcome == "success"
        assert entry.timestamp is not None
        assert entry.platform is None
        assert entry.client_id is None
        assert entry.details == {}

    def test_log_entry_to_dict(self):
        """LogEntry converts to dict correctly."""
        entry = LogEntry(
            action_type="test",
            entity_id="test-id",
            outcome="success",
            platform="twitter",
            client_id="client-1",
            details={"key": "value"},
        )

        data = entry.to_dict()

        assert data["action_type"] == "test"
        assert data["entity_id"] == "test-id"
        assert data["outcome"] == "success"
        assert data["platform"] == "twitter"
        assert data["client_id"] == "client-1"
        assert data["details"]["key"] == "value"

    def test_log_entry_from_dict(self):
        """LogEntry is created from dict correctly."""
        data = {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "action_type": "test_action",
            "entity_id": "test-entity",
            "platform": "linkedin",
            "client_id": "client-2",
            "outcome": "failed",
            "details": {"error": "connection refused"},
        }

        entry = LogEntry.from_dict(data)

        assert entry.timestamp == "2026-01-01T00:00:00+00:00"
        assert entry.action_type == "test_action"
        assert entry.entity_id == "test-entity"
        assert entry.platform == "linkedin"
        assert entry.client_id == "client-2"
        assert entry.outcome == "failed"
        assert entry.details["error"] == "connection refused"


class TestIDGenerators:
    """Tests for ID generator functions."""

    def test_generate_draft_id_format(self):
        """Draft ID has correct format."""
        draft_id = generate_draft_id()

        assert draft_id.startswith("draft-")
        assert len(draft_id) == 18  # "draft-" + 12 hex chars

    def test_generate_draft_id_unique(self):
        """Generated draft IDs are unique."""
        ids = {generate_draft_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_brief_id_format(self):
        """Brief ID has correct format."""
        brief_id = generate_brief_id()

        assert brief_id.startswith("brief-")
        assert len(brief_id) == 18  # "brief-" (6) + 12 hex chars

    def test_generate_brief_id_unique(self):
        """Generated brief IDs are unique."""
        ids = {generate_brief_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_post_id_format(self):
        """Post ID has correct format."""
        post_id = generate_post_id()

        assert post_id.startswith("post-")
        assert len(post_id) == 17  # "post-" (5) + 12 hex chars

    def test_generate_post_id_unique(self):
        """Generated post IDs are unique."""
        ids = {generate_post_id() for _ in range(100)}
        assert len(ids) == 100
