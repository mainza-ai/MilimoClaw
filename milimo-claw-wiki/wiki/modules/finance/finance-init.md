# finance-init

**Summary**: Filesystem initialization for Finance Claw.

**Sources**: `milimo-blueprint/orchestrator/finance/finance_init.py`

**Last updated**: 2026-04-14

**Tags**: #module #finance-claw

---

## Purpose

Initializes Finance Claw filesystem structure on first run.

## Location

**File**: `milimo-blueprint/orchestrator/finance/finance_init.py`

## Key Classes

### FinanceFilesystemInit

Initializes Finance Claw directories.

```python
class FinanceFilesystemInit:
    def __init__(self, root: str = "/sandbox/finance"):
        self._root = root

    def initialize(self) -> None:
        """Create all required directories."""
        pass

    def verify(self) -> bool:
        """Verify filesystem structure is correct."""
        pass
```

## Directory Structure

```
/sandbox/finance/
├── revenue/
│   ├── weekly-summary.json
│   ├── monthly-summary.json
│   ├── annual-summary.json
│   └── history/
├── invoices/
│   ├── pending/
│   ├── approved/
│   ├── sent/
│   ├── paid/
│   └── overdue/
├── expenses/
│   ├── log.jsonl
│   └── categories/
├── pricing/
│   ├── rules.json
│   ├── estimates/
│   └── history/
├── tax/
│   ├── categories.json
│   ├── quarterly/
│   └── annual/
└── logs/
```

## Initialization Check

Runs on Finance Claw startup:
- Verifies all directories exist
- Creates missing directories
- Validates permissions (no read access from other claws)

## Isolation

Finance Claw is the most isolated:
- No other claw can read `/sandbox/finance`
- Data shared only through messages
- Kernel-level Landlock enforcement

## Dependencies

- [[finance-claw]] — Parent claw

## Related Pages

- [[finance-claw]] — Parent claw
- [[sandbox-isolation]] — Isolation model
- [[file-structure]] — Full project structure
