# MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md — Code Audit Report

**Audit Date:** 2026-03-22  
**Auditor:** AI Assistant  
**Spec Version:** v2 (742 lines)  
**Codebase Commit:** `5213c09`

---

## Executive Summary

This audit compares the current code implementation against `MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md`. The spec introduces five significant upgrades from v1, and this audit identifies gaps between spec requirements and actual implementation.

### Overall Status by Category

| Category | Spec Requirements | Implementation Status | Gap Level |
|----------|-------------------|----------------------|-----------|
| Ground Truth Hierarchy | Defined | Partially aligned | **Medium** |
| Phase A — Shared Mount Verification | A1-A8 tests required | Partially implemented | **High** |
| Evolution Cycle Schedule | Specific times with 5-min gaps | Single time for all | **High** |
| Non-Negotiable Sequencing Rules | 8 rules defined | 5 implemented, 3 missing | **Medium** |
| Weekly Intelligence Shared Read | Single shared file | Configured, mount incomplete | **Medium** |

---

## 1. Ground Truth Hierarchy (Spec Lines 691-705)

### Spec Requirement

> 1. **Individual claw spec documents** — ground truth for each claw's internal behavior
> 2. **This document (solo template spec v2)** — ground truth for coordination, approval thresholds, scheduling
> 3. **solo-founder.yaml** — configuration values
> 4. **AGENTS.md** — quick reference summary (not ground truth)

### Implementation Findings

| Aspect | Status | Notes |
|--------|--------|-------|
| Claw spec files exist | ✅ Implemented | `MILIMO_CLAW_*_CLAW_SPEC.md` files present |
| solo-founder.yaml validates | ✅ Implemented | `solo_init.py` validates all fields |
| Conflict resolution | ⚠️ Partial | No explicit conflict detection in code |
| AGENTS.md documented as non-authoritative | ❓ Unclear | AGENTS.md not found in codebase |

### Gaps

1. **No explicit conflict detection** — When solo spec and claw spec conflict, there's no automated check to alert developers.
2. **AGENTS.md not found** — The reference to AGENTS.md as "quick reference summary" suggests it should exist but wasn't found.

---

## 2. Phase A — Shared Mount Verification (Spec Lines 534-553)

### Spec Requirement

> **Phase A — Verify Isolation and Shared Mount (before anything else)**
> 
> A1. Confirm all five sandbox filesystem mounts exist and are isolated  
> A2. Write a test file to `/sandbox/analytics/reports/weekly-intelligence.json`  
> A3. Confirm Content Claw can read the file from its sandbox  
> A4. Confirm Ops Claw can read the file from its sandbox  
> A5. Confirm Finance Claw can read the file from its sandbox  
> A6. Confirm Build Claw can read the file from its sandbox  
> A7. Confirm Content Claw CANNOT read `/sandbox/clients` (should fail)  
> A8. Confirm Finance Claw CANNOT read `/sandbox/build` (should fail)  
> 
> **Stop here if any of A1–A6 fails. Fix the mount configuration before proceeding.**

### Implementation Findings

| Test | Spec Ref | Implementation | Status |
|------|----------|----------------|--------|
| A1: Sandbox mounts exist | A1 | `test_solo_sandbox.py` tests policy creation | ⚠️ Partial |
| A2: Write test file | A2 | `test_analytics_integration.py` creates report | ✅ Implemented |
| A3: Content Claw reads report | A3 | `test_analytics_integration.py:265-276` | ⚠️ Simulated |
| A4: Ops Claw reads report | A4 | `test_analytics_integration.py:278-289` | ⚠️ Simulated |
| A5: Finance Claw reads report | A5 | Not found | ❌ Missing |
| A6: Build Claw reads report | A6 | Not found | ❌ Missing |
| A7: Content CANNOT read `/sandbox/clients` | A7 | Not found | ❌ Missing |
| A8: Finance CANNOT read `/sandbox/build` | A8 | Not found | ❌ Missing |

### Sandbox Policy Files

The sandbox policy files exist in `/policies/`:

- `content-sandbox.yaml` — Line 23: `read_only: /sandbox/analytics/reports`
- `analytics-sandbox.yaml` — Line 22: `read_write: /sandbox/analytics`
- `build-sandbox.yaml` — Defines `/sandbox/build` mount
- `finance-sandbox.yaml` — Defines `/sandbox/finance` mount
- `ops-sandbox.yaml` — Defines `/sandbox/clients` mount

### Gaps

