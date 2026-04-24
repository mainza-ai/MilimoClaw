> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — SOLO TEMPLATE V2 AUDIT REMEDIATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. SOLO_TEMPLATE_SPEC_V2_AUDIT.md          (the gap analysis)
#   2. MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md    (the ground truth spec)
#   3. solo-founder.yaml                        (template config — EXISTS)
#   4. solo_evolution.py                        (evolution scheduler — EXISTS)
#   5. solo_sandbox.py                          (sandbox policy generator — EXISTS)
#   6. solo_warroom.py                          (War Room — EXISTS)
#   7. contracts.py                             (message schemas — EXISTS)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert Python and TypeScript engineer remediating gaps in the
Milimo Claw solo-founder template implementation identified by the v2 audit.

The audit found 9 gaps across three priority levels. This prompt addresses
all 9 in priority order. Most are targeted fixes to existing files — not
new modules. Read each task fully before writing any code.

The spec is the ground truth. The audit identifies what deviates from it.
This prompt defines exactly what to fix and how.

---

## CONTEXT — WHAT ALREADY WORKS (DO NOT TOUCH)

The audit confirms the following are correctly implemented:
  - Rule 1: OPS → FINANCE pricing_query sequencing ✅
  - Rule 2: FINANCE two-stage invoice approval ✅
  - Rule 3: BUILD two-stage PR + deploy approval ✅
  - Rule 5: CONTENT brief_acknowledged within 5 min ✅
  - Rule 8: BUILD sprint planning 5-minute Analytics timeout ✅
  - Deep Work Mode per-claw policies ✅
  - Phase C MVR (Ops intake → Finance → Content/Build) ✅
  - Phase D MVR (Finance invoice flow) ✅
  - Phase E MVR (Build PR + deploy flow) ✅
  - Phase F MVR (Analytics intelligence flow) ✅
  - All 17 message type schemas in contracts.py ✅
  - Analytics baseline (Sunday 01:00) and report (Sunday 02:00) ✅

Do not rewrite, reorganize, or refactor any of the above.
Fix only what the audit flags. Surgical edits only.

---

## DEVELOPMENT PHASE CONSTRAINTS

**Inference:** ALL inference routes to cloud. No local NIM routing.
Log data_type on every inference call. Mandatory.

**Standards:**
  - Python 3.11+, full type hints, pathlib.Path only
  - PyYAML safe_load only — never yaml.load()
  - All log files: append-only JSONL with fcntl file locking
  - Atomic writes: temp file → Path.rename() for all JSON summaries
  - Tests: pytest for Python, Jest for TypeScript
  - No stubs, no TODOs, no placeholder comments

---

## HIGH PRIORITY FIXES
## These block correct operation. Fix all three before anything else.

---

### FIX 1 — Add Shared Read Mount to Missing Sandbox Policies

**Audit finding (Section 3, HIGH):**
Only `content-sandbox.yaml` has the shared read mount for
`/sandbox/analytics/reports`. The other five claws are missing it.
The Analytics Claw's `weekly-intelligence.json` must be readable by
ALL claws. Without this, the intelligence layer is silently broken.

**Files to modify:**
  - `milimo-blueprint/policies/ops-sandbox.yaml`
  - `milimo-blueprint/policies/finance-sandbox.yaml`
  - `milimo-blueprint/policies/build-sandbox.yaml`

**For each of the three files**, add the shared read mount entry in the
`filesystem` section following the exact same pattern as
`content-sandbox.yaml` line 23:

```yaml
filesystem:
  # ... existing entries unchanged ...
  read_only:
    # ... existing read_only entries unchanged ...
    - path: "/sandbox/analytics/reports/weekly-intelligence.json"
      label: "analytics_shared_read"
      purpose: "Weekly intelligence report — read by all claws"
```

If the `read_only` key already exists in any of the three files,
append the new entry to it. Do not replace existing entries.

Print the updated `filesystem` section of each modified file.

**Verification:** After adding the mount entries, confirm that all six
sandbox policy files now contain a reference to
`/sandbox/analytics/reports/weekly-intelligence.json`. Run a grep
across all six policy files and show the output.

---

### FIX 2 — Stagger Evolution Cycle Schedule in solo-founder.yaml

**Audit finding (Section 3, HIGH):**
`solo-founder.yaml` uses a single `time: "02:00"` for all claws.
The spec requires staggered per-claw times with 5-minute gaps so each
claw runs its evolution on fresh Analytics data.

Required schedule:
```
analytics_baseline:   "01:00"   (already implemented in analytics_scheduler.py)
analytics_report:     "02:00"   (already implemented in analytics_scheduler.py)
content:              "02:05"
ops:                  "02:15"
analytics_evolution:  "02:25"
build:                "02:35"
finance:              "03:00"
```

**File to modify:** `milimo-blueprint/templates/solo-founder.yaml`

Replace the existing `evolution:` block with:

```yaml
evolution:
  cycle_day: sunday
  schedule:
    analytics_baseline:  "01:00"
    analytics_report:    "02:00"
    content:             "02:05"
    ops:                 "02:15"
    analytics_evolution: "02:25"
    build:               "02:35"
    finance:             "03:00"

  min_thresholds:
    content:
      approved_posts: 10
      rejected_drafts: 3
      performance_weeks: 1
    ops:
      client_interactions: 5
      projects: 3
      comms_weeks: 2
    analytics:
      signal_weeks: 3
      revenue_summaries: 1
      health_signals: 1
    finance:
      invoices: 3
      completed_projects: 2
      expense_weeks: 4
    build:
      merged_prs: 5
      sprints: 3
      deploys: 2
      cost_weeks: 4
```

