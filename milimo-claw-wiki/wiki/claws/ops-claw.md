# Ops Claw

**Summary**: Account manager that owns the full client lifecycle — intake, scoping, delivery, and close.

**Sources**:
- `raw/OPS_CLAW_SPEC.md`
- `milimo-blueprint/roles/ops-claw.yaml`

**Last updated**: 2026-04-28

**Tags**: #claw #ops

---

## Role

The Ops Claw is the **account manager and project manager** of MilimoClaw. It owns the full client lifecycle from intake to close.

## Sandbox

**Mount**: `/sandbox/.openclaw-data/milimo/claws/ops`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/.openclaw-data/milimo/claws/ops/` | Client records, project histories | Read-write |
| `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` | Intelligence reports | Read-only |

## What It Does

- Intercepts and triages all incoming client inquiries (budget 40%, scope 30%, fit 30%)
- Manages the full project lifecycle: intake → scoping → delivery → close
- Runs deadline risk prediction daily for all active projects
- Detects scope creep and drafts change orders (always HOLD — never auto)
- Scores client relationship health weekly and sends signals to Analytics Claw
- Always queries Finance Claw for pricing before sending any proposal

## What It Cannot Do

- Read `/sandbox/.openclaw-data/milimo/claws/finance`, `/sandbox/.openclaw-data/milimo/claws/content`, or `/sandbox/.openclaw-data/milimo/claws/build`
- Send any client-facing message without operator REVIEW approval
- Send a `project_brief` before receiving a `pricing_response` from Finance Claw
- Generate or send invoices — Finance Claw only
- Send `project_complete` before client confirms receipt of deliverables

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| New client welcome message | REVIEW | First impression |
| Intake questionnaire | REVIEW | Client interaction |
| Client proposal | REVIEW | Commercial content |
| Project brief to creative claws | REVIEW | Initiates work |
| Routine client update | AUTO | Status communications |
| Deadline risk flag (5+ days) | REVIEW | Early warning |
| Deadline critical (24 hours) | HOLD | Blocks until released |
| Scope creep change order | HOLD | Always requires release |
| Client delivery message | REVIEW | Deliverable handoff |
| Deep Work auto-response | AUTO | Focused sprint mode |

## Inter-Claw Messages

### Sent

| Message Type | To | Trigger | SLA |
|--------------|-----|---------|-----|
| `project_brief` | Content/Build | New project scoped | After pricing_response |
| `feature_brief` | Build | New technical feature | After pricing_response |
| `pricing_query` | Finance | Before any proposal | 10-min response |
| `project_complete` | Finance | Client confirms delivery | Immediate |
| `client_health_signal` | Analytics | Weekly | Sunday |
| `client_onboarded` | Analytics | New client onboarded | Immediate |

### Received

| Message Type | From | Handler |
|--------------|------|---------|
| `deliverable_complete` | Content | Mark project deliverable complete |
| `deploy_complete` | Build | Mark deployment complete |
| `pricing_response` | Finance | Include in proposal |
| `invoice_ready` | Finance | Invoice ready for review |
| `payment_overdue` | Finance | Escalate to client |
| `feature_brief_acknowledged` | Build | Confirm feature brief received |
| `client_health_alert` | Analytics | Take action on health score |
| `assistant_query` | Assistant | Return status and state |
| `assistant_task` | Assistant | Execute ops-related tasks |

## Sequencing Rules

### Non-Negotiable: Pricing Before Brief

```
pricing_query → pricing_response → project_brief
```

`pricing_query` must be sent and `pricing_response` received BEFORE `project_brief` is sent to any creative claw. No exceptions.

### Non-Negotiable: Client Confirmation Before Complete

`project_complete` fires only after client confirms receipt — not on internal completion, not on deploy.

## Key Modules

- [[ops-init]] — Filesystem initialization
- [[intake-manager]] — Client inquiry triage
- [[project-manager]] — Project lifecycle management
- [[comms-manager]] — Client communications
- [[scope-monitor]] — Scope creep detection
- [[health-scorer]] — Client relationship health
- [[approval-handler]] — War Room approval processing
- [[ops-scheduler]] — Scheduled tasks (deadline checks, health scores)
- [[signal-dispatcher]] — Inter-claw message sending

## Evolution Tools

Tools that emerge autonomously over time:

```
Client triage scorer → Brief quality checker → Deadline risk predictor →
Communication tone calibrator → Scope creep detector v2 →
Relationship health scorer v2
```

## Evolution Schedule

**Sunday 02:15** — Ops Claw evolution cycle

Runs after Content Claw evolution.

## Spec Document

Full specification: `raw/OPS_CLAW_SPEC.md`

## Related Pages

- [[message-contracts]] — Message schemas
- [[sequencing-rules]] — Ordering constraints
- [[approval-thresholds]] — Approval rules
- [[finance-claw]] — Pricing queries and invoices
- [[analytics-claw]] — Health signals

## See Also

- Implementation prompt: `milimo-claw-docs/prompts/OPS_CLAW_IMPLEMENTATION_PROMPT.md`
- Policy: `milimo-blueprint/policies/ops-sandbox.yaml`
- Tests: `milimo-blueprint/tests/test_ops_claw*.py`