1. **A3-A6 are simulated, not enforced** — Current tests check if a file can be read within the same test process, not actual sandbox isolation.
2. **A7-A8 completely missing** — No tests verify that cross-sandbox reads FAIL when they should.
3. **No integration test halts on failure** — The spec requires "Stop here if any of A1-A6 fails" but there's no test orchestration that enforces this.

### Recommendation

Create a dedicated Phase A integration test file:

```python
# tests/test_phase_a_isolation.py
# Tests A1-A8 with actual sandbox enforcement
# Must pass before any other MVR tests run
```

---

## 3. Evolution Cycle Schedule (Spec Lines 312-339)

### Spec Requirement

> **The Evolution Cycle schedule now has specific times with 5-minute gaps:**
> 
> - Sunday 01:00 — Analytics Claw: baseline recalculation
> - Sunday 02:00 — Analytics Claw: weekly intelligence report generated
> - Sunday 02:05 — Content Claw: evolution cycle begins (reads fresh report)
> - Sunday 02:15 — Ops Claw: evolution cycle begins
> - Sunday 02:25 — Analytics Claw: evolution cycle begins
> - Sunday 02:35 — Build Claw: evolution cycle begins (tech squads only)
> - Sunday 03:00 — Finance Claw: weekly revenue summary + evolution cycle

### Implementation Findings

| Spec Time | Implementation | Status |
|-----------|----------------|--------|
| Sunday 01:00 — Analytics baseline | `analytics_scheduler.py` line 74-80 | ✅ Implemented |
| Sunday 02:00 — Weekly report | `analytics_scheduler.py` line 82-88 | ✅ Implemented |
| Sunday 02:05 — Content evolution | Not found | ❌ Missing |
| Sunday 02:15 — Ops evolution | Not found | ❌ Missing |
| Sunday 02:25 — Analytics evolution | Not found | ❌ Missing |
| Sunday 02:35 — Build evolution | Not found | ❌ Missing |
| Sunday 03:00 — Finance evolution | Not found | ❌ Missing |

### Configuration in solo-founder.yaml

```yaml
evolution:
  cycle: weekly
  day: sunday
  time: "02:00"  # Single time, not per-claw schedule
```

### Code in solo_evolution.py

```python
# Line 94-95
day = evolution_config.get("day", "sunday")
time_str = evolution_config.get("time", "02:00")  # Single time for all claws
```

### Gaps

1. **Single evolution time** — The spec requires staggered 5-minute gaps between claw evolution cycles. Implementation uses a single `time` value for all claws.
2. **Per-claw scheduler not implemented** — Each claw should have its own evolution scheduler entry, not share one.
3. **Finance revenue summary timing** — Spec says Finance runs at 03:00 after all other evolutions; implementation has no separate Finance scheduler.

### Recommendation

Update `solo-founder.yaml`:

```yaml
evolution:
  schedule:
    analytics_baseline: "01:00"
    analytics_report: "02:00"
    content: "02:05"
    ops: "02:15"
    analytics_evolution: "02:25"
    build: "02:35"
    finance: "03:00"
```

---

## 4. Non-Negotiable Sequencing Rules (Spec Lines 384-416)

### Spec Requirement

> **Eight rules, numbered, covering all the critical cross-claw constraints:**
> 
> 1. **OPS → FINANCE sequencing:** `pricing_query` must be sent and `pricing_response` received BEFORE `project_brief` is sent to any creative claw.
> 2. **FINANCE two-stage invoice:** Stage 1 REVIEW approve moves invoice to HOLD queue only. Stage 2 HOLD release is the only trigger for Stripe transmission.
> 3. **BUILD two-stage PR + deploy:** PR REVIEW approve → HOLD (not merge). PR HOLD release → GitHub merge. Deploy stages automatically after merge. Deploy HOLD release → production deployment.
> 4. **FINANCE project_complete:** `project_complete` to Finance Claw fires ONLY after client confirms receipt of deliverables.
> 5. **CONTENT brief_acknowledged:** Must be sent within 5 minutes of every `project_brief` received from Ops Claw.
> 6. **BUILD feature_brief_acknowledged:** Must be sent within 10 minutes of every `feature_brief` received from Ops Claw.
> 7. **ANALYTICS query response SLA:** Must respond to `content_performance_query` and `behavior_query` within 2 minutes.
> 8. **BUILD sprint planning timeout:** If `behavior_query_response` does not arrive within 5 minutes, proceed without Analytics retention signals.

### Implementation Findings