**File to modify:** `milimo-blueprint/orchestrator/solo_evolution.py`

The current code reads a single `time` value (line 94–95):
```python
day = evolution_config.get("day", "sunday")
time_str = evolution_config.get("time", "02:00")
```

Replace this with per-claw schedule parsing:

```python
def parse_evolution_schedule(evolution_config: dict) -> dict[str, str]:
    """
    Parse per-claw evolution schedule from solo-founder.yaml.

    Returns dict mapping claw role to scheduled time string.
    Falls back to legacy single-time format if schedule key missing.
    """
    schedule = evolution_config.get("schedule", {})

    if schedule:
        return {
            "content":             schedule.get("content",             "02:05"),
            "ops":                 schedule.get("ops",                 "02:15"),
            "analytics_evolution": schedule.get("analytics_evolution", "02:25"),
            "build":               schedule.get("build",               "02:35"),
            "finance":             schedule.get("finance",             "03:00"),
        }
    else:
        # Legacy fallback: single time for all claws
        legacy_time = evolution_config.get("time", "02:00")
        return {role: legacy_time for role in
                ["content", "ops", "analytics_evolution", "build", "finance"]}
```

Then update the scheduler initialization to use the per-claw schedule:

```python
def _init_evolution_timers(
    self,
    evolution_config: dict,
    claw_schedulers: dict[str, Any]
) -> None:
    """
    Initialize per-claw evolution timers from staggered schedule.

    claw_schedulers: dict mapping role name to that claw's scheduler instance.
    Each scheduler must expose a run_evolution_cycle() method.
    """
    schedule = parse_evolution_schedule(evolution_config)

    for role, time_str in schedule.items():
        if role not in claw_schedulers:
            # Skip if this claw is not active in the current template
            continue

        hour, minute = map(int, time_str.split(":"))
        scheduler = claw_schedulers[role]

        self._schedule_weekly(
            job_name=f"{role}_evolution",
            job_fn=scheduler.run_evolution_cycle,
            target_hour=hour,
            target_minute=minute,
            target_weekday=6   # Sunday
        )

        self._log(f"Evolution scheduled for {role} at {time_str} on Sunday")
```

Write pytest tests:
- `parse_evolution_schedule` with full schedule key returns correct per-claw times
- `parse_evolution_schedule` with legacy `time` key falls back correctly
- `parse_evolution_schedule` with empty config returns default times
- `_init_evolution_timers` schedules one timer per active claw
- Finance timer scheduled at 03:00, Content at 02:05 (verify separately)
- Inactive claw (e.g. build=None) skipped without error

---

### FIX 3 — Create Phase A Isolation Test Suite

**Audit finding (Section 2, HIGH):**
Phase A tests A3–A8 are missing or simulated. The spec is explicit:
"Stop here if any of A1–A6 fails. Fix the mount configuration before
proceeding." There is no test file that enforces this gate.

**New file:** `milimo-blueprint/tests/test_phase_a_isolation.py`

This file is the mandatory first gate. If ANY test in this file fails,
the entire MVR suite must not proceed. Implement with pytest marks so
CI can enforce this ordering.

