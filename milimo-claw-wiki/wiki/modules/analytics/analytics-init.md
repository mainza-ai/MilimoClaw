# analytics-init

**Summary**: Filesystem initialization for Analytics Claw.

**Sources**: `milimo-blueprint/orchestrator/analytics/analytics_init.py`

**Last updated**: 2026-04-14

**Tags**: #module #analytics-claw

---

## Purpose

Initializes Analytics Claw filesystem structure on first run.

## Location

**File**: `milimo-blueprint/orchestrator/analytics/analytics_init.py`

## Key Classes

### AnalyticsFilesystemInit

Initializes Analytics Claw directories.

```python
class AnalyticsFilesystemInit:
    def __init__(self, root: str = "/sandbox/analytics"):
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
/sandbox/analytics/
├── reports/
│   ├── weekly-intelligence.json
│   ├── weekly-intelligence-archive/
│   └── opportunity-scores.json
├── signals/
│   ├── anomalies/
│   ├── opportunities/
│   └── alerts/
├── data/
│   ├── content-performance/
│   ├── client-health/
│   ├── revenue/
│   └── delivery-velocity/
├── baselines/
├── tools/
└── logs/
```

## Initialization Check

Runs on Analytics Claw startup:
- Verifies all directories exist
- Creates missing directories
- Validates shared-read permissions

## Dependencies

- [[analytics-claw]] — Parent claw

## Related Pages

- [[analytics-claw]] — Parent claw
- [[file-structure]] — Full project structure
