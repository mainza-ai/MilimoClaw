"""Tests for Finance Claw Filesystem Initialization."""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    FinanceLogEntry,
    PaymentEventsLog,
    PaymentEvent,
    InitResult,
    ValidationResult,
    REQUIRED_DIRS,
    REQUIRED_FILES,
)


class TestFinanceFilesystemInit:
    """Tests for FinanceFilesystemInit class."""

    def test_initialize_creates_all_directories(self, tmp_path: Path):
        """All required directories are created."""
        fs = FinanceFilesystemInit(tmp_path)
        result = fs.initialize()

        assert result.success
        for dir_path in REQUIRED_DIRS:
            full_path = tmp_path / dir_path
            assert full_path.is_dir(), f"Directory {dir_path} was not created"

    def test_initialize_creates_all_files(self, tmp_path: Path):
        """All required files are created with correct content."""
        fs = FinanceFilesystemInit(tmp_path)
        result = fs.initialize()

        assert result.success
        for file_path, content in REQUIRED_FILES.items():
            full_path = tmp_path / file_path
            assert full_path.is_file(), f"File {file_path} was not created"

            if content is not None:
                actual = json.loads(full_path.read_text())
                assert actual == content

    def test_initialize_is_idempotent(self, tmp_path: Path):
        """Running initialize twice does not raise errors."""
        fs = FinanceFilesystemInit(tmp_path)

        result1 = fs.initialize()
        assert result1.success

        result2 = fs.initialize()
        assert result2.success

        assert len(result2.created_dirs) == 0
        assert len(result2.created_files) == 0
        assert len(result2.already_existed) > 0

    def test_validate_returns_missing_directories(self, tmp_path: Path):
        """Validation detects missing directories."""
        fs = FinanceFilesystemInit(tmp_path)

        result = fs.validate()
        assert not result.valid
        assert len(result.missing_dirs) == len(REQUIRED_DIRS)
        assert len(result.missing_files) == len(REQUIRED_FILES)

    def test_validate_passes_when_complete(self, tmp_path: Path):
        """Validation passes when all paths exist."""
        fs = FinanceFilesystemInit(tmp_path)
        fs.initialize()

        result = fs.validate()
        assert result.valid
        assert len(result.missing_dirs) == 0
        assert len(result.missing_files) == 0

    def test_get_invoice_path_returns_correct_path(self, tmp_path: Path):
        """Invoice path is correctly constructed."""
        fs = FinanceFilesystemInit(tmp_path)

        path = fs.get_invoice_path("pending", "inv-123")
        assert path == tmp_path / "invoices" / "pending" / "inv-123.json"

        path = fs.get_invoice_path("approved", "inv-456")
        assert path == tmp_path / "invoices" / "approved" / "inv-456.json"

    def test_get_invoice_path_raises_on_invalid_status(self, tmp_path: Path):
        """Invalid status raises ValueError."""
        fs = FinanceFilesystemInit(tmp_path)

        with pytest.raises(ValueError, match="Invalid invoice status"):
            fs.get_invoice_path("invalid", "inv-123")  # type: ignore

    def test_get_pricing_estimate_path(self, tmp_path: Path):
        """Pricing estimate path is correct."""
        fs = FinanceFilesystemInit(tmp_path)

        path = fs.get_pricing_estimate_path("proj-123")
        assert path == tmp_path / "pricing" / "estimates" / "proj-123.json"

    def test_get_pricing_history_path(self, tmp_path: Path):
        """Pricing history path is correct."""
        fs = FinanceFilesystemInit(tmp_path)

        path = fs.get_pricing_history_path("proj-123")
        assert path == tmp_path / "pricing" / "history" / "proj-123.json"

    def test_get_tax_quarterly_path(self, tmp_path: Path):
        """Tax quarterly path is correct."""
        fs = FinanceFilesystemInit(tmp_path)

        path = fs.get_tax_quarterly_path(2026, 1)
        assert path == tmp_path / "tax" / "quarterly" / "2026-Q1.json"

        path = fs.get_tax_quarterly_path(2026, 4)
        assert path == tmp_path / "tax" / "quarterly" / "2026-Q4.json"

    def test_get_tax_quarterly_path_raises_on_invalid_quarter(self, tmp_path: Path):
        """Invalid quarter raises ValueError."""
        fs = FinanceFilesystemInit(tmp_path)

        with pytest.raises(ValueError, match="Invalid quarter"):
            fs.get_tax_quarterly_path(2026, 5)

    def test_get_revenue_daily_path(self, tmp_path: Path):
        """Revenue daily path is correct."""
        fs = FinanceFilesystemInit(tmp_path)

        date = datetime(2026, 3, 21)
        path = fs.get_revenue_daily_path(date)
        assert path == tmp_path / "revenue" / "history" / "2026-03-21.json"


