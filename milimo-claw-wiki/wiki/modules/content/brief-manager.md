# brief-manager

**Summary**: Handles project brief intake and validation for Content Claw.

**Sources**: `milimo-blueprint/orchestrator/content/brief_manager.py`

**Last updated**: 2026-04-14

**Tags**: #module #content-claw

---

## Purpose

Validates and processes project briefs from Ops Claw before content generation begins.

## Location

**File**: `milimo-blueprint/orchestrator/content/brief_manager.py`

## Key Classes

### BriefManager

Manages brief intake and validation.

```python
class BriefManager:
    def __init__(
        self,
        fs: ContentFilesystemInit,
        war_room: WarRoomClient,
        mesh: MeshClient,
    ):
        self._fs = fs
        self._war_room = war_room
        self._mesh = mesh

    def receive_brief(self, brief: ProjectBrief) -> BriefValidation:
        """Validate incoming project brief."""
        pass

    def acknowledge_brief(self, brief_id: str) -> None:
        """Send brief_acknowledged to Ops Claw."""
        pass
```

## Brief Validation

Checks for:
- Missing deadline
- Undefined scope
- Missing platform targets
- Tone requirements absent
- Contradictory requirements

## Message Flow

1. **Receive** `project_brief` from Ops Claw
2. **Validate** brief completeness
3. **Send** `brief_acknowledged` within 5 minutes
4. **Queue** content generation

## File Storage

Briefs stored at:
- Active: `/sandbox/content/briefs/active/{project_id}.json`
- Completed: `/sandbox/content/briefs/completed/{project_id}.json`

## Dependencies

- [[content-init]] — Filesystem initialization
- [[content-generator]] — Draft generation
- [[ops-claw]] — Brief source

## Related Pages

- [[content-claw]] — Parent claw
- [[message-contracts]] — project_brief schema
- [[ops-claw]] — Brief sender
