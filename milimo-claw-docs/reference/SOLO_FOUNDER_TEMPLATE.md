# Solo Founder Template

**Version:** 1.0
**Date:** March 2026
**Status:** Implemented

---

## Overview

The Solo Founder template enables a single operator to run all five claws simultaneously on one machine. Designed for solo founders who want to run a full autonomous operation before scaling to a squad.

---

## Quick Start

```bash
# Initialize solo founder configuration
openclaw milimo init --squad solo --template solo-founder

# Launch the War Room
openclaw milimo warroom

# Activate deep work mode
openclaw milimo squad finals-mode --resume-date 2026-04-15
```

---

## Configuration

The `solo-founder.yaml` template defines:

| Section | Description |
|---------|-------------|
| `template` | Template metadata (name, category, squad_size=1) |
| `operator_policy` | Approval modes for all five claws |
| `filesystem` | Mount paths for each claw sandbox |
| `inference` | Routing overrides and cost guard |
| `war_room` | Single-operator queue configuration |
| `evolution` | Per-claw evolution thresholds |
| `network_egress` | Approved API domains per claw |
| `deep_work_mode` | Finals mode configuration |

---

## Operator Policy

Single operator = you approve everything. Thresholds are set higher to reduce noise.

### Approval Modes

| Mode | Description |
|------|-------------|
| `AUTO` | Action executes without operator input |
| `REVIEW` | Action appears in queue for approval |
| `HOLD` | Action requires explicit approval before proceeding |

### Per-Claw Defaults

| Claw | Default Policy | Notes |
|------|----------------|-------|
| **Content** | Mostly AUTO | Social posts queue for morning review |
| **Ops** | REVIEW for clients | You decide who to work with |
| **Analytics** | Mostly AUTO | It only reads, trust it |
| **Finance** | HOLD for invoices | Nothing moves without you |
| **Build** | HOLD for deploys | You explicitly merge and deploy |

---

## Inference Routing

### Routing Configuration

| Data Type | Route | Reason |
|-----------|-------|--------|
| Client-facing drafts | `cloud` | Nemotron 120B for quality |
| Internal ideation | `local` | Save credits, stay private |
| Financial data | `local` | **LOCKED** — never cloud |
| Source code | `local` | **LOCKED** — never cloud |
| Client records | `local` | Sensitive — stays on device |
| Analytics synthesis | `local` | Proprietary operational data |
| Public docs/changelogs | `cloud` | Community will read these |

### Locked Routes

Financial data and source code are **locked to local**. Any attempt to override these routes raises `PrivacyPolicyViolationError`.

### Cost Guard

```yaml
cost_guard:
  daily_cloud_token_budget: 50000  # Hard ceiling
  alert_at_percent: 80             # Alert at 80% usage
  fallback_on_exceed: local        # Never fail, always fallback
```

---

## War Room

### Queue Priority

Actions are ordered by priority:

1. **HOLD** — Show blockers first
2. **REVIEW** — Then items needing your decision
3. **AUTO** — Finally auto-completed items for awareness

### Digest Schedule

| Digest | Time | Description |
|--------|------|-------------|
| Morning Brief | 07:00 | Overnight autonomous activity summary |
| Evening Wrap | 20:00 | Today's activity and tomorrow's queue |

---

## Evolution

### Per-Claw Thresholds

Each claw must meet minimum activity before first evolution:

| Claw | Threshold | Description |
|------|-----------|-------------|
| Content | 10 approved posts | Need real content history |
| Ops | 5 client interactions | Need client lifecycle data |
| Analytics | 3 weeks of data | Need trend baseline |
| Finance | 3 invoices | Need revenue patterns |
| Build | 5 merged PRs | Need shipping history |

### Schedule

```yaml
evolution:
  cycle: weekly
  day: sunday
  time: "02:00"  # Runs while you sleep
```

---

## Deep Work Mode

Solo founder equivalent of "finals mode" — for shipping sprints, conference travel, or any focused work period.

### Activation

```bash
openclaw milimo squad finals-mode --resume-date 2026-04-15
```

### Per-Claw Behavior

| Claw | On Activate | Behavior |
|------|-------------|----------|
| Content | `pause_drafts` | Queue only, no publishing |
| Ops | `maintenance` | Auto-responses to active clients |
| Analytics | `passive` | Collect data, no new experiments |
| Finance | `invoices_only` | Sends continue, no new intake |
| Build | `issues_only` | Triage only, no new PRs opened |

### Auto-Response Template

```
Hey [name], I'm heads-down on a focused sprint until [resume_date].
Your project is on track — I'll be back in full swing then. 🙏
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `milimo-blueprint/templates/solo-founder.yaml` | Template configuration |
| `milimo-blueprint/orchestrator/solo_init.py` | Template loader and validator |
| `milimo-blueprint/orchestrator/solo_sandbox.py` | Sandbox initialization |
| `milimo-blueprint/orchestrator/solo_warroom.py` | War Room queue |
| `milimo-blueprint/orchestrator/solo_privacy.py` | Inference router |
| `milimo-blueprint/orchestrator/solo_evolution.py` | Evolution scheduler |
| `milimo-blueprint/orchestrator/solo_deep_work.py` | Deep work mode |

---

## Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `solo_init.py` | 20 | Valid config, missing fields, invalid types, locked routes |
| `solo_sandbox.py` | 21 | Policy generation, network egress, inference routes |
| `solo_warroom.py` | 24 | Priority ordering, approve/block, AUTO execution |
| `solo_privacy.py` | 30 | Routing, locked routes, cost guard |
| `solo_evolution.py` | 28 | Thresholds, scheduling, status |
| `solo_deep_work.py` | 22 | Activation, policy changes, template substitution |

**Total:** 145 tests

---

## API Reference

### Template Loader

```python
from orchestrator.solo_init import load_solo_founder_template

config = load_solo_founder_template("milimo-blueprint/templates/solo-founder.yaml")
```

### Sandbox Initializer

```python
from orchestrator.solo_sandbox import init_solo_sandbox

result = init_solo_sandbox(config)
# Creates policies for all 5 claws
```

### War Room Queue

```python
from orchestrator.solo_warroom import SoloWarRoom

warroom = SoloWarRoom(config)
action = warroom.queue_action("content", "client_proposal_draft", {"title": "Test"})
warroom.approve(action.id)
```

### Inference Router

```python
from orchestrator.solo_privacy import SoloPrivacyRouter

router = SoloPrivacyRouter(config)
decision = router.route("client_facing_drafts")  # Returns "cloud", "local", or "vllm"
```

### Evolution Scheduler

```python
from orchestrator.solo_evolution import schedule_evolution

schedule = schedule_evolution(config, current_activity={"content": 15})
```

### Deep Work Mode

```python
from orchestrator.solo_deep_work import activate_deep_work_mode

result = activate_deep_work_mode(config, "2026-04-15")
```

---

## References

- [Solo Founder Template](../../milimo-blueprint/templates/solo-founder.yaml)
- [Implementation Prompt](../../SOLO_FOUNDER_IMPLEMENTATION_PROMPT.md)
- [Phase 6 Features](./PHASE6_FEATURES.md)
