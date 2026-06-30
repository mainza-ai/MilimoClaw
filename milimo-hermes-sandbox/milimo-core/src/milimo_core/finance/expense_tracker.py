# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Expense Tracker.

Logs expenses and classifies them for tax preparation.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
import uuid
import json

from .finance_init import FinanceOperationalLog, FinanceLogEntry


class InferenceClient(Protocol):
    """Protocol for inference client."""

    def complete(
        self,
        prompt: str,
        data_type: str,
        max_tokens: int = 800,
    ) -> str:
        """Complete a prompt with the model."""
        ...


@dataclass
class ExpenseEntry:
    """Expense entry."""

    expense_id: str
    description: str
    amount: float
    currency: str
    expense_date: str
    tax_category: str
    source: str
    logged_at: str

    def to_dict(self) -> dict:
        return {
            "expense_id": self.expense_id,
            "description": self.description,
            "amount": self.amount,
            "currency": self.currency,
            "expense_date": self.expense_date,
            "tax_category": self.tax_category,
            "source": self.source,
            "logged_at": self.logged_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExpenseEntry":
        return cls(
            expense_id=data["expense_id"],
            description=data["description"],
            amount=data["amount"],
            currency=data.get("currency", "USD"),
            expense_date=data["expense_date"],
            tax_category=data.get("tax_category", "uncategorized"),
            source=data.get("source", "manual"),
            logged_at=data["logged_at"],
        )


TAX_CATEGORIES = [
    "office_supplies",
    "software_subscriptions",
    "hardware_equipment",
    "travel",
    "meals_entertainment",
    "professional_services",
    "marketing_advertising",
    "education_training",
    "utilities",
    "insurance",
    "rent_lease",
    "bank_fees",
    "other_business",
    "uncategorized",
]


class ExpenseTracker:
    """
    Logs expenses and classifies them for tax preparation.

    Expenses are logged as AUTO (no approval required).
    Uncategorized expenses are batched at quarterly tax prep.
    All inference calls log data_type.
    """

    def __init__(
        self,
        fs_path: Path,
        inference_client: InferenceClient,
        operational_log: FinanceOperationalLog,
    ):
        self.fs_path = fs_path
        self.inference_client = inference_client
        self.operational_log = operational_log

    def log_expense(
        self,
        description: str,
        amount: float,
        expense_date: str,
        source: str = "manual",
    ) -> ExpenseEntry:
        """
        Log an expense.

        1. Assign expense_id (UUID)
        2. Classify tax category via inference with data_type="tax_category_classification"
        3. On failure: category = "uncategorized"
        4. Append to expenses/log.jsonl (thread-safe)
        5. Update category summary in expenses/categories/{category}.json
        6. Log operational.log: action_type="expense_logged" (AUTO)
        7. Return ExpenseEntry
        """
        expense_id = f"exp-{uuid.uuid4().hex[:8]}"
        logged_at = datetime.now(timezone.utc).isoformat()

        tax_category = self._classify_expense(description, amount)

        expense = ExpenseEntry(
            expense_id=expense_id,
            description=description,
            amount=amount,
            currency="USD",
            expense_date=expense_date,
            tax_category=tax_category,
            source=source,
            logged_at=logged_at,
        )

        self._append_expense(expense)
        self._update_category_summary(expense)

        entry = FinanceLogEntry(
            timestamp=logged_at,
            action_type="expense_logged",
            entity_id=expense_id,
            amount=amount,
            outcome="success",
            details={"category": tax_category, "source": source},
        )
        self.operational_log.append(entry)

        return expense

    def get_uncategorized_expenses(self) -> list[ExpenseEntry]:
        """
        Get all uncategorized expenses.

        Read expenses/log.jsonl.
        Filter where tax_category == "uncategorized".
        Used during quarterly tax prep batch review.
        """
        expenses: list[ExpenseEntry] = []
        log_path = self.fs_path / "expenses" / "log.jsonl"

        if not log_path.exists():
            return expenses

        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("tax_category") == "uncategorized":
                        expenses.append(ExpenseEntry.from_dict(data))
                except (json.JSONDecodeError, KeyError):
                    continue

        return expenses

    def recategorize_expense(self, expense_id: str, new_category: str) -> None:
        """
        Recategorize an expense.

        Update category in log.jsonl entry (find by expense_id).
        Update category summary files.
        Log: action_type="expense_recategorized"
        """
        import fcntl

        log_path = self.fs_path / "expenses" / "log.jsonl"

        if not log_path.exists():
            return

        lines: list[str] = []
        old_category = ""
        expense_amount = 0.0

        with open(log_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("expense_id") == expense_id:
                            old_category = data.get("tax_category", "")
                            expense_amount = data.get("amount", 0)
                            data["tax_category"] = new_category
                            line = json.dumps(data)
                        lines.append(line)
                    except json.JSONDecodeError:
                        lines.append(line)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        with open(log_path, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write("\n".join(lines) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        if old_category:
            self._decrement_category_summary(old_category, expense_amount)
        self._update_category_summary_by_category(new_category, expense_amount)

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="expense_recategorized",
            entity_id=expense_id,
            amount=expense_amount,
            outcome="success",
            details={"old_category": old_category, "new_category": new_category},
        )
        self.operational_log.append(entry)

    def get_expenses_by_period(
        self, start_date: str, end_date: str
    ) -> list[ExpenseEntry]:
        """
        Get expenses by period.

        Read log.jsonl, filter by expense_date range.
        Used by quarterly tax prep.
        """
        expenses: list[ExpenseEntry] = []
        log_path = self.fs_path / "expenses" / "log.jsonl"

        if not log_path.exists():
            return expenses

        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    expense_date = data.get("expense_date", "")
                    if start_date <= expense_date <= end_date:
                        expenses.append(ExpenseEntry.from_dict(data))
                except (json.JSONDecodeError, KeyError):
                    continue

        return expenses

    def get_category_summary(self) -> dict[str, float]:
        """
        Get category summary.

        Return {category: total_amount} for current year.
        Read from expenses/categories/.
        """
        summary: dict[str, float] = {}
        categories_dir = self.fs_path / "expenses" / "categories"

        if not categories_dir.exists():
            return summary

        for path in categories_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                category = path.stem
                summary[category] = data.get("total", 0)
            except (json.JSONDecodeError, KeyError):
                continue

        return summary

    def _classify_expense(self, description: str, amount: float) -> str:
        """Classify expense using inference."""
        prompt = f"""Classify this expense into a tax category.

Expense: {description}
Amount: ${amount:.2f}

Categories: office_supplies, software_subscriptions, hardware_equipment, travel, meals_entertainment, professional_services, marketing_advertising, education_training, utilities, insurance, rent_lease, bank_fees, other_business

Return only the category name."""

        try:
            output = self.inference_client.complete(
                prompt=prompt,
                data_type="tax_category_classification",
                max_tokens=50,
            )

            for category in TAX_CATEGORIES:
                if category in output.lower():
                    return category

        except Exception:
            pass

        return "uncategorized"

    def _append_expense(self, expense: ExpenseEntry) -> None:
        """Append expense to log.jsonl with file locking."""
        import fcntl

        log_path = self.fs_path / "expenses" / "log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(expense.to_dict()) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _update_category_summary(self, expense: ExpenseEntry) -> None:
        """Update category summary file."""
        self._update_category_summary_by_category(expense.tax_category, expense.amount)

    def _update_category_summary_by_category(
        self, category: str, amount: float
    ) -> None:
        """Update a specific category summary."""
        category_path = self.fs_path / "expenses" / "categories" / f"{category}.json"
        category_path.parent.mkdir(parents=True, exist_ok=True)

        data = {"total": 0, "count": 0, "last_updated": None}
        if category_path.exists():
            try:
                data = json.loads(category_path.read_text())
            except json.JSONDecodeError:
                pass

        data["total"] = data.get("total", 0) + amount
        data["count"] = data.get("count", 0) + 1
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

        category_path.write_text(json.dumps(data, indent=2))

    def _decrement_category_summary(self, category: str, amount: float) -> None:
        """Decrement a category summary."""
        category_path = self.fs_path / "expenses" / "categories" / f"{category}.json"

        if not category_path.exists():
            return

        try:
            data = json.loads(category_path.read_text())
            data["total"] = max(0, data.get("total", 0) - amount)
            data["count"] = max(0, data.get("count", 0) - 1)
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            category_path.write_text(json.dumps(data, indent=2))
        except (json.JSONDecodeError, KeyError):
            pass
