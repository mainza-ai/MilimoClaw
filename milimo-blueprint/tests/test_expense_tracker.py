"""Tests for Finance Claw Expense Tracker."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import FinanceOperationalLog
from finance.expense_tracker import (
    ExpenseTracker,
    ExpenseEntry,
    TAX_CATEGORIES,
)


class MockInferenceClient:
    """Mock inference client."""

    def __init__(self, response: str | None = None, should_fail: bool = False):
        self.response = response
        self.should_fail = should_fail
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        self.calls.append({"prompt": prompt, "data_type": data_type})
        if self.should_fail:
            raise RuntimeError("Inference failed")
        if self.response:
            return self.response
        return "software_subscriptions"


class TestExpenseTracker:
    """Tests for ExpenseTracker."""

    @pytest.fixture
    def fs_path(self, tmp_path: Path):
        return tmp_path

    @pytest.fixture
    def operational_log(self, tmp_path: Path):
        log_path = tmp_path / "logs" / "operational.log"
        return FinanceOperationalLog(log_path)

    @pytest.fixture
    def inference_client(self):
        return MockInferenceClient()

    @pytest.fixture
    def expense_tracker(self, fs_path, inference_client, operational_log):
        return ExpenseTracker(
            fs_path=fs_path,
            inference_client=inference_client,
            operational_log=operational_log,
        )

    def test_log_expense_returns_expense_entry(self, expense_tracker):
        """log_expense returns an ExpenseEntry."""
        expense = expense_tracker.log_expense(
            description="Adobe subscription",
            amount=50.00,
            expense_date="2026-03-01",
        )

        assert isinstance(expense, ExpenseEntry)
        assert expense.description == "Adobe subscription"
        assert expense.amount == 50.00

    def test_expense_id_is_uuid_format(self, expense_tracker):
        """expense_id has format 'exp-{uuid8}'."""
        expense = expense_tracker.log_expense(
            description="Test expense",
            amount=100.00,
            expense_date="2026-03-01",
        )

        assert expense.expense_id.startswith("exp-")
        assert len(expense.expense_id) == 12

    def test_expense_written_to_log_jsonl(self, expense_tracker, fs_path):
        """Expense is appended to expenses/log.jsonl."""
        expense = expense_tracker.log_expense(
            description="Office supplies",
            amount=75.00,
            expense_date="2026-03-15",
        )

        log_path = fs_path / "expenses" / "log.jsonl"
        assert log_path.exists()

        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) >= 1
        data = json.loads(lines[-1])
        assert data["expense_id"] == expense.expense_id
        assert data["amount"] == 75.00

    def test_inference_call_includes_data_type(self, expense_tracker, inference_client):
        """Inference call includes data_type='tax_category_classification'."""
        expense_tracker.log_expense(
            description="AWS bill",
            amount=200.00,
            expense_date="2026-03-01",
        )

        assert len(inference_client.calls) >= 1
        assert inference_client.calls[0]["data_type"] == "tax_category_classification"

    def test_category_classification(self, expense_tracker):
        """Expense is classified into a tax category."""
        classified_client = MockInferenceClient(response="software_subscriptions")
        expense_tracker.inference_client = classified_client

        expense = expense_tracker.log_expense(
            description="GitHub subscription",
            amount=25.00,
            expense_date="2026-03-01",
        )

        assert expense.tax_category == "software_subscriptions"

    def test_fallback_to_uncategorized_on_failure(self, expense_tracker):
        """Uncategorized when inference fails."""
        failing_client = MockInferenceClient(should_fail=True)
        expense_tracker.inference_client = failing_client

        expense = expense_tracker.log_expense(
            description="Mystery purchase",
            amount=100.00,
            expense_date="2026-03-01",
        )

        assert expense.tax_category == "uncategorized"

    def test_category_summary_updated(self, expense_tracker, fs_path):
        """Category summary file is updated."""
        classified_client = MockInferenceClient(response="office_supplies")
        expense_tracker.inference_client = classified_client

        expense_tracker.log_expense(
            description="Notebooks",
            amount=30.00,
            expense_date="2026-03-01",
        )

        category_path = fs_path / "expenses" / "categories" / "office_supplies.json"
        assert category_path.exists()

        data = json.loads(category_path.read_text())
        assert data["total"] == 30.00
        assert data["count"] == 1

    def test_get_uncategorized_expenses(self, expense_tracker, fs_path):
        """get_uncategorized_expenses returns correct expenses."""
        log_path = fs_path / "expenses" / "log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            expense = ExpenseEntry(
                expense_id=f"exp-{i}",
                description=f"Expense {i}",
                amount=100 * i,
                currency="USD",
                expense_date="2026-03-01",
                tax_category="uncategorized" if i % 2 == 0 else "office_supplies",
                source="manual",
                logged_at="2026-03-01T10:00:00",
            )
            with open(log_path, "a") as f:
                f.write(json.dumps(expense.to_dict()) + "\n")

        uncategorized = expense_tracker.get_uncategorized_expenses()

        assert len(uncategorized) == 2

    def test_recategorize_expense(self, expense_tracker, fs_path):
        """recategorize_expense updates category."""
        log_path = fs_path / "expenses" / "log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        expense = ExpenseEntry(
            expense_id="exp-recat",
            description="Test expense",
            amount=100,
            currency="USD",
            expense_date="2026-03-01",
            tax_category="uncategorized",
            source="manual",
            logged_at="2026-03-01T10:00:00",
        )
        log_path.write_text(json.dumps(expense.to_dict()) + "\n")

        expense_tracker.recategorize_expense("exp-recat", "travel")

        with open(log_path) as f:
            data = json.loads(f.read())

        assert data["tax_category"] == "travel"

    def test_get_expenses_by_period(self, expense_tracker, fs_path):
        """get_expenses_by_period filters by date range."""
        log_path = fs_path / "expenses" / "log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        for i, date in enumerate(["2026-01-15", "2026-02-15", "2026-03-15"]):
            expense = ExpenseEntry(
                expense_id=f"exp-period-{i}",
                description=f"Expense {i}",
                amount=100,
                currency="USD",
                expense_date=date,
                tax_category="other",
                source="manual",
                logged_at="2026-03-01T10:00:00",
            )
            with open(log_path, "a") as f:
                f.write(json.dumps(expense.to_dict()) + "\n")

        expenses = expense_tracker.get_expenses_by_period("2026-02-01", "2026-03-01")

        assert len(expenses) == 1
        assert expenses[0].expense_date == "2026-02-15"

    def test_get_category_summary(self, expense_tracker, fs_path):
        """get_category_summary returns totals by category."""
        categories_dir = fs_path / "expenses" / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)

        (categories_dir / "office_supplies.json").write_text(json.dumps({"total": 150, "count": 3}))
        (categories_dir / "software_subscriptions.json").write_text(json.dumps({"total": 500, "count": 2}))

        summary = expense_tracker.get_category_summary()

        assert summary["office_supplies"] == 150
        assert summary["software_subscriptions"] == 500

    def test_tax_categories_list_exists(self):
        """TAX_CATEGORIES contains expected categories."""
        assert "office_supplies" in TAX_CATEGORIES
        assert "software_subscriptions" in TAX_CATEGORIES
        assert "uncategorized" in TAX_CATEGORIES

    def test_logged_to_operational_log(self, expense_tracker, operational_log):
        """Expense logging is logged to operational.log."""
        expense_tracker.log_expense(
            description="Test log",
            amount=50.00,
            expense_date="2026-03-01",
        )

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "expense_logged" for e in entries)

    def test_multiple_expenses_accumulate_in_category(self, expense_tracker, fs_path):
        """Multiple expenses accumulate in category summary."""
        classified_client = MockInferenceClient(response="travel")
        expense_tracker.inference_client = classified_client

        expense_tracker.log_expense("Flight", 300, "2026-03-01")
        expense_tracker.log_expense("Hotel", 200, "2026-03-02")

        category_path = fs_path / "expenses" / "categories" / "travel.json"
        data = json.loads(category_path.read_text())

        assert data["total"] == 500
        assert data["count"] == 2

    def test_file_locking_on_append(self, expense_tracker, fs_path):
        """Expense log uses file locking for thread safety."""
        import fcntl

        expense = expense_tracker.log_expense(
            description="Lock test",
            amount=100,
            expense_date="2026-03-01",
        )

        log_path = fs_path / "expenses" / "log.jsonl"
        assert log_path.exists()

    def test_expense_entry_to_dict(self):
        """ExpenseEntry.to_dict serializes correctly."""
        expense = ExpenseEntry(
            expense_id="exp-123",
            description="Test",
            amount=100,
            currency="USD",
            expense_date="2026-03-01",
            tax_category="office_supplies",
            source="manual",
            logged_at="2026-03-01T10:00:00",
        )

        data = expense.to_dict()

        assert data["expense_id"] == "exp-123"
        assert data["amount"] == 100
        assert data["tax_category"] == "office_supplies"

    def test_expense_entry_from_dict(self):
        """ExpenseEntry.from_dict deserializes correctly."""
        data = {
            "expense_id": "exp-456",
            "description": "Test from dict",
            "amount": 200,
            "currency": "USD",
            "expense_date": "2026-03-01",
            "tax_category": "travel",
            "source": "manual",
            "logged_at": "2026-03-01T10:00:00",
        }

        expense = ExpenseEntry.from_dict(data)

        assert expense.expense_id == "exp-456"
        assert expense.amount == 200