```python
"""
Phase A — Shared Mount Verification and Sandbox Isolation Tests

These tests MUST ALL PASS before any other MVR tests run.
They verify:
  1. All six sandbox mounts exist and are correctly configured
  2. weekly-intelligence.json is readable by all six claws
  3. Cross-sandbox reads correctly fail (isolation enforcement)

If any test in this file fails: fix sandbox policy configuration
before proceeding to Phase B, C, D, E, or F tests.
"""
import pytest
import tempfile
import json
from pathlib import Path

# Mark all tests in this file as phase_a — run first in CI
pytestmark = pytest.mark.phase_a


SANDBOX_ROOTS = {
    "content":   Path("/sandbox/content"),
    "clients":   Path("/sandbox/clients"),
    "analytics": Path("/sandbox/analytics"),
    "finance":   Path("/sandbox/finance"),
    "build":     Path("/sandbox/build"),
}

# Fallback paths for dev machines where /sandbox/ is not available
FALLBACK_ROOTS = {
    role: Path.home() / ".milimo" / "sandboxes" / role
    for role in SANDBOX_ROOTS
}

SHARED_REPORT_PATH = Path("/sandbox/analytics/reports/weekly-intelligence.json")
SHARED_REPORT_FALLBACK = (
    Path.home() / ".milimo" / "sandboxes" / "analytics" /
    "reports" / "weekly-intelligence.json"
)

VALID_REPORT_CONTENT = {
    "generated_at": "2026-03-22T01:00:00Z",
    "week_of": "2026-03-16",
    "squad_id": "test-squad",
    "summary_narrative": "Test report for Phase A isolation verification.",
    "content_performance": {},
    "client_health": {},
    "revenue": {},
    "delivery": {},
    "opportunities": [],
    "anomalies": [],
    "forward_projections": {}
}


def _resolve_sandbox(role: str) -> Path:
    """Return actual sandbox path — primary if exists, fallback otherwise."""
    primary = SANDBOX_ROOTS.get(role, FALLBACK_ROOTS[role])
    return primary if primary.exists() else FALLBACK_ROOTS[role]

def _resolve_shared_report() -> Path:
    return (
        SHARED_REPORT_PATH
        if SHARED_REPORT_PATH.parent.exists()
        else SHARED_REPORT_FALLBACK
    )


# ─────────────────────────────────────────────────────────────────
# A1 — All five sandbox mounts exist and are isolated
# ─────────────────────────────────────────────────────────────────

def test_a1_content_sandbox_exists():
    """Content Claw sandbox directory exists."""
    path = _resolve_sandbox("content")
    assert path.exists(), f"Content sandbox missing: {path}"

def test_a1_clients_sandbox_exists():
    """Ops Claw sandbox directory exists."""
    path = _resolve_sandbox("clients")
    assert path.exists(), f"Ops sandbox missing: {path}"

def test_a1_analytics_sandbox_exists():
    """Analytics Claw sandbox directory exists."""
    path = _resolve_sandbox("analytics")
    assert path.exists(), f"Analytics sandbox missing: {path}"

def test_a1_finance_sandbox_exists():
    """Finance Claw sandbox directory exists."""
    path = _resolve_sandbox("finance")
    assert path.exists(), f"Finance sandbox missing: {path}"

def test_a1_build_sandbox_exists():
    """Build Claw sandbox directory exists."""
    path = _resolve_sandbox("build")
    assert path.exists(), f"Build sandbox missing: {path}"


# ─────────────────────────────────────────────────────────────────
# A2 — Write test file to shared report location
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def written_report() -> Path:
    """
    Write a valid weekly-intelligence.json to the Analytics reports dir.
    Used by A3–A6 read tests.
    Cleans up after the module completes.
    """
    report_path = _resolve_shared_report()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(
        json.dumps(VALID_REPORT_CONTENT, indent=2),
        encoding="utf-8"
    )
    yield report_path

    # Cleanup — restore to empty dict after tests
    report_path.write_text("{}", encoding="utf-8")

def test_a2_write_report_to_analytics(written_report):
    """
    Weekly intelligence report can be written to the Analytics reports dir.
    """
    assert written_report.exists(), f"Report not written: {written_report}"
    content = json.loads(written_report.read_text())
    assert content.get("squad_id") == "test-squad"


# ─────────────────────────────────────────────────────────────────
# A3–A6 — All four non-Analytics claws can read the shared report
# ─────────────────────────────────────────────────────────────────

def _read_report_as_claw(claw_role: str, report_path: Path) -> dict:
    """
    Simulate a claw reading the shared report.

    In production this goes through Landlock filesystem policy.
    In testing, we verify:
      1. The report path is within the claw's declared read_only mounts
         (parsed from the claw's sandbox policy yaml)
      2. The file is actually readable at that path
    """
    from milimo_blueprint.orchestrator.solo_sandbox import (
        load_sandbox_policy,
        get_read_only_mounts
    )

    policy = load_sandbox_policy(claw_role)
    read_only_mounts = get_read_only_mounts(policy)

    # Verify the shared report path is declared in this claw's read_only mounts
    report_str = str(report_path)
    declared = any(
        report_str.startswith(str(mount)) or report_str == str(mount)
        for mount in read_only_mounts
    )

    assert declared, (
        f"{claw_role} sandbox policy does not declare read access to "
        f"{report_path}.
"
        f"Declared read_only mounts: {read_only_mounts}
"
        f"Fix: add the shared_read entry to "
        f"policies/{claw_role}-sandbox.yaml"
    )

    # Verify the file is actually readable
    content = json.loads(report_path.read_text(encoding="utf-8"))
    return content


def test_a3_content_claw_can_read_report(written_report):
    """
    Content Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if content-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("content", written_report)
    assert "squad_id" in content

def test_a4_ops_claw_can_read_report(written_report):
    """
    Ops Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if ops-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("ops", written_report)
    assert "squad_id" in content

def test_a5_finance_claw_can_read_report(written_report):
    """
    Finance Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if finance-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("finance", written_report)
    assert "squad_id" in content

def test_a6_build_claw_can_read_report(written_report):
    """
    Build Claw can read /sandbox/analytics/reports/weekly-intelligence.json.
    Fails if build-sandbox.yaml missing the shared_read mount entry.
    """
    content = _read_report_as_claw("build", written_report)
    assert "squad_id" in content


# ─────────────────────────────────────────────────────────────────
# A7–A8 — Cross-sandbox isolation: reads that MUST FAIL
# ─────────────────────────────────────────────────────────────────

def _assert_cross_sandbox_read_blocked(
    reading_claw: str,
    blocked_path: Path
) -> None:
    """
    Assert that reading_claw does NOT have the blocked_path in its
    declared read_only or read_write mounts.

    This verifies filesystem isolation at the policy level.
    In production, Landlock enforcement makes this a kernel-level block.
    In testing, we verify the policy declaration is correct.
    """
    from milimo_blueprint.orchestrator.solo_sandbox import (
        load_sandbox_policy,
        get_all_accessible_mounts
    )

    policy = load_sandbox_policy(reading_claw)
    accessible = get_all_accessible_mounts(policy)

    blocked_str = str(blocked_path)
    accessible_strs = [str(m) for m in accessible]

    # None of the accessible mounts should be a parent of blocked_path
    # (except the shared analytics/reports mount which is intentional)
    SHARED_REPORT_STR = str(SHARED_REPORT_PATH)

    for mount in accessible_strs:
        if mount == SHARED_REPORT_STR:
            continue   # This cross-mount is intentional and expected
        assert not blocked_str.startswith(mount), (
            f"ISOLATION VIOLATION: {reading_claw} has access to {blocked_path} "
            f"via mount {mount}.
"
            f"This claw should NOT be able to read this path.
"
            f"Fix: remove the mount entry from "
            f"policies/{reading_claw}-sandbox.yaml"
        )


def test_a7_content_cannot_read_clients_sandbox():
    """
    Content Claw CANNOT read /sandbox/clients.
    Cross-sandbox isolation must be enforced.
    """
    _assert_cross_sandbox_read_blocked(
        reading_claw="content",
        blocked_path=Path("/sandbox/clients")
    )

def test_a8_finance_cannot_read_build_sandbox():
    """
    Finance Claw CANNOT read /sandbox/build.
    Cross-sandbox isolation must be enforced.
    """
    _assert_cross_sandbox_read_blocked(
        reading_claw="finance",
        blocked_path=Path("/sandbox/build")
    )

# Bonus isolation checks — not in spec A1-A8 but verify full isolation
def test_isolation_ops_cannot_read_finance():
    _assert_cross_sandbox_read_blocked("ops", Path("/sandbox/finance"))

def test_isolation_ops_cannot_read_build():
    _assert_cross_sandbox_read_blocked("ops", Path("/sandbox/build"))

def test_isolation_build_cannot_read_finance():
    _assert_cross_sandbox_read_blocked("build", Path("/sandbox/finance"))

def test_isolation_build_cannot_read_clients():
    _assert_cross_sandbox_read_blocked("build", Path("/sandbox/clients"))

def test_isolation_finance_cannot_read_clients():
    _assert_cross_sandbox_read_blocked("finance", Path("/sandbox/clients"))
```