class TestFinanceLogEntry:
    """Tests for FinanceLogEntry dataclass."""

    def test_to_dict(self):
        """Log entry serializes correctly."""
        entry = FinanceLogEntry(
            timestamp="2026-03-21T10:00:00",
            action_type="invoice_generated",
            entity_id="inv-123",
            amount=1500.00,
            outcome="success",
            details={"client_id": "client-456"},
        )

        data = entry.to_dict()
        assert data["timestamp"] == "2026-03-21T10:00:00"
        assert data["action_type"] == "invoice_generated"
        assert data["entity_id"] == "inv-123"
        assert data["amount"] == 1500.00
        assert data["outcome"] == "success"
        assert data["details"]["client_id"] == "client-456"

    def test_from_dict(self):
        """Log entry deserializes correctly."""
        data = {
            "timestamp": "2026-03-21T10:00:00",
            "action_type": "invoice_generated",
            "entity_id": "inv-123",
            "amount": 1500.00,
            "outcome": "success",
            "details": {"client_id": "client-456"},
        }

        entry = FinanceLogEntry.from_dict(data)
        assert entry.timestamp == "2026-03-21T10:00:00"
        assert entry.action_type == "invoice_generated"
        assert entry.entity_id == "inv-123"
        assert entry.amount == 1500.00
        assert entry.outcome == "success"
        assert entry.details["client_id"] == "client-456"


class TestFinanceOperationalLog:
    """Tests for FinanceOperationalLog class."""

    def test_append_creates_file_if_missing(self, tmp_path: Path):
        """Append creates log file if it doesn't exist."""
        log_path = tmp_path / "logs" / "operational.log"
        log = FinanceOperationalLog(log_path)

        entry = FinanceLogEntry(
            timestamp="2026-03-21T10:00:00",
            action_type="test_action",
            entity_id="test-123",
            amount=None,
            outcome="success",
            details={},
        )

        log.append(entry)
        assert log_path.exists()

    def test_append_writes_jsonl(self, tmp_path: Path):
        """Entries are written as JSONL."""
        log_path = tmp_path / "logs" / "operational.log"
        log = FinanceOperationalLog(log_path)

        entry = FinanceLogEntry(
            timestamp="2026-03-21T10:00:00",
            action_type="test_action",
            entity_id="test-123",
            amount=100.0,
            outcome="success",
            details={"key": "value"},
        )

        log.append(entry)

        content = log_path.read_text().strip()
        data = json.loads(content)
        assert data["action_type"] == "test_action"
        assert data["entity_id"] == "test-123"

    def test_read_recent_returns_filtered_entries(self, tmp_path: Path):
        """read_recent returns entries within days window."""
        log_path = tmp_path / "logs" / "operational.log"
        log = FinanceOperationalLog(log_path)

        for i in range(5):
            entry = FinanceLogEntry(
                timestamp=f"2026-03-2{i}T10:00:00",
                action_type=f"action_{i}",
                entity_id=f"entity_{i}",
                amount=None,
                outcome="success",
                details={},
            )
            log.append(entry)

        entries = log.read_recent(days=10)
        assert len(entries) == 5

    def test_read_recent_filters_by_action_type(self, tmp_path: Path):
        """read_recent filters by action_type."""
        log_path = tmp_path / "logs" / "operational.log"
        log = FinanceOperationalLog(log_path)

        for i in range(5):
            entry = FinanceLogEntry(
                timestamp="2026-03-21T10:00:00",
                action_type="invoice_generated" if i % 2 == 0 else "payment_received",
                entity_id=f"entity_{i}",
                amount=None,
                outcome="success",
                details={},
            )
            log.append(entry)

        entries = log.read_recent(days=10, action_type="invoice_generated")
        assert len(entries) == 3

    def test_count_by_type(self, tmp_path: Path):
        """count_by_type returns correct count."""
        log_path = tmp_path / "logs" / "operational.log"
        log = FinanceOperationalLog(log_path)

        for i in range(5):
            entry = FinanceLogEntry(
                timestamp="2026-03-21T10:00:00",
                action_type="invoice_generated",
                entity_id=f"entity_{i}",
                amount=None,
                outcome="success",
                details={},
            )
            log.append(entry)

        count = log.count_by_type("invoice_generated", days=10)
        assert count == 5


