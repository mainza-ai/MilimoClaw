# Build Claw

**Summary**: Engineering department that ships code autonomously — PRs, deploys, and error monitoring.

**Sources**:
- `raw/BUILD_CLAW_SPEC.md`
- `milimo-blueprint/roles/build-claw.yaml`

**Last updated**: 2026-04-14

**Tags**: #claw #build

---

## Role

The Build Claw is the **engineering department** of MilimoClaw. It ships code autonomously — reading issues, writing code, opening PRs, and deploying to production.

## Sandbox

**Mount**: `/sandbox/build`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/build/repo/` | Codebase (GitHub mount) | Read-write |
| `/sandbox/build/context/` | Sprint plans, error patterns | Read-write |
| `/sandbox/build/prs/` | PR state tracking | Read-write |
| `/sandbox/build/deployments/` | Deploy state | Read-write |
| `/sandbox/build/docs/` | Changelog, API docs | Read-write |
| `/sandbox/build/memory/` | Filesystem memory | Read-write |
| `/sandbox/build/logs/` | Operational logs | Read-write |
| `/sandbox/analytics/reports/` | Intelligence reports | Read-only |

## What It Does

- Reads open GitHub issues, scores by complexity, proposes sprint plans
- Queries Analytics Claw before sprint planning (5-min timeout then proceeds)
- Writes code from approved issues, opens PRs, runs test suites
- Monitors production error logs and auto-drafts patches for recurring errors
- Runs weekly dependency audits and queues security PRs
- Tracks inference API costs daily and alerts on drift > 15%
- Sends shipping summaries to Content Claw for devlog posts (Friday 17:00)
- Sends deploy completion signals to Ops Claw after every production deploy
- Acknowledges every feature_brief from Ops Claw within 10 minutes

## What It Cannot Do

- Merge any PR without operator HOLD clearance
- Deploy to production without operator HOLD clearance (separate from PR HOLD)
- Share source code or API keys with any other claw via inter-sandbox message
- Read `/sandbox/clients`, `/sandbox/finance`, or `/sandbox/content`

## Two-Stage Approval Flows

### PR Flow

```
Stage 1 — REVIEW:
  Operator reviews code diff and test results
  REVIEW approve → PR moves to HOLD queue (does NOT merge)

Stage 2 — HOLD:
  Operator releases to trigger GitHub merge

If REVIEW approve triggers merge: CRITICAL BUG.
```

### Deploy Flow (Independent of PR Flow)

```
PR merged → deployment staged automatically
Deploy queued as its own separate HOLD
HOLD release → production deployment triggered

A merged PR that has not been deployed waits in deploy HOLD indefinitely.
If PR merge auto-deploys without deploy HOLD: CRITICAL BUG.
```

## Approval Thresholds

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

## Scheduling

| Time | Action |
|------|--------|
| Every 30 min | Error monitoring pass |
| Daily | Inference cost monitoring |
| Monday 08:00 | Dependency security audit |
| Friday 17:00 | Weekly devlog + shipping_summary to Content |
| Sunday 02:35 | Evolution cycle |

## Inter-Claw Messages

### Sent

| Message Type | To | Trigger | SLA |
|--------------|-----|---------|-----|
| `deploy_complete` | Ops | After every production deploy | Immediate |
| `feature_brief_acknowledged` | Ops | Within 10 min of feature_brief | 10 minutes |
| `shipping_summary` | Content | Friday 17:00 (weekly accumulated) | Friday 17:00 |
| `behavior_query` | Analytics | Before sprint planning | 5-min timeout |

### Received

| Message Type | From | Handler |
|--------------|------|---------|
| `feature_brief` | Ops | Acknowledge and plan |
| `retention_signals` | Analytics | Weekly + churn anomaly |
| `behavior_query_response` | Analytics | Include in sprint planning |
| `assistant_query` | Assistant | Return status and state |
| `assistant_task` | Assistant | Execute build-related tasks |

## Sprint Planning Timeout

If `behavior_query_response` does not arrive within 5 minutes:
- Proceed with complexity scores only
- Log the timeout
- Never block sprint planning

## Key Modules

- [[build-init]] — Filesystem initialization
- [[issue-manager]] — GitHub issue handling (5-min Analytics timeout)
- [[code-generator]] — Inference-based code generation
- [[pr-manager]] — PR creation and management
- [[deploy-manager]] — Production deployment (separate HOLD)
- [[error-monitor]] — Production error tracking
- [[cost-monitor]] — Inference cost tracking
- [[dependency-auditor]] — Security dependency checks
- [[doc-maintainer]] — Changelog and documentation
- [[approval-handler]] — Two-stage approval processing
- [[signal-dispatcher]] — Inter-claw message sending (10-min ack)
- [[build-scheduler]] — Scheduled tasks

## Evolution Tools

Tools that emerge autonomously over time:

```
PR style enforcer → Issue complexity scorer v2 → Prompt regression tester →
Cost anomaly detector v2 → Dependency audit runner v2 →
Error pattern classifier v2 → Churn signal correlator → Auto-roadmap drafter
```

## Evolution Schedule

**Sunday 02:35** — Build Claw evolution cycle

Runs after Analytics evolution.

## Spec Document

Full specification: `raw/BUILD_CLAW_SPEC.md`

## Related Pages

- [[message-contracts]] — Message schemas
- [[sequencing-rules]] — PR and deploy approval
- [[approval-thresholds]] — Two-stage flows
- [[ops-claw]] — Feature briefs and deploys
- [[analytics-claw]] — Behavior queries
- [[content-claw]] — Shipping summaries

## See Also

- Implementation prompt: `milimo-claw-docs/prompts/BUILD_CLAW_IMPLEMENTATION_PROMPT.md`
- Policy: `milimo-blueprint/policies/build-sandbox.yaml`
- Tests: `milimo-blueprint/tests/test_build_claw*.py`