Also add the helper functions this test file requires to `solo_sandbox.py`:

```python
def load_sandbox_policy(claw_role: str) -> dict:
    """
    Load and return the parsed sandbox policy YAML for a given claw role.
    Reads from milimo-blueprint/policies/{role}-sandbox.yaml.
    Maps role names: "ops" → "ops-sandbox.yaml", "clients" → "ops-sandbox.yaml"
    """

def get_read_only_mounts(policy: dict) -> list[Path]:
    """
    Extract all read_only mount paths from a parsed sandbox policy dict.
    Returns list of Path objects.
    """

def get_all_accessible_mounts(policy: dict) -> list[Path]:
    """
    Extract ALL accessible paths (read_only + read_write) from policy.
    Returns list of Path objects.
    Used for isolation violation detection.
    """
```

---

## MEDIUM PRIORITY FIXES
## Spec deviations that affect correctness. Fix after all HIGH fixes pass.

---

### FIX 4 — Add feature_brief_acknowledged to contracts.py and Build Claw

**Audit finding (Section 4, Rule 6 — MEDIUM):**
The spec requires Build Claw to acknowledge every `feature_brief` from
Ops Claw within 10 minutes. The message type is missing from contracts.py
and there is no acknowledgment timer in the Build Claw.

**File to modify:** `milimo-blueprint/orchestrator/contracts.py`

Add to `MESSAGE_TYPE_SCHEMAS`:

```python
"feature_brief_acknowledged": {
    "sender_roles": ["build"],
    "recipient_roles": ["ops"],
    "required_payload": [
        "project_id",
        "estimated_start",    # ISO timestamp
        "clarity_score"       # "clear" | "low"
    ],
    "optional_payload": ["missing_elements", "deadline_risk"],
    "frequency": "on_event",
    "priority": "AUTO",
    "sla_minutes": 10,   # must send within 10 min of feature_brief receipt
},
```

**File to modify:**
`milimo-blueprint/orchestrator/build/signal_dispatcher.py`

The `handle_feature_brief` method exists but the acknowledgment is
flagged as missing. Verify the method sends
`feature_brief_acknowledged` within 10 minutes of receipt. If the
acknowledgment send is missing, add it:

```python
def handle_feature_brief(self, message: dict) -> None:
    """
    Receives feature_brief from Ops Claw.
    Validates schema, routes to issue_manager for GitHub issue creation.
    MUST send feature_brief_acknowledged within 10 minutes.
    """
    # Validate schema against contracts.py
    self._validate_message(message, "feature_brief")

    project_id = message["payload"]["project_id"]
    feature_description = message["payload"]["feature_description"]
    deadline = message["payload"]["deadline"]
    acceptance_criteria = message["payload"].get("acceptance_criteria", "")

    # Log receipt
    self._log(
        action_type="feature_brief_received",
        entity_id=project_id,
        outcome="received",
        details={"feature_description": feature_description[:100]}
    )

    # Start 10-minute acknowledgment timer
    # Acknowledgment is sent from issue_manager.handle_feature_brief()
    # which is called synchronously — if it takes longer than 10 min,
    # send a preliminary acknowledgment immediately
    ack_timer = threading.Timer(
        600,  # 10 minutes
        self._send_overdue_ack_warning,
        args=[project_id]
    )
    ack_timer.start()

    try:
        # Route to issue_manager for GitHub issue creation and scoring
        self._issue_manager.handle_feature_brief(
            client_id=message["payload"]["client_id"],
            project_id=project_id,
            feature_description=feature_description,
            deadline=deadline,
            acceptance_criteria=acceptance_criteria
        )
        # issue_manager.handle_feature_brief() calls
        # send_feature_brief_acknowledged() on completion
    finally:
        ack_timer.cancel()

def _send_overdue_ack_warning(self, project_id: str) -> None:
    """
    Called if feature_brief processing exceeds 10 minutes.
    Sends a preliminary acknowledgment to prevent Ops Claw timeout.
    """
    self.send_feature_brief_acknowledged(
        project_id=project_id,
        estimated_start="TBD",
        clarity_score="low"
    )
    self._log(
        action_type="feature_brief_ack_delayed",
        entity_id=project_id,
        outcome="preliminary_ack_sent",
        details={"reason": "processing exceeded 10-minute SLA"}
    )
```