class TestPaymentEvent:
    """Tests for PaymentEvent dataclass."""

    def test_to_dict(self):
        """Payment event serializes correctly."""
        event = PaymentEvent(
            timestamp="2026-03-21T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-123",
            client_id="client-456",
            amount=1500.00,
            details={"stripe_id": "st_abc"},
        )

        data = event.to_dict()
        assert data["timestamp"] == "2026-03-21T10:00:00"
        assert data["event_type"] == "invoice_sent"
        assert data["invoice_id"] == "inv-123"

    def test_from_dict(self):
        """Payment event deserializes correctly."""
        data = {
            "timestamp": "2026-03-21T10:00:00",
            "event_type": "invoice_sent",
            "invoice_id": "inv-123",
            "client_id": "client-456",
            "amount": 1500.00,
            "details": {"stripe_id": "st_abc"},
        }

        event = PaymentEvent.from_dict(data)
        assert event.event_type == "invoice_sent"
        assert event.invoice_id == "inv-123"


class TestPaymentEventsLog:
    """Tests for PaymentEventsLog class."""

    def test_append_creates_file_if_missing(self, tmp_path: Path):
        """Append creates log file if it doesn't exist."""
        log_path = tmp_path / "logs" / "payment-events.log"
        log = PaymentEventsLog(log_path)

        event = PaymentEvent(
            timestamp="2026-03-21T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-123",
            client_id="client-456",
            amount=1500.00,
            details={},
        )

        log.append(event)
        assert log_path.exists()

    def test_read_recent_returns_events(self, tmp_path: Path):
        """read_recent returns events within days window."""
        log_path = tmp_path / "logs" / "payment-events.log"
        log = PaymentEventsLog(log_path)

        for i in range(5):
            event = PaymentEvent(
                timestamp=f"2026-03-2{i}T10:00:00",
                event_type="invoice_sent",
                invoice_id=f"inv-{i}",
                client_id="client-456",
                amount=100.0,
                details={},
            )
            log.append(event)

        events = log.read_recent(days=10)
        assert len(events) == 5

    def test_get_client_history(self, tmp_path: Path):
        """get_client_history returns events for specific client."""
        log_path = tmp_path / "logs" / "payment-events.log"
        log = PaymentEventsLog(log_path)

        for i in range(5):
            event = PaymentEvent(
                timestamp="2026-03-21T10:00:00",
                event_type="invoice_sent",
                invoice_id=f"inv-{i}",
                client_id=f"client-{i % 2}",
                amount=100.0,
                details={},
            )
            log.append(event)

        history = log.get_client_history("client-0")
        assert len(history) == 3

    def test_count_overdue_by_client(self, tmp_path: Path):
        """count_overdue_by_client counts overdue events."""
        log_path = tmp_path / "logs" / "payment-events.log"
        log = PaymentEventsLog(log_path)

        event_types = ["invoice_sent", "payment_overdue", "payment_overdue", "invoice_sent"]
        for i, event_type in enumerate(event_types):
            event = PaymentEvent(
                timestamp="2026-03-21T10:00:00",
                event_type=event_type,
                invoice_id=f"inv-{i}",
                client_id="client-456",
                amount=100.0,
                details={},
            )
            log.append(event)

        count = log.count_overdue_by_client("client-456")
        assert count == 2
