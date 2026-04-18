# Approval Thresholds

**Summary**: REVIEW/HOLD/AUTO approval modes for all claw actions.

**Sources**:
- `raw/AGENTS.md`
- `milimo-blueprint/templates/solo-founder.yaml`

**Last updated**: 2026-04-14

**Tags**: #coordination #approvals #war-room

---

## Overview

Every claw action has an approval threshold that determines whether it requires human intervention before execution.

## Approval Modes

| Mode | Description | War Room Queue |
|------|-------------|----------------|
| **REVIEW** | Requires operator approval before execution | Yellow priority |
| **HOLD** | Requires explicit operator release (blocks until released) | Red priority (top) |
| **AUTO** | Executed automatically, logged for morning digest | Logged only |

## Priority Order

```
🔴 HOLD — Requires explicit operator release (always on top)
🟡 REVIEW — Requires operator decision before execution
✓ AUTO — Executed, logged for morning digest
```

---

## Content Claw Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Social post draft | REVIEW | Requires approval before publishing |
| Client proposal | REVIEW | Client-facing content |
| Email campaign | REVIEW | Bulk communications |
| Brand asset usage | AUTO | Internal brand usage |
| Content calendar update | AUTO | Schedule changes |
| A/B variant | REVIEW | Multiple versions |
| Trend-reactive post | REVIEW | Time-sensitive content |

---

## Ops Claw Thresholds

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

---

## Analytics Claw Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Anomaly dispatch | AUTO | Automatic alerting |
| Weekly report generation | AUTO | Routine operation |
| Opportunity scoring | AUTO | Routine analysis |
| Query response | AUTO | SLA-driven response |

---

## Finance Claw Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Invoice generation (Stage 1) | REVIEW | Review content only |
| Invoice send (Stage 2) | HOLD | ONLY trigger for Stripe transmission |
| Expense log entry | AUTO | Routine logging |
| Overdue payment alert (first) | REVIEW | First escalation |
| Overdue payment alert (repeat) | HOLD | Repeated escalation |
| Margin compression alert | REVIEW | Profitability warning |
| Rate optimization advisory | REVIEW | Pricing suggestions |
| Tax quarterly summary | AUTO | Routine reporting |

---

## Build Claw Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Sprint plan | REVIEW | Planning approval |
| PR open | REVIEW | Code review |
| PR merge | HOLD | Separate from deploy |
| Production deploy | HOLD | Separate from PR HOLD |
| Issue triage and scoring | AUTO | Routine analysis |
| Dependency audit | AUTO | Weekly security check |
| Error pattern detection | REVIEW | Error analysis |
| Auto-drafted patch PR | REVIEW | Generated code |
| Cost alert | REVIEW | Budget warning |
| Devlog draft | AUTO | Weekly documentation |
| Changelog update | AUTO | Routine documentation |

---

## Two-Stage Approval Systems

### Finance Invoice

```
Stage 1: REVIEW (view invoice)
    ↓ Approved
Stage 2: HOLD (authorize transmission)
    ↓ Released
Stripe transmission
```

### Build PR + Deploy (Independent)

```
PR Flow:
Stage 1: REVIEW (code review)
    ↓ Approved
Stage 2: HOLD (authorize merge)
    ↓ Released
GitHub merge

Deploy Flow (separate):
PR merged automatically stages deployment
    ↓
HOLD (authorize deploy)
    ↓ Released
Production deployment
```

---

## War Room Interface

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| A | Approve current REVIEW |
| B | Block current item |
| E | Edit inline |
| R | Release current HOLD |
| D | Toggle morning/evening digest |
| F | Toggle Deep Work Mode |
| H | Help overlay |
| Q | Quit |

### Daily Schedule

- **07:00** — Morning brief: overnight AUTO log + pending queue summary
- **20:00** — Evening wrap: today's activity + tomorrow's queue preview

### Target

**Solo operator**: Full War Room review in under 15 minutes per day.

---

## Related Pages

- [[war-room]] — TUI interface
- [[sequencing-rules]] — Ordering constraints
- [[message-contracts]] — Message schemas
- [[content-claw]] — Content thresholds
- [[ops-claw]] — Ops thresholds
- [[finance-claw]] — Finance thresholds
- [[build-claw]] — Build thresholds
