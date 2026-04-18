# ops-init

**Summary**: Filesystem initialization for Ops Claw.

**Sources**: `milimo-blueprint/orchestrator/ops/ops_init.py`

**Last updated**: 2026-04-14

**Tags**: #module #ops-claw

---

## Purpose

Initializes Ops Claw filesystem structure on first run.

## Location

**File**: `milimo-blueprint/orchestrator/ops/ops_init.py`

## Key Classes

### OpsFilesystemInit

Initializes Ops Claw directories.

```python
class OpsFilesystemInit:
    def __init__(self, root: str = "/sandbox/clients"):
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
/sandbox/clients/
├── active/
│   └── {client_id}/
│       ├── profile.json
│       ├── projects/
│       └── comms/
├── prospects/
├── completed/
├── contracts/
├── templates/
└── logs/
```

## Initialization Check

Runs on Ops Claw startup:
- Verifies all directories exist
- Creates missing directories
- Validates permissions

## Dependencies

- [[ops-claw]] — Parent claw

## Related Pages

- [[ops-claw]] — Parent claw
- [[file-structure]] — Full project structure
