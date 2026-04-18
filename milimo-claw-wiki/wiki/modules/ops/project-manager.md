# project-manager

**Summary**: Project lifecycle management and deadline tracking.

**Sources**: `milimo-blueprint/orchestrator/ops/project_manager.py`

**Last updated**: 2026-04-14

**Tags**: #module #ops-claw

---

## Purpose

Manages project lifecycle from intake to delivery, including deadline tracking and risk detection.

## Location

**File**: `milimo-blueprint/orchestrator/ops/project_manager.py`

## Key Classes

### ProjectManager

Manages project lifecycle and tracking.

```python
class ProjectManager:
    def __init__(
        self,
        fs: OpsFilesystemInit,
        war_room: WarRoomClient,
        mesh: MeshClient,
    ):
        self._fs = fs
        self._war_room = war_room
        self._mesh = mesh

    def create_project(self, brief: ProjectBrief) -> Project:
        """Create new project from validated brief."""
        pass

    def check_deadline_risk(self) -> List[DeadlineRisk]:
        """Check all active projects for deadline risk."""
        pass

    def complete_project(self, project_id: str) -> None:
        """Mark project as completed."""
        pass
```

## Project Storage

```
/sandbox/clients/active/{client_id}/projects/{project_id}/
├── brief.json      # original brief
├── status.json     # current state
├── timeline.json   # milestones, deadlines, risks
└── comms/          # project communication log
```

## Deadline Risk Detection

**Daily check:**
- Deadline within 5+ days + risk → REVIEW
- Deadline within 24 hours + not received → HOLD

## Message Flow

1. **Receive** `project_brief` from intake
2. **Create** project record
3. **Send** `project_brief` to Content/Build Claw
4. **Monitor** timeline and risks
5. **Receive** `deliverable_complete`
6. **Send** `project_complete` to Finance Claw

## Dependencies

- [[intake-manager]] — Brief source
- [[health-scorer]] — Health signals
- [[ops-scheduler]] — Scheduled checks

## Related Pages

- [[ops-claw]] — Parent claw
- [[intake-manager]] — Client intake
- [[message-contracts]] — Message schemas
