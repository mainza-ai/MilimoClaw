# Sequencing Rules

**Summary**: Non-negotiable ordering constraints for inter-claw messages.

**Sources**:
- `raw/AGENTS.md`
- `raw/SOLO_TEMPLATE_SPEC.md`

**Last updated**: 2026-04-14

**Tags**: #coordination #sequencing #rules

---

## Overview

These eight rules apply in every deployment — solo or squad. They are non-negotiable and enforced by contract validation.

## The Eight Rules

### Rule 1: Pricing Before Brief

**OPS → FINANCE sequencing**

```
pricing_query → pricing_response → project_brief
```

`pricing_query` must be sent and `pricing_response` received BEFORE `project_brief` is sent to any creative claw. No exceptions.

**Why**: Ensures pricing is confirmed before committing to client.

**Enforcement**:
- Contract validation checks for `pricing_response` before allowing `project_brief`
- Violation logged as critical error

---

### Rule 2: Two-Stage Invoice Approval

**FINANCE invoice flow**

```
Stage 1 (REVIEW): Operator sees invoice → Approve → Moves to HOLD queue
Stage 2 (HOLD): Operator releases → Triggers Stripe transmission
```

If REVIEW approve sends invoice: **CRITICAL BUG**

**Why**: Prevents accidental invoice transmission without final approval.

**Enforcement**:
- Invoice manager has separate state machine
- No code path to Stripe except through HOLD release

---

### Rule 3: Two-Stage PR + Deploy

**BUILD approval flows (independent)**

```
PR Flow:
  REVIEW approve → HOLD queue (not merged)
  HOLD release → GitHub merge

Deploy Flow (separate):
  PR merged → Deployment staged
  HOLD release → Production deployment
```

If REVIEW approve triggers merge: **CRITICAL BUG**
If PR merge auto-deploys: **CRITICAL BUG**

**Why**: Code review and deployment are separate concerns.

**Enforcement**:
- Two separate approval queues
- Two separate HOLD states

---

### Rule 4: Client Confirmation Before Complete

**FINANCE project_complete trigger**

```
project_complete → Only after client confirms receipt
```

Not on internal completion. Not on deploy. Never earlier.

**Why**: Prevents invoicing for undelivered work.

**Enforcement**:
- `client_confirmed: true` required in payload
- Contract validation enforces

---

### Rule 5: Brief Acknowledgment Within 5 Minutes

**CONTENT brief_acknowledged**

```
project_brief received → brief_acknowledged sent within 5 min
```

**Why**: Confirms brief was received and work started.

**Enforcement**:
- Timer in Content Claw
- SLA violation logged

---

### Rule 6: Feature Brief Acknowledgment Within 10 Minutes

**BUILD feature_brief_acknowledged**

```
feature_brief received → feature_brief_acknowledged sent within 10 min
```

**Why**: Confirms Build Claw received technical requirements.

**Enforcement**:
- Timer in Build Claw
- SLA violation logged

---

### Rule 7: Analytics Query Response Within 2 Minutes

**ANALYTICS query SLA**

```
content_performance_query → Response within 2 min
behavior_query → Response within 2 min
```

Log SLA violations. Never timeout silently.

**Why**: Content and Build Claws depend on timely analytics.

**Enforcement**:
- Timer in Analytics Claw
- SLA violation logged to operational log

---

### Rule 8: Sprint Planning Timeout

**BUILD sprint planning**

```
behavior_query sent → Wait 5 min for response
If no response → Proceed with complexity scores only
```

Never block sprint planning.

**Why**: Analytics unavailability shouldn't halt development.

**Enforcement**:
- 5-minute timeout in Issue Manager
- Log timeout and proceed

---

## Sequence Diagrams

### Pricing Before Brief

```
Ops Claw          Finance Claw       Content Claw
    │                  │                  │
    │ pricing_query    │                  │
    │─────────────────►│                  │
    │                  │                  │
    │                  │ pricing_response │
    │◄─────────────────│                  │
    │                  │                  │
    │ project_brief    │                  │
    │────────────────────────────────────►│
    │                  │                  │
```

### Two-Stage Invoice

```
Finance Claw       War Room           Stripe
     │                │                 │
     │ invoice_ready  │                 │
     │───────────────►│                 │
     │                │                 │
     │                │ REVIEW approve  │
     │◄───────────────│                 │
     │                │                 │
     │ (queued in HOLD)                 │
     │                │                 │
     │                │ HOLD release    │
     │◄───────────────│                 │
     │                │                 │
     │ send invoice   │                 │
     │────────────────────────────────►│
```

---

## Violation Handling

| Rule | Violation Detection | Response |
|------|---------------------|----------|
| 1 | Contract validation | Block message, log error |
| 2 | State machine check | Log critical bug |
| 3 | State machine check | Log critical bug |
| 4 | Contract validation | Block message, log error |
| 5 | Timer expiry | Log SLA violation |
| 6 | Timer expiry | Log SLA violation |
| 7 | Timer expiry | Log SLA violation, timeout silently |
| 8 | Timer expiry | Log timeout, proceed |

---

## Related Pages

- [[message-contracts]] — Message schemas
- [[approval-thresholds]] — Approval modes
- [[war-room]] — Approval interface
- [[ops-claw]] — Rule 1 enforcement
- [[finance-claw]] — Rules 2, 4
- [[build-claw]] — Rules 3, 6, 8
- [[content-claw]] — Rule 5
- [[analytics-claw]] — Rule 7