Write pytest tests:
- feature_brief_acknowledged schema validates with all required fields
- handle_feature_brief sends acknowledgment within 10 minutes (mock timer)
- Overdue acknowledgment fires if issue_manager takes > 10 minutes
- clarity_score="low" set when acceptance_criteria is empty
- schema rejects "content" as sender_role (build only)

---

### FIX 5 — Add Analytics Query Response SLA Enforcement

**Audit finding (Section 4, Rule 7 — MEDIUM):**
The spec requires Analytics Claw to respond to
`content_performance_query` and `behavior_query` within 2 minutes.
There is no SLA timer or enforcement in the query handler.

**File to modify:**
`milimo-blueprint/orchestrator/analytics/query_handler.py`

The `QueryHandler` class exists with a `RESPONSE_TIMEOUT_SECONDS = 110`
constant. The audit flags that this SLA is not being enforced or logged.

Add SLA enforcement and logging to the `handle` method:

```python
def handle(self, raw_message: dict) -> QueryResponse:
    """
    Handle on-demand query. SLA: 2-minute maximum response time.
    Logs SLA violation if processing exceeds RESPONSE_TIMEOUT_SECONDS.
    Always responds — never times out silently.
    """
    start_time = time.monotonic()
    query_id = raw_message.get("message_id", str(uuid.uuid4()))
    message_type = raw_message.get("message_type", "unknown")
    requesting_claw = raw_message.get("sender_role", "unknown")

    # Log query receipt
    self._queries_log.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query_id": query_id,
        "message_type": message_type,
        "requesting_claw": requesting_claw,
        "event": "received"
    })

    try:
        # Route and process
        response = self._route_query(raw_message)

    except Exception as e:
        # Never fail silently — return error response
        response = self._error_response(
            query_id=query_id,
            query_type=message_type,
            requesting_claw=requesting_claw,
            error=str(e)
        )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    sla_exceeded = elapsed_ms > (self.RESPONSE_TIMEOUT_SECONDS * 1000)

    if sla_exceeded:
        # Log SLA violation — do not raise, still send response
        self._log_sla_violation(
            query_id=query_id,
            message_type=message_type,
            elapsed_ms=elapsed_ms,
            sla_ms=self.RESPONSE_TIMEOUT_SECONDS * 1000
        )

    # Log response dispatch with timing
    self._queries_log.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query_id": query_id,
        "message_type": message_type,
        "requesting_claw": requesting_claw,
        "event": "responded",
        "elapsed_ms": elapsed_ms,
        "sla_exceeded": sla_exceeded,
        "data_quality": response.data_quality
    })

    return response

def _log_sla_violation(
    self,
    query_id: str,
    message_type: str,
    elapsed_ms: int,
    sla_ms: int
) -> None:
    """Log SLA violation to operational.log and signals.log."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action_type": "query_sla_violation",
        "entity_id": query_id,
        "outcome": "sla_exceeded",
        "details": {
            "message_type": message_type,
            "elapsed_ms": elapsed_ms,
            "sla_ms": sla_ms,
            "overage_ms": elapsed_ms - sla_ms
        }
    }
    self._operational_log.append(entry)
    # Also write to signals.log as a warning signal
    self._signals_log.append(entry)
```

Write pytest tests:
- Query within 2 minutes: no SLA violation logged
- Query exceeding 110 seconds: SLA violation logged (mock slow aggregation)
- SLA violation does NOT prevent response from being sent
- Both queries.log and operational.log updated on each query
- Error response returned and logged when processing throws exception
- sla_exceeded flag correct in both passing and failing cases

---

### FIX 6 — Create Phase B War Room Integration Tests

**Audit finding (Section 9, MEDIUM):**
Phase B (War Room approval flow) tests are entirely missing.
The spec defines 8 steps covering the War Room TUI, priority ordering,
and approval mechanics.

**New file:** `milimo-blueprint/tests/test_phase_b_warroom.py`

