# content-init

**Summary**: Filesystem initialization and validation for Content Claw.

**Sources**: `milimo-blueprint/orchestrator/content/content_init.py`

**Last updated**: 2026-04-14

**Tags**: #module #content-claw

---

## Purpose

Initializes and validates the Content Claw filesystem structure, ensuring all required directories and files exist before the claw starts.

## Location

**File**: `milimo-blueprint/orchestrator/content/content_init.py`

## Key Classes

### ContentFilesystemInit

Validates and creates the Content Claw directory structure.

```python
class ContentFilesystemInit:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.created_dirs: list[Path] = []
        self.existed_dirs: list[Path] = []
        self.failed_dirs: list[Path] = []

    def initialize(self) -> ContentInitResult:
        """Create missing directories and return status."""
        pass
```

### ContentOperationalLog

Append-only JSONL log for Content Claw operations.

```python
class ContentOperationalLog:
    def __init__(self, log_path: Path):
        self.log_path = log_path

    def append(self, entry: ContentLogEntry) -> None:
        """Append entry to operational log."""
        pass
```

## Directory Structure

Creates these directories:

```
/sandbox/content/
├── drafts/           # Draft content
├── approved/         # Approved content ready for publishing
├── published/        # Published content archive
├── brand/            # Brand assets and style guides
│   └── voice-profiles/
├── logs/             # Operational logs
└── queue/            # Message queue
    ├── inbox/
    └── outbox/
```

## Dependencies

- `pathlib.Path` — File path handling
- `logging` — Operation logging
- `json` — Log entry serialization

## Usage

```python
from orchestrator.content.content_init import ContentFilesystemInit

fs = ContentFilesystemInit(Path("/sandbox/content"))
result = fs.initialize()

if not result.success:
    raise RuntimeError(f"Init failed: {result.failed}")
```

## Related Pages

- [[content-claw]] — Parent claw
- [[content-generator]] — Uses initialized structure
- [[sandbox-isolation]] — Mount configuration
