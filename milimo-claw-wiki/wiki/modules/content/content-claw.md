# Content Claw

**Summary**: Main entry point for the Content Claw. Initializes all components (filesystem, content generator, brief manager, approval handler, platform publisher, performance monitor, publish scheduler, brand voice manager, content scheduler), wires them together, and starts the scheduler.

**Sources**: `milimo-blueprint/orchestrator/content/content_claw.py`

**Last updated**: 2026-04-17

**Tags**: #claw #content #entry-point

---

## Overview

`ContentClaw` is the main entry point for the Content Claw. Handles all creative content generation, from project briefs to published content.

**File**: `orchestrator/content/content_claw.py`

---

## Key Components

| Component | Type | Purpose |
|-----------|------|---------|
| `ContentFilesystemInit` | Filesystem | Initialize claw directory structure |
| `ContentOperationalLog` | Logging | Structured action logging |
| `ContentGenerator` | Content | Core content generation engine |
| `BriefManager` | Content | Project brief handling |
| `ContentApprovalHandler` | Coordination | Draft approval workflow |
| `PlatformPublisher` | Publishing | Platform-specific publishing APIs |
| `PerformanceMonitor` | Analytics | Post-publication performance tracking |
| `PublishScheduler` | Scheduling | Scheduled content publishing |
| `BrandVoiceManager` | Content | Brand voice profile management |
| `ContentScheduler` | Scheduling | Morning planning, weekly queries |
| `PrivacyRouter` | Privacy | Inference routing based on data sensitivity |
| `ToolRegistry` | Evolution | Tool inventory management |

---

## Startup Sequence

```python
claw = ContentClaw(
    squad_id="my-squad",
    inference_client=inference,
    mesh_sender=send_via_mesh,
    base_path=Path("/sandbox/content"),
    privacy_router=privacy_router,
    tool_registry=tool_registry,
    war_room=war_room
)
claw.startup()
```

**Steps:**
1. Initialize filesystem
2. Create operational log
3. Initialize `BrandVoiceManager`
4. Initialize `ContentGenerator` with privacy router and tool registry
5. Initialize `BriefManager`
6. Initialize `ContentApprovalHandler`
7. Initialize `PlatformPublisher`
8. Initialize `PerformanceMonitor`
9. Initialize `PublishScheduler`
10. Initialize `ContentScheduler`
11. Register inbound message handlers
12. Start scheduler

---

## Inbound Message Handlers

| Message Type | Handler | Source Claw |
|--------------|---------|-------------|
| `project_brief` | `_handle_project_brief` | Ops Claw |
| `performance_intel` | `_handle_performance_intel` | Analytics Claw |
| `client_health_signal` | `_handle_client_health_signal` | Analytics Claw |
| `revision_request` | `_handle_revision_request` | Ops Claw |
| `content_performance_response` | `_handle_content_performance_response` | Analytics Claw |
| `assistant_query` | `_handle_assistant_query` | Lucy |
| `assistant_task` | `_handle_assistant_task` | Lucy |

---

## Message Flow

### Inbound (from other claws)
```
project_brief (Ops) → BriefManager → acknowledge within 5min SLA
performance_intel (Analytics) → ContentScheduler → morning planning
client_health_signal (Analytics) → ContentScheduler → adjust priority
revision_request (Ops) → BriefManager → re-generate
```

### Outbound (to other claws)
```
draft_ready → War Room (for approval)
content_performance_query → Analytics
performance_signal → Analytics
brief_acknowledged → Ops
deliverable_complete → Ops
```

---

## Approval Decision Handler

Content Claw handles War Room approval decisions:

```python
claw.handle_approval_decision(
    action_id="draft_123",
    decision="approved"  # or "edited", "blocked"
    edited_content="new content..."  # for "edited"
    reason="needs changes"  # for "blocked"
)
```

---

## Properties

| Property | Type | Access |
|----------|------|--------|
| `is_running` | `bool` | Read-only |
| `generator` | `ContentGenerator | None` | Read-only |
| `brief_manager` | `BriefManager | None` | Read-only |
| `approval_handler` | `ContentApprovalHandler | None` | Read-only |
| `publisher` | `PlatformPublisher | None` | Read-only |
| `performance_monitor` | `PerformanceMonitor | None` | Read-only |
| `scheduler` | `ContentScheduler | None` | Read-only |
| `voice_manager` | `BrandVoiceManager | None` | Read-only |

---

## Related Pages

- [[content-claw]] — This page
- [[content-generator]] — Core content generation
- [[brief-manager]] — Project brief handling
- [[content-scheduler]] — Morning planning
- [[platform-publisher]] — Publishing APIs
- [[performance-monitor]] — Post-publication tracking

---

## See Also

- `orchestrator/content/content_init.py` — Filesystem initialization
- `orchestrator/content/content_scheduler.py` — Scheduling
- `orchestrator/content/approval_handler.py` — Approval workflow