```python
"""
Phase B — War Room Approval Flow Integration Tests

Tests B1-B8: War Room initialization, queue priority ordering,
and REVIEW/HOLD approval mechanics.

These tests run after Phase A passes.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

pytestmark = pytest.mark.phase_b


class TestWarRoomInitialization:

    def test_b1_war_room_tui_renders_five_claw_health_panel(self):
        """
        War Room TUI initializes with health panel showing all 6 claws.
        Each claw appears in the right panel with: name, status dot,
        tool count, last evolution timestamp, this-week activity count.
        """
        from milimo_blueprint.orchestrator.solo_warroom import SoloWarRoom

        war_room = SoloWarRoom(squad_id="test-squad")
        health_panel = war_room.get_health_panel()

        expected_claws = ["content", "ops", "analytics", "finance", "build", "assistant"]
        for claw in expected_claws:
            assert claw in health_panel, (
                f"Claw '{claw}' missing from War Room health panel"
            )

    def test_b2_morning_brief_scheduled_at_07_00(self):
        """
        Morning brief is scheduled for 07:00 daily.
        Evening wrap is scheduled for 20:00 daily.
        """
        from milimo_blueprint.orchestrator.solo_warroom import SoloWarRoom

        war_room = SoloWarRoom(squad_id="test-squad")
        schedule = war_room.get_digest_schedule()

        assert schedule["morning_brief"] == "07:00"
        assert schedule["evening_wrap"] == "20:00"


class TestQueuePriorityOrdering:

    def test_b3_mock_review_action_appears_in_queue(self):
        """
        Injecting a mock REVIEW action produces a queued entry
        with correct mode, claw source, and summary.
        """
        from milimo_blueprint.orchestrator.solo_warroom import (
            SoloWarRoom, queue_action
        )

        war_room = SoloWarRoom(squad_id="test-squad")
        action_id = queue_action(
            war_room=war_room,
            claw_role="content",
            mode="REVIEW",
            action_type="social_post_draft",
            entity_id="draft_001",
            summary="Draft ready: LinkedIn post for @NovaBrand",
            context={"platform": "linkedin", "approval_probability": 0.87}
        )

        queue = war_room.get_pending_queue()
        entry = next((a for a in queue if a["action_id"] == action_id), None)

        assert entry is not None
        assert entry["mode"] == "REVIEW"
        assert entry["claw_role"] == "content"
        assert "LinkedIn" in entry["summary"]

    def test_b4_hold_items_appear_above_review_items(self):
        """
        HOLD actions must always appear above REVIEW actions in the queue
        regardless of insertion order.
        """
        from milimo_blueprint.orchestrator.solo_warroom import (
            SoloWarRoom, queue_action
        )

        war_room = SoloWarRoom(squad_id="test-squad")

        # Insert REVIEW first, then HOLD
        queue_action(war_room, "content", "REVIEW", "draft", "draft_001",
                     "REVIEW action inserted first", {})
        queue_action(war_room, "finance", "HOLD", "invoice_send",
                     "invoice_001", "HOLD action inserted second", {})

        queue = war_room.get_pending_queue()
        modes = [a["mode"] for a in queue]

        # Find first HOLD and first REVIEW index
        hold_idx = next(i for i, m in enumerate(modes) if m == "HOLD")
        review_idx = next(i for i, m in enumerate(modes) if m == "REVIEW")

        assert hold_idx < review_idx, (
            "HOLD items must appear before REVIEW items in queue. "
            f"Got HOLD at index {hold_idx}, REVIEW at index {review_idx}"
        )


class TestApprovalMechanics:

    def test_b5_approve_review_executes_and_moves_to_auto_log(self):
        """
        Approving a REVIEW action:
        1. Executes the action (calls execute_fn)
        2. Removes item from pending queue
        3. Adds item to AUTO log (morning digest)
        """
        from milimo_blueprint.orchestrator.solo_warroom import (
            SoloWarRoom, queue_action
        )

        war_room = SoloWarRoom(squad_id="test-squad")
        execute_fn = MagicMock()

        action_id = queue_action(
            war_room, "ops", "REVIEW", "welcome_message", "client_001",
            "New client welcome — @TestCo", {"triage_score": 94}
        )

        war_room.handle_approve(action_id=action_id, execute_fn=execute_fn)

        # execute_fn must have been called
        execute_fn.assert_called_once()

        # Must be gone from pending queue
        pending = war_room.get_pending_queue()
        assert not any(a["action_id"] == action_id for a in pending), (
            "Approved action should be removed from pending queue"
        )

        # Must appear in AUTO log
        auto_log = war_room.get_auto_log()
        assert any(a["action_id"] == action_id for a in auto_log), (
            "Approved action should appear in AUTO log for morning digest"
        )

    def test_b6_inject_hold_action_appears_at_queue_top(self):
        """
        A HOLD action queued after existing REVIEW items appears
        at the top of the queue (above all REVIEW items).
        """
        from milimo_blueprint.orchestrator.solo_warroom import (
            SoloWarRoom, queue_action
        )

        war_room = SoloWarRoom(squad_id="test-squad")

        # Fill queue with REVIEW items first
        for i in range(3):
            queue_action(war_room, "content", "REVIEW", "draft",
                         f"draft_{i}", f"Review item {i}", {})

        # Now inject a HOLD
        hold_id = queue_action(
            war_room, "finance", "HOLD", "invoice_send", "invoice_001",
            "Invoice ready to send — $2,400", {}
        )

        queue = war_room.get_pending_queue()
        assert queue[0]["action_id"] == hold_id, (
            "HOLD action must be at position 0 in queue "
            "regardless of when it was inserted"
        )

    def test_b7_release_hold_executes_action(self):
        """
        Releasing a HOLD:
        1. Calls execute_fn (the actual action — merge, send invoice, deploy)
        2. Removes item from HOLD queue
        """
        from milimo_blueprint.orchestrator.solo_warroom import (
            SoloWarRoom, queue_action
        )

        war_room = SoloWarRoom(squad_id="test-squad")
        execute_fn = MagicMock()

        hold_id = queue_action(
            war_room, "finance", "HOLD", "invoice_send", "invoice_001",
            "Invoice ready to send", {}
        )

        war_room.handle_hold_release(
            action_id=hold_id,
            execute_fn=execute_fn
        )

        execute_fn.assert_called_once()

        pending = war_room.get_pending_queue()
        assert not any(a["action_id"] == hold_id for a in pending)

    def test_b8_keyboard_shortcuts_registered(self):
        """
        War Room TUI has keyboard shortcuts registered:
        A=approve, B=block, E=edit, R=release, D=digest, F=deep_work, Q=quit
        """
        from milimo_blueprint.orchestrator.solo_warroom import SoloWarRoom

        war_room = SoloWarRoom(squad_id="test-squad")
        shortcuts = war_room.get_registered_shortcuts()

        required = {"A", "B", "E", "R", "D", "F", "Q"}
        registered = set(shortcuts.keys())

        missing = required - registered
        assert not missing, (
            f"Missing keyboard shortcuts: {missing}. "
            f"Registered shortcuts: {registered}"
        )
```