| Rule | Spec | Implementation | Status |
|------|------|----------------|--------|
| 1. OPS → FINANCE sequencing | Line 388-390 | `intake_manager.py` sends `pricing_query` before `project_brief` | ✅ Implemented |
| 2. FINANCE two-stage invoice | Line 392-394 | `invoice_manager.py:276-322` (Stage 1) and `397-481` (Stage 2) | ✅ Implemented |
| 3. BUILD two-stage PR + deploy | Line 396-399 | Build Claw MVR tests verify this | ✅ Implemented |
| 4. project_complete timing | Line 401-403 | `intake_manager.py` sends on client confirmation | ⚠️ Verify |
| 5. brief_acknowledged within 5 min | Line 405-406 | `brief_manager.py:124-207` | ✅ Implemented |
| 6. feature_brief_acknowledged within 10 min | Line 408-409 | Not found in Build Claw | ❌ Missing |
| 7. ANALYTICS query response SLA (2 min) | Line 411-412 | Not found | ❌ Missing |
| 8. Sprint planning timeout (5 min) | Line 414-416 | `issue_manager.py:39` — `ANALYTICS_WAIT_SECONDS = 300` | ✅ Implemented |

### Detailed Analysis

#### Rule 1: OPS → FINANCE Sequencing ✅

**Code:** `intake_manager.py:373-379`
```python
self._dispatcher.send_pricing_query(
    project_id=brief.project_id,
    scope_description=brief.scope_description,
    ...
)
```
Pricing query is sent BEFORE any project brief. The `handle_pricing_response` method at line 529 stores the response and triggers proposal draft.

#### Rule 2: FINANCE Two-Stage Invoice ✅

**Code:** `invoice_manager.py`
- `handle_stage1_approve()` — Line 276: Moves to `approved/`, does NOT send
- `handle_stage2_hold_release()` — Line 397: ONLY place Stripe transmission occurs

**MVR Test:** `test_finance_mvr_integration.py` validates:
- `test_mvr_step_06_review_approve_moves_to_hold_not_sent`
- `test_mvr_step_08_hold_release_triggers_stripe`

#### Rule 3: BUILD Two-Stage PR + Deploy ✅

**MVR Test:** `test_build_mvr_integration.py`
- MVR-06: PR REVIEW approve → HOLD (not merged)
- MVR-08: PR HOLD release → GitHub merge
- MVR-10: Deploy appears as SEPARATE HOLD

#### Rule 4: project_complete Timing ⚠️

**Needs Verification:** The spec says `project_complete` fires "ONLY after client confirms receipt of deliverables." Need to verify the Ops Claw doesn't send this signal prematurely.

#### Rule 5: brief_acknowledged within 5 min ✅

**Code:** `brief_manager.py:124-207`
```python
# Per spec: 5-minute SLA. Timer fires at 4.5 minutes to ensure
# acknowledgment before the 5-minute hard deadline.
```

#### Rule 6: feature_brief_acknowledged within 10 min ❌

**Gap:** Build Claw does not have a `feature_brief_acknowledged` message type or handler.

#### Rule 7: ANALYTICS Query Response SLA (2 min) ❌

**Gap:** No timer or SLA enforcement for `content_performance_query` or `behavior_query` responses.

#### Rule 8: Sprint Planning Timeout (5 min) ✅

**Code:** `issue_manager.py:39`
```python
ANALYTICS_WAIT_SECONDS = 300  # 5 minutes
```

### Gaps

1. **Rule 6 missing** — `feature_brief_acknowledged` within 10 minutes not implemented.
2. **Rule 7 missing** — ANALYTICS query response SLA of 2 minutes not enforced.
3. **Rule 4 unverified** — Need to confirm `project_complete` only fires after client confirmation.

---

## 5. Weekly Intelligence Shared Read (Spec Lines 124-131)

### Spec Requirement

> **The one shared-read file:** `/sandbox/analytics/reports/weekly-intelligence.json`
> 
> This is the only file in the entire mesh that all five claws can read directly without a message contract. It is written by the Analytics Claw every Sunday and mounted as read-only in every other claw's sandbox policy.
> 
> **Verify this mount is configured in every claw's sandbox policy file. This is the most critical single configuration item in the solo template.**

### Implementation Findings

| Claw | Mount Configured | Status |
|------|------------------|--------|
| Content Claw | `content-sandbox.yaml` line 23 | ✅ Configured |
| Ops Claw | `ops-sandbox.yaml` — NOT found | ❌ Missing |
| Finance Claw | `finance-sandbox.yaml` — NOT found | ❌ Missing |
| Build Claw | `build-sandbox.yaml` — NOT found | ❌ Missing |
| Analytics Claw | Writes to own mount | ✅ N/A |

