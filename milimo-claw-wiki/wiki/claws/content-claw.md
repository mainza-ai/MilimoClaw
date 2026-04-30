# Content Claw

**Summary**: Creative department that generates all content autonomously — posts, copy, campaigns, and proposals.

**Sources**:
- `raw/CONTENT_CLAW_SPEC.md`
- `milimo-blueprint/roles/content-claw.yaml`

**Last updated**: 2026-04-28

**Tags**: #claw #content

---

## Role

The Content Claw is the **creative department** of MilimoClaw. It generates all content autonomously including social posts, copy, campaigns, proposals, and content calendars.

## Sandbox

**Mount**: `/sandbox/.openclaw-data/milimo/claws/content`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/.openclaw-data/milimo/claws/content/drafts/` | Draft content | Read-write |
| `/sandbox/.openclaw-data/milimo/claws/content/brand/` | Brand assets, style guides | Read-write |
| `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` | Intelligence reports | Read-only |

## What It Does

- Generates social posts, copy, campaigns, proposals, and content calendars
- Applies a pipeline of self-evolved tools to every draft before surfacing
- Queries Analytics Claw weekly for top-performing content patterns
- Schedules approved content via platform publishing APIs
- Monitors post-publication performance and sends signals to Analytics Claw
- Sends `brief_acknowledged` within 5 minutes of every project brief received

## What It Cannot Do

- Read `/sandbox/.openclaw-data/milimo/claws/ops`, `/sandbox/.openclaw-data/milimo/claws/finance`, or `/sandbox/.openclaw-data/milimo/claws/build`
- Publish anything without operator REVIEW approval in the War Room
- Make inference calls that bypass the privacy router

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Social post draft | REVIEW | Requires approval before publishing |
| Client proposal | REVIEW | Client-facing content |
| Email campaign | REVIEW | Bulk communications |
| Brand asset usage | AUTO | Internal brand usage |
| Content calendar update | AUTO | Schedule changes |
| A/B variant | REVIEW | Multiple versions |
| Trend-reactive post | REVIEW | Time-sensitive content |

## Inter-Claw Messages

### Sent

| Message Type | To | Trigger | SLA |
|--------------|-----|---------|-----|
| `draft_ready` | War Room | Draft ready for review | Immediate |
| `content_performance_query` | Analytics | Monday 06:00 + on demand | 2-min response |
| `performance_signal` | Analytics | After every published post | Immediate |
| `brief_acknowledged` | Ops | Within 5 min of project_brief | 5 minutes |
| `deliverable_complete` | Ops | All deliverables published | Immediate |

### Received

| Message Type | From | Handler |
|--------------|------|---------|
| `project_brief` | Ops | Validate and acknowledge, begin generation |
| `performance_intel` | Analytics | Incorporate into content strategy |
| `client_health_signal` | Analytics | Adjust tone/approach for client |
| `revision_request` | Ops | Revise content based on feedback |
| `assistant_query` | Assistant | Return status and state |
| `assistant_task` | Assistant | Execute content-related tasks |

## Key Modules

- [[content-init]] — Filesystem initialization and validation
- [[content-generator]] — Core content generation engine
- [[brief-manager]] — Project brief handling and acknowledgment
- [[brand-voice]] — Brand voice profile management
- [[platform-publisher]] — Platform-specific publishing APIs
- [[content-scheduler]] — Content calendar and scheduling
- [[performance-monitor]] — Post-publication performance tracking
- [[approval-handler]] — War Room approval processing

## Evolution Tools

Tools that emerge autonomously over time:

```
Style descriptor → Tone classifier → Approval predictor →
Platform calibrator → Timing optimizer → A/B variant engine →
Client voice adapter → Trend injector
```

## Evolution Schedule

**Sunday 02:05** — Content Claw evolution cycle

Runs after Analytics generates weekly intelligence report.

## Spec Document

Full specification: `raw/CONTENT_CLAW_SPEC.md`

## Related Pages

- [[message-contracts]] — Message schemas
- [[approval-thresholds]] — Approval rules
- [[sandbox-isolation]] — Isolation model
- [[analytics-claw]] — Receives performance signals
- [[ops-claw]] — Sends/receives project briefs

## See Also

- Implementation prompt: `milimo-claw-docs/prompts/CONTENT_CLAW_IMPLEMENTATION_PROMPT.md`
- Policy: `milimo-blueprint/policies/content-sandbox.yaml`
- Tests: `milimo-blueprint/tests/test_content_claw*.py`
