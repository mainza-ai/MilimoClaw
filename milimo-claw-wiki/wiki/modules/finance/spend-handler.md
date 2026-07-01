# Spend Approval Handler

**Summary**: Mirror of `FinanceApprovalHandler` for the outbound direction of money — agent-initiated purchases via Stripe Link CLI.

**Sources**:
- `milimo-core/src/milimo_core/finance/spend_handler.py`
- `milimo-blueprint/orchestrator/finance/spend_warroom_bridge.py`

**Last updated**: 2026-06-30

**Tags**: #module #finance #spend #stripe #approval

---

## Overview

`SpendApprovalHandler` is the payables counterpart to `FinanceApprovalHandler` (receivables). While `FinanceApprovalHandler` governs invoices MilimoClaw sends and gets paid for, `SpendApprovalHandler` governs purchases a claw wants to make on the operator's behalf — buying API credit bundles, provisioning SaaS dependencies, paying per-call 402 APIs, etc.

Implements the NVIDIA x Stripe x Nous Research integration from the Hermes Agent Accelerated Business Hackathon (2026-06).

---

## Two-Stage Spend Approval

Same two-stage shape as invoice approval, opposite direction:

```
Stage 1 — REVIEW:
  Agent wants to buy X for $Y, because Z.
  Approving Stage 1 does NOT spend. It moves the request to HOLD only.

Stage 2 — HOLD release:
  Invokes `link-cli spend-request create --request-approval`.
  This blocks on an independent second approval in the user's Stripe Link app.
```

**Two independent human gates** sit between the agent and the charge:
1. War Room HOLD release — operator explicitly releases the spend hold
2. Stripe Link in-app approval — Hermes cannot self-approve this step either

---

## Daily Spend Cap

A safety cap (`MILIMO_DAILY_SPEND_CAP_CENTS`, default $100/10,000¢) auto-blocks any request exceeding the limit. Auto-blocked requests never reach the War Room and are logged immediately.

```python
import os
cap = int(os.environ.get("MILIMO_DAILY_SPEND_CAP_CENTS", "10000"))  # $100
```

---

## Spend Request Flow

```
Any claw sends a spend_request message
       ↓
SpendApprovalHandler.queue_spend_review()
       ↓
Daily cap check — auto-blocked if exceeded
       ↓
Queued in War Room as spend_review (REVIEW priority)
       ↓
Operator presses A → approve_review()
       ↓
Moves to HOLD — new spend_hold action appears in War Room (HOLD priority)
       ↓
Operator presses R → release_hold()
       ↓
SpendApprovalHandler.handle_hold_release() invokes link-cli
       ↓
link-cli blocks on Stripe Link app approval (user's phone)
       ↓
Charge completes or is denied/timed out
```

---

## Spend War Room Bridge

`SpendWarRoomBridge` connects `SpendApprovalHandler` to the existing `SoloWarRoom` action queue. Claws call the bridge instead of touching `SpendApprovalHandler` or `link-cli` directly:

```python
bridge = SpendWarRoomBridge(spend_handler, solo_warroom)
wr_action_id = bridge.submit_spend_request(request)
bridge.approve_review(wr_action_id)
action, request = bridge.release_hold(hold_action_id)
if request.status == "released":
    print("Charge completed")
```

---

## Inbound Message Handlers

| Message Type | Handler | Action |
|--------------|---------|--------|
| `spend_request` | `SpendApprovalHandler.queue_spend_review()` | Queue a purchase for review |
| `spend_review_decision` | `approve`/`edit`/`block` | Stage 1 decision |
| `spend_hold_decision` | `release`/`cancel` | Stage 2 decision |

---

## Logging

Every decision is written to `decisions.log` (same file as `FinanceApprovalHandler`), with the same format and stage vocabulary:

```json
{"action_id": "spend-review-abc123", "stage": "review", "action_type": "approve", ...}
{"action_id": "spend-hold-abc123", "stage": "hold", "action_type": "release", ...}
```

A dedicated `agent-spend.log` records completed purchase details:

```json
{"spend_id": "abc123", "claw": "build", "merchant_name": "Neon", "amount_cents": 5000, ...}
```

---

## Approval Modes

Configured in `solo-founder.yaml`:

```yaml
finance:
  spend_review: REVIEW   # agent wants to buy something — you see it first
  spend_hold: HOLD       # you explicitly release the charge (Link confirms too)
```

---

## Related Pages

- [[finance-claw]] — Finance claw main entry point
- [[approval-handler]] — Receivables approval (two-stage invoices)
- [[approval-thresholds]] — REVIEW/HOLD/AUTO rules
- [[war-room]] — TUI for pending actions
- [[message-contracts]] — Message types

---

## See Also

- `milimo-core/src/milimo_core/finance/spend_handler.py` — Implementation
- `milimo-blueprint/orchestrator/finance/spend_warroom_bridge.py` — War Room bridge
- `milimo-blueprint/templates/solo-founder.yaml` — Approval mode config