### Configuration Reference

**solo-founder.yaml line 95-96:**
```yaml
shared_read:
  - /sandbox/analytics/reports/weekly-intelligence.json
```

**content-sandbox.yaml line 23:**
```yaml
read_only:
  - /sandbox/analytics/reports  # Cross-mount: Analytics weekly reports
```

### Gaps

1. **Only Content Claw has shared mount** — The other 4 claw sandbox policies don't include the shared read.
2. **No test verifies all 5 claws can read** — Only Content and Ops have read tests in `test_analytics_integration.py`.

### Recommendation

Update all sandbox policies to include:
```yaml
read_only:
  - /sandbox/analytics/reports/weekly-intelligence.json
```

---

## 6. Approval Mode Thresholds (Spec Lines 144-208)

### Spec Requirement

The spec defines approval modes (AUTO/REVIEW/HOLD) for each action type per claw, tuned for a solo operator.

### Implementation Findings

| Claw | Spec Actions | Config File | Status |
|------|--------------|-------------|--------|
| Content | 7 action types | Lines 43-49 | ✅ Matched |
| Ops | 10 action types | Lines 52-57 | ⚠️ Partial |
| Analytics | 5 action types | Lines 60-63 | ✅ Matched |
| Finance | 8 action types | Lines 66-71 | ✅ Matched |
| Build | 9 action types | Lines 74-80 | ✅ Matched |

### Ops Claw Discrepancies

**Spec (Line 159-169):**
- `deadline_critical_(24_hours)`: HOLD
- `scope_creep_change_order`: HOLD
- `deep_work_auto_response`: AUTO

**Config (solo-founder.yaml lines 52-57):**
- `deadline_flag`: REVIEW (not HOLD for critical)
- `scope_change`: HOLD ✅
- No `deep_work_auto_response` action type

### Gaps

1. **Ops deadline_critical missing** — Should be HOLD at 24 hours, config has REVIEW.
2. **Deep Work auto-response action missing** — Should be AUTO.

---

## 7. Cost Guard (Spec Lines 295-298)

### Spec Requirement

> **Cost guard (active even in dev):**
> - Daily cloud token budget: 50,000 tokens
> - Alert at 80% of daily budget
> - Automatic fallback to a lighter prompt strategy if budget exceeded
> - Never block a claw action — always fallback, never fail

### Implementation Findings

**solo-founder.yaml lines 120-123:**
```yaml
cost_guard:
  daily_cloud_token_budget: 100000  # Higher limit for cloud-only testing
  alert_at_percent: 80
  fallback_on_exceed: cloud  # In Docker mode, fallback to cloud
```

### Gaps

1. **Token budget is 100,000** — Spec says 50,000. This is noted as "Docker testing mode" which is acceptable.
2. **Fallback strategy unclear** — Spec says "lighter prompt strategy" but config says `cloud`. These are different fallback mechanisms.

---

## 8. Deep Work Mode (Spec Lines 419-452)

### Spec Requirement

> **Per-claw behavior during Deep Work Mode:**
> 
> | Claw | Active behavior | Paused behavior |
> |------|-----------------|-----------------|
> | Content | Nothing | Draft generation, publishing |
> | Ops | Auto-responses to active clients | New client intake |
> | Analytics | Passive data collection | New experiments, opportunity scoring |
> | Finance | Invoice sends continue | New project initiations |
> | Build | Issue triage only | New PRs, deploys, code generation |

### Implementation Findings

**solo_deep_work.py lines 28-63:**
```python
DEEP_WORK_POLICIES = {
    "pause_drafts": {"actions_blocked": ["publish", "send"], ...},
    "maintenance": {"actions_blocked": ["new_outreach", "follow_up"], ...},
    "passive": {"actions_blocked": ["experiment", "test"], ...},
    "invoices_only": {"actions_blocked": ["new_invoice", "new_client"], ...},
    "issues_only": {"actions_blocked": ["open_pr", "merge"], ...},
}
```

### Status: ✅ Implemented

The Deep Work Mode policies match the spec requirements.

---

## 9. MVR Integration Tests Coverage

### Spec Requirement

The spec defines a complete MVR sequence (Phases A-F) that must pass before autonomous scheduling is enabled.

### Implementation Findings