---

## LOW PRIORITY FIXES
## Minor discrepancies. Fix after all MEDIUM fixes pass.

---

### FIX 7 — Correct Token Budget in solo-founder.yaml

**Audit finding (Section 7, LOW):**
`cost_guard.daily_cloud_token_budget` is set to 100,000.
Spec requires 50,000. The audit notes "Docker testing mode" as the
reason for the higher value. The spec's 50,000 is the correct value
for solo development on an Apple Silicon machine.

**File to modify:** `milimo-blueprint/templates/solo-founder.yaml`

In the `cost_guard` section:

```yaml
cost_guard:
  daily_cloud_token_budget: 50000          # was 100000 — corrected per spec
  alert_at_percent: 80
  fallback_on_exceed: lighter_prompt       # was "cloud" — corrected per spec
  never_block_claw_action: true            # always fallback, never fail
```

The `fallback_on_exceed: lighter_prompt` means: when the daily budget
is exceeded, the inference client automatically uses a reduced-context
prompt strategy (shorter codebase context, fewer examples, tighter max_tokens)
rather than failing the action entirely.

**File to verify/modify:**
`milimo-blueprint/orchestrator/solo_privacy.py` (or equivalent inference client)

Confirm the `lighter_prompt` fallback strategy is implemented. It should:
- Reduce max_tokens by 50% when in fallback mode
- Trim any long context fields (codebase_context, comms_history, etc.)
- Log: `action_type="cost_guard_fallback_active"` on every call that uses it
- Never return an error — always complete the inference call

If the strategy is not implemented, add it:

```python
def _apply_lighter_prompt_strategy(
    self,
    prompt: str,
    max_tokens: int,
    data_type: str
) -> tuple[str, int]:
    """
    Reduce prompt complexity when daily token budget is exceeded.
    Called automatically when cost_guard triggers fallback.
    Returns (trimmed_prompt, reduced_max_tokens).
    """
    reduced_max_tokens = max_tokens // 2

    # Trim long sections that are enrichments, not core instructions
    # These are heuristic cuts — preserve the task instruction, trim context
    TRIM_MARKERS = [
        "CODEBASE CONTEXT:",
        "COMMUNICATION HISTORY:",
        "HISTORICAL CALIBRATION DATA:",
        "SIMILAR PAST PROJECTS:",
    ]

    trimmed = prompt
    for marker in TRIM_MARKERS:
        if marker in trimmed:
            idx = trimmed.index(marker)
            next_section = trimmed.find("

", idx + len(marker) + 200)
            if next_section != -1:
                # Keep first 200 chars of context section, cut the rest
                trimmed = (
                    trimmed[:idx + len(marker) + 200] +
                    "
[context trimmed — cost guard active]

" +
                    trimmed[next_section:]
                )

    return trimmed, reduced_max_tokens
```

Write pytest tests: budget at 100% triggers fallback, fallback reduces
max_tokens by 50%, fallback never raises exception, cost_guard_fallback_active
logged on each fallback call, budget below 80% uses normal strategy.

---

### FIX 8 — Correct Ops deadline_critical Approval Mode to HOLD

**Audit finding (Section 6, LOW):**
`solo-founder.yaml` has `deadline_flag: REVIEW` for Ops Claw deadline
critical (24-hour) events. The spec requires HOLD for the 24-hour
deadline threshold.

**File to modify:** `milimo-blueprint/templates/solo-founder.yaml`

In the Ops Claw approval modes section, find and correct:

```yaml
# BEFORE (incorrect):
deadline_flag: REVIEW

# AFTER (correct):
deadline_risk: REVIEW           # 5+ days out — elevated risk
deadline_critical: HOLD         # 24 hours — explicit action required
```

These are two separate action types. The audit found only `deadline_flag`
which collapses both. They must be separate with different modes.

**File to verify:** `milimo-blueprint/orchestrator/ops/project_manager.py`

Confirm `check_all_deadlines()` uses two separate queue calls:

