# Expense Tracker

Logs expenses and classifies them for tax preparation.

## Purpose

Tracks all business expenses with automatic tax category classification. Uncategorized expenses are batched for quarterly tax prep review.

## Approval Routing

- All expenses logged as **AUTO** — no approval required
- Uncategorized expenses flagged for quarterly review

## Tax Categories

| Category | Examples |
|----------|----------|
| `office_supplies` | Paper, pens, equipment |
| `software_subscriptions` | SaaS, cloud services |
| `hardware_equipment` | Computers, monitors |
| `travel` | Flights, hotels, mileage |
| `meals_entertainment` | Client meals, events |
| `professional_services` | Contractors, consultants |
| `marketing_advertising` | Ads, sponsorships |
| `education_training` | Courses, certifications |
| `utilities` | Internet, phone, electricity |
| `insurance` | Business insurance |
| `rent_lease` | Office space |
| `bank_fees` | Transaction fees |
| `other_business` | Misc business expenses |
| `uncategorized` | Needs review |

## ExpenseEntry Data Class

```python
@dataclass
class ExpenseEntry:
    expense_id: str
    description: str
    amount: float
    currency: str
    expense_date: str
    tax_category: str
    source: str
    logged_at: str
```

## Methods

| Method | Purpose |
|--------|---------|
| `log_expense()` | Log and classify new expense |
| `get_uncategorized_expenses()` | Get expenses needing review |
| `recategorize_expense()` | Change expense category |
| `get_expenses_by_period()` | Get expenses for date range |
| `get_category_summary()` | Get totals by category |

## Classification Flow

1. Assign `expense_id` (UUID)
2. Send to inference with `data_type="tax_category_classification"`
3. On failure: category = "uncategorized"
4. Append to `expenses/log.jsonl` (thread-safe)
5. Update category summary in `expenses/categories/{category}.json`

## File Locations

```
/sandbox/finance/expenses/
├── log.jsonl                    # All expenses (JSONL)
└── categories/
    ├── office_supplies.json     # Category summaries
    ├── software_subscriptions.json
    └── uncategorized.json
```

## Category Summary Format

```json
{
  "total": 1250.00,
  "count": 12,
  "last_updated": "2026-01-15T10:30:00Z"
}
```

## Dependencies

- `FinanceOperationalLog` — Action logging
- `InferenceClient` — Classification

## Relationships

- Used by: [[quarterly-tax-prep]] — Batch review uncategorized expenses

## Source

`milimo-blueprint/orchestrator/finance/expense_tracker.py`