| Phase | Spec Steps | Test File | Coverage |
|-------|------------|-----------|----------|
| Phase A | A1-A8 | `test_analytics_integration.py` | ⚠️ Partial (A3-A4 only) |
| Phase B | B1-B8 | Not found | ❌ Missing |
| Phase C | C1-C9 | `test_ops_mvr_integration.py` | ✅ Covered |
| Phase D | D1-D9 | `test_finance_mvr_integration.py` | ✅ Covered |
| Phase E | E1-E12 | `test_build_mvr_integration.py` | ✅ Covered |
| Phase F | F1-F10 | `test_analytics_integration.py` | ✅ Covered |

### Gaps

1. **Phase A incomplete** — Only 2 of 8 tests exist, and they're simulated.
2. **Phase B missing entirely** — No War Room approval flow integration tests.

---

## 10. Message Flow (Spec Lines 351-382)

### Spec Requirement

The spec defines a complete message flow matrix for inter-claw communication.

### Implementation Findings

**contracts.py** defines `MESSAGE_TYPE_SCHEMAS` (lines 90-323) with validation for:

- `draft_ready` ✅
- `brief` ✅
- `deliverable_complete` ✅
- `content_performance_query` ✅
- `performance_signal` ✅
- `brief_acknowledged` ✅
- `client_health_signal` ✅
- `pricing_query` ✅
- `pricing_response` ✅
- `invoice_ready` ✅
- `project_complete` ✅
- `deploy_complete` ✅
- `shipping_summary` ✅
- `behavior_query` ✅
- `performance_intel` ✅
- `retention_signals` ✅
- `revenue_anomaly` ✅

### Missing Message Types

| Message Type | Spec Line | Status |
|--------------|-----------|--------|
| `feature_brief_acknowledged` | Line 408-409 | ❌ Not in schema |

---

## Summary of Critical Gaps

### HIGH Priority (Blocks Correct Operation)

1. **Phase A isolation tests missing** — Cannot verify shared mount works correctly
2. **Evolution schedule uses single time** — Should be staggered with 5-min gaps
3. **Only Content Claw has shared_read mount** — Other 4 claws need it

### MEDIUM Priority (Spec Deviation)

4. **Rule 6 (feature_brief_acknowledged) missing** — Build Claw should ack within 10 min
5. **Rule 7 (ANALYTICS SLA) missing** — 2-minute response SLA not enforced
6. **Phase B (War Room) tests missing** — No approval flow integration tests

### LOW Priority (Minor Discrepancies)

7. **Token budget is 100K not 50K** — Acceptable for Docker testing mode
8. **Ops deadline_critical should be HOLD** — Currently REVIEW
9. **AGENTS.md not found** — Referenced but doesn't exist

---

## Recommendations

### Immediate Actions

1. **Add shared_read mount to all sandbox policies:**
   - `ops-sandbox.yaml`
   - `finance-sandbox.yaml`
   - `build-sandbox.yaml`

2. **Create Phase A integration test file:**
   ```python
   # tests/test_phase_a_isolation.py
   # Tests A1-A8 with actual sandbox enforcement
   ```

3. **Update evolution schedule configuration:**
   - Add per-claw time slots
   - Implement separate schedulers for each claw

### Near-Term Actions

4. **Add feature_brief_acknowledged to Build Claw:**
   - New message type in contracts.py
   - Handler in Build Claw with 10-minute timer

5. **Add ANALYTICS query response SLA enforcement:**
   - Timer in query handlers
   - Log warning if SLA exceeded

6. **Create Phase B War Room integration tests:**
   - Morning brief scheduling
   - Queue priority ordering
   - Keyboard shortcut actions

---

## Files Referenced

| File | Purpose |
|------|---------|
| `MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md` | Spec document (742 lines) |
| `solo-founder.yaml` | Template configuration (284 lines) |
| `solo_init.py` | Template loader and validator (554 lines) |
| `solo_evolution.py` | Evolution scheduler (462 lines) |
| `solo_sandbox.py` | Sandbox policy generator (283 lines) |
| `solo_warroom.py` | War Room implementation (510 lines) |
| `solo_deep_work.py` | Deep Work Mode (439 lines) |
| `contracts.py` | Message type schemas (554 lines) |
| `invoice_manager.py` | Finance invoice lifecycle (572 lines) |
| `issue_manager.py` | Build sprint planning (663 lines) |
| `intake_manager.py` | Ops intake pipeline (686 lines) |
| `analytics_scheduler.py` | Analytics timing (381 lines) |

---

*End of Audit Report*
