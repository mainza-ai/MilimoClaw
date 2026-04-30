# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Filesystem Initialization.

Creates and validates the full /sandbox/finance/ filesystem structure.
Idempotent — safe to call on every claw startup.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import fcntl
import json


from milimo_paths import claw_base

BASE = claw_base("finance")

REQUIRED_DIRS = [
    "revenue/history",
    "invoices/pending",
    "invoices/approved",
    "invoices/sent",
    "invoices/paid",
    "invoices/overdue",
    "expenses/categories",
    "pricing/estimates",
    "pricing/history",
    "tax/quarterly",
    "tax/annual",
    "logs",
]

REQUIRED_FILES: dict[str, dict | None] = {
    "revenue/weekly-summary.json": {
        "week_total": 0,
        "invoices_paid": 0,
        "invoices_pending": 0,
        "week_over_week_pct": 0.0,
        "last_updated": None,
    },
    "revenue/monthly-summary.json": {
        "month_total": 0,
        "invoices_paid": 0,
        "last_updated": None,
    },
    "revenue/annual-summary.json": {
        "year_total": 0,
        "invoices_paid": 0,
        "last_updated": None,
    },
    "pricing/rules.json": {
        "default_hourly_rate": 0,
        "floor_multiplier": 0.8,
        "ceiling_multiplier": 1.5,
        "scope_weights": {},
        "last_updated": None,
    },
    "tax/categories.json": {
        "income_categories": [],
        "expense_categories": [],
        "last_updated": None,
    },
    "expenses/log.jsonl": None,
    "logs/operational.log": None,
    "logs/decisions.log": None,
    "logs/payment-events.log": None,
}


@dataclass
class InitResult:
    created_dirs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


@dataclass
class ValidationResult:
    missing_dirs: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_dirs and not self.missing_files


class FinanceFilesystemInit:
    """
    Creates and validates the full /sandbox/finance/ filesystem structure.
    Idempotent — safe to call on every claw startup.
    """

    def __init__(self, base_path: Path | None = None):
        self.base = base_path or BASE

    def initialize(self) -> InitResult:
        result = InitResult()

        for dir_path in REQUIRED_DIRS:
            full_path = self.base / dir_path
            try:
                if full_path.exists():
                    result.already_existed.append(dir_path)
                else:
                    full_path.mkdir(parents=True, exist_ok=True)
                    result.created_dirs.append(dir_path)
            except Exception as e:
                result.failed.append((dir_path, str(e)))

        for file_path, content in REQUIRED_FILES.items():
            full_path = self.base / file_path
            try:
                if full_path.exists():
                    result.already_existed.append(file_path)
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    if content is not None:
                        full_path.write_text(json.dumps(content, indent=2))
                    else:
                        full_path.touch()
                    result.created_files.append(file_path)
            except Exception as e:
                result.failed.append((file_path, str(e)))

        return result

    def validate(self) -> ValidationResult:
        result = ValidationResult()

        for dir_path in REQUIRED_DIRS:
            full_path = self.base / dir_path
            if not full_path.is_dir():
                result.missing_dirs.append(dir_path)

        for file_path in REQUIRED_FILES:
            full_path = self.base / file_path
            if not full_path.is_file():
                result.missing_files.append(file_path)

        return result

    def get_invoice_path(
        self,
        status: Literal["pending", "approved", "sent", "paid", "overdue", "blocked"],
        invoice_id: str,
    ) -> Path:
        valid_statuses = ["pending", "approved", "sent", "paid", "overdue"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid invoice status: {status}")
        return self.base / "invoices" / status / f"{invoice_id}.json"

    def get_pricing_estimate_path(self, project_id: str) -> Path:
        return self.base / "pricing" / "estimates" / f"{project_id}.json"

    def get_pricing_history_path(self, project_id: str) -> Path:
        return self.base / "pricing" / "history" / f"{project_id}.json"

    def get_tax_quarterly_path(self, year: int, quarter: int) -> Path:
        if quarter not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid quarter: {quarter}")
        return self.base / "tax" / "quarterly" / f"{year}-Q{quarter}.json"

    def get_revenue_daily_path(self, date: datetime) -> Path:
        return self.base / "revenue" / "history" / f"{date.strftime('%Y-%m-%d')}.json"


@dataclass
class FinanceLogEntry:
    timestamp: str
    action_type: str
    entity_id: str
    amount: float | None
    outcome: str
    details: dict

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "entity_id": self.entity_id,
            "amount": self.amount,
            "outcome": self.outcome,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FinanceLogEntry":
        return cls(
            timestamp=data["timestamp"],
            action_type=data["action_type"],
            entity_id=data["entity_id"],
            amount=data.get("amount"),
            outcome=data["outcome"],
            details=data.get("details", {}),
        )


class FinanceOperationalLog:
    """Append-only structured log. Thread-safe via file locking."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, entry: FinanceLogEntry) -> None:
        with open(self.log_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry.to_dict()) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_recent(
        self,
        days: int = 30,
        action_type: str | None = None,
    ) -> list[FinanceLogEntry]:
        entries: list[FinanceLogEntry] = []
        if not self.log_path.exists():
            return entries

        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = FinanceLogEntry.from_dict(data)
                    _dt = datetime.fromisoformat(entry.timestamp)
                    if _dt.tzinfo is None:
                        _dt = _dt.replace(tzinfo=timezone.utc)
                    entry_time = _dt.timestamp()
                    if entry_time >= cutoff:
                        if action_type is None or entry.action_type == action_type:
                            entries.append(entry)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return entries

    def count_by_type(self, action_type: str, days: int = 30) -> int:
        entries = self.read_recent(days=days, action_type=action_type)
        return len(entries)


@dataclass
class PaymentEvent:
    timestamp: str
    event_type: str
    invoice_id: str
    client_id: str
    amount: float
    details: dict

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "invoice_id": self.invoice_id,
            "client_id": self.client_id,
            "amount": self.amount,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaymentEvent":
        return cls(
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            invoice_id=data["invoice_id"],
            client_id=data["client_id"],
            amount=data["amount"],
            details=data.get("details", {}),
        )


class PaymentEventsLog:
    """Append-only payment event log. Separate from operational log."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event: PaymentEvent) -> None:
        with open(self.log_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event.to_dict()) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_recent(self, days: int = 90) -> list[PaymentEvent]:
        events: list[PaymentEvent] = []
        if not self.log_path.exists():
            return events

        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = PaymentEvent.from_dict(data)
                    _dt = datetime.fromisoformat(event.timestamp)
                    if _dt.tzinfo is None:
                        _dt = _dt.replace(tzinfo=timezone.utc)
                    event_time = _dt.timestamp()
                    if event_time >= cutoff:
                        events.append(event)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return events

    def get_client_history(self, client_id: str) -> list[PaymentEvent]:
        events = self.read_recent(days=365)
        return [e for e in events if e.client_id == client_id]

    def count_overdue_by_client(self, client_id: str) -> int:
        events = self.get_client_history(client_id)
        return sum(
            1
            for e in events
            if e.event_type in ("payment_overdue", "repeat_overdue_flagged")
        )