```python
def check_all_deadlines(self) -> list[DeadlineRisk]:
    risks = []
    for project in self.get_active_projects():
        days_remaining = self._days_until(project.deadline)

        if days_remaining <= 1:
            # 24 hours or less — HOLD
            action_id = self._approval_handler.queue_hold(
                action_type="deadline_critical",
                entity_id=project.project_id,
                content=f"Deadline in {days_remaining * 24:.0f} hours — "
                        f"{project.client_id}: {project.project_id}",
                context={
                    "deadline": project.deadline,
                    "hours_remaining": days_remaining * 24,
                    "risk_level": "critical"
                }
            )
            risks.append(DeadlineRisk(
                project_id=project.project_id,
                client_id=project.client_id,
                deadline=project.deadline,
                days_remaining=days_remaining,
                risk_level="critical",
                recommended_action="Immediate operator action required"
            ))

        elif days_remaining <= 5:
            # 2–5 days — REVIEW
            action_id = self._approval_handler.queue_review(
                action_type="deadline_risk",
                entity_id=project.project_id,
                content=f"Deadline risk: {days_remaining} days remaining — "
                        f"{project.client_id}: {project.project_id}",
                context={
                    "deadline": project.deadline,
                    "days_remaining": days_remaining,
                    "risk_level": "elevated"
                }
            )
            risks.append(DeadlineRisk(
                project_id=project.project_id,
                client_id=project.client_id,
                deadline=project.deadline,
                days_remaining=days_remaining,
                risk_level="elevated",
                recommended_action="Review delivery status"
            ))

    return risks
```

Write pytest tests: 24-hour deadline queues HOLD (not REVIEW),
5-day deadline queues REVIEW (not HOLD), 6-day deadline queues nothing,
boundary at exactly 1 day queues HOLD, boundary at exactly 5 days
queues REVIEW.

---

### FIX 9 — Verify AGENTS.md Exists in Codebase

**Audit finding (Section 1, LOW):**
The audit reports AGENTS.md "not found" in the codebase. It was
generated in this session and must exist at the repository root.

**Action:** Copy or confirm `AGENTS.md` is present at the repository
root (same level as `README.md`). The file contents are already
defined — this is a placement verification only.

Confirm the file exists at `milimo-claw/AGENTS.md` and that it
contains a reference to all six claw spec documents in
`milimo-claw-docs/reference/`.

---

## FINAL VERIFICATION CHECKLIST

□ FIX 1: ops-sandbox.yaml has shared_read mount for weekly-intelligence.json
□ FIX 1: finance-sandbox.yaml has shared_read mount
□ FIX 1: build-sandbox.yaml has shared_read mount
□ FIX 1: All five policy files reference weekly-intelligence.json (grep confirms)
□ FIX 2: solo-founder.yaml evolution block has per-claw schedule times
□ FIX 2: parse_evolution_schedule() handles both schedule and legacy time key
□ FIX 2: _init_evolution_timers() creates one timer per active claw
□ FIX 2: Finance timer at 03:00, Content at 02:05 verified by test
□ FIX 3: test_phase_a_isolation.py exists with all A1–A8 + bonus tests
□ FIX 3: load_sandbox_policy(), get_read_only_mounts(), get_all_accessible_mounts() in solo_sandbox.py
□ FIX 3: A3 (Content reads report) passes with actual policy check
□ FIX 3: A4 (Ops reads report) passes
□ FIX 3: A5 (Finance reads report) passes — was missing in audit
□ FIX 3: A6 (Build reads report) passes — was missing in audit
□ FIX 3: A7 (Content cannot read /sandbox/clients) passes
□ FIX 3: A8 (Finance cannot read /sandbox/build) passes
□ FIX 4: feature_brief_acknowledged schema in contracts.py
□ FIX 4: handle_feature_brief sends ack within 10 minutes
□ FIX 4: Overdue ack (preliminary) fires if processing > 10 min
□ FIX 5: QueryHandler.handle() measures elapsed time on every query
□ FIX 5: SLA violation logged to operational.log and signals.log
□ FIX 5: SLA violation does NOT prevent response from being sent
□ FIX 6: test_phase_b_warroom.py exists with tests B1–B8
□ FIX 6: B4 verifies HOLD items appear above REVIEW items in queue
□ FIX 6: B5 verifies REVIEW approve calls execute_fn and moves to AUTO log
□ FIX 6: B7 verifies HOLD release calls execute_fn
□ FIX 7: daily_cloud_token_budget is 50000 (not 100000)
□ FIX 7: fallback_on_exceed is "lighter_prompt" (not "cloud")
□ FIX 7: _apply_lighter_prompt_strategy() reduces max_tokens by 50%
□ FIX 7: lighter_prompt fallback never raises exception
□ FIX 8: deadline_risk → REVIEW and deadline_critical → HOLD (separate)
□ FIX 8: check_all_deadlines() uses HOLD at day 1 boundary
□ FIX 8: check_all_deadlines() uses REVIEW at day 5 boundary
□ FIX 9: AGENTS.md present at repository root
□ All Phase A tests pass: pytest -m phase_a
□ All Phase B tests pass: pytest -m phase_b
□ All solo evolution tests pass
□ No existing passing tests broken by any fix

---

## OUTPUT FORMAT

For each fix:

  --- FIX N: [Title] ---
  Files: [exact paths — UPDATE or NEW]
  Summary: [one sentence]

  [complete implementation — no TODOs, no stubs]

  Tests: [complete pytest file if new, targeted test additions if existing]
  -----------------------------------------

Begin with Fix 1 (sandbox policies). Do not proceed to Fix 2 until
Fix 1 verification passes. Complete all HIGH fixes before MEDIUM.
Complete all MEDIUM fixes before LOW. The spec is ground truth.
All inference to cloud. Log data_type on every call.
