# Evolution Cycle

**Summary**: Sunday 5-stage evolution pipeline that generates new tools.

**Sources**:
- `milimo-blueprint/orchestrator/evolution_cycle.py`
- `raw/AGENTS.md`

**Last updated**: 2026-04-14

**Tags**: #evolution #tools #self-improvement

---

## Overview

Every claw runs an Evolution Cycle every Sunday. The system observes its own behavior, identifies patterns, and generates new tools to improve performance.

## Schedule

Staggered so each claw runs on fresh Analytics intelligence:

| Time | Action |
|------|--------|
| Sunday 01:00 | Analytics: baseline recalculation |
| Sunday 02:00 | Analytics: weekly intelligence report |
| Sunday 02:05 | Content: evolution cycle |
| Sunday 02:15 | Ops: evolution cycle |
| Sunday 02:25 | Analytics: evolution cycle |
| Sunday 02:35 | Build: evolution cycle |
| Sunday 03:00 | Finance: weekly revenue summary + evolution cycle |

Analytics runs first. Every other claw's cycle reads the fresh report. Finance runs last — uses revenue summary just generated.

## The 5-Stage Cycle

### Stage 1: OBSERVE

Review week's logs, approval decisions, outcomes.

```python
def observe(self) -> ObservationData:
    logs = self._read_weekly_logs()
    approvals = self._read_approval_decisions()
    outcomes = self._read_outcomes()
    return ObservationData(logs, approvals, outcomes)
```

### Stage 2: IDENTIFY

Surface recurring patterns from operational history.

```python
def identify_patterns(self, observations: ObservationData) -> list[Pattern]:
    # Use inference to identify patterns
    patterns = self._pattern_detector.detect(observations)
    return [p for p in patterns if p.confidence > 0.7]
```

### Stage 3: PROPOSE

Nominate one new tool for the strongest pattern.

```python
def propose_tool(self, pattern: Pattern) -> ToolProposal:
    # Generate tool specification
    spec = self._tool_proposal.generate(pattern)
    return ToolProposal(
        name=spec.name,
        pattern=pattern,
        spec=spec,
    )
```

### Stage 4: BUILD

Generate via inference, test against 4 weeks of history.

```python
def build_tool(self, proposal: ToolProposal) -> Tool:
    # Generate tool code
    code = self._tool_builder.generate(proposal.spec)

    # Test against historical data
    test_result = self._test_against_history(code, weeks=4)

    # Must outperform baseline by 5% to qualify
    if test_result.improvement < 0.05:
        raise EvolutionError("Tool does not meet threshold")

    return Tool(code=code, test_result=test_result)
```

### Stage 5: DEPLOY

Activate, version blueprint, log to War Room evolution panel.

```python
def deploy_tool(self, tool: Tool) -> None:
    # Register tool
    self._tool_registry.register(tool)

    # Version blueprint
    self._blueprint_manager.version_bump()

    # Log to War Room
    self._log_evolution(tool)
```

## Minimum Data Thresholds

Before first evolution, each claw needs:

| Claw | Threshold |
|------|-----------|
| Content | 10 approved posts + 3 rejected drafts + 1 week performance data |
| Ops | 5 client interactions + 3 projects + 2 weeks comms data |
| Analytics | 3 weeks signal data + 1 revenue_summary + 1 health_signal |
| Finance | 3 invoices + 2 completed projects + 4 weeks expense data |
| Build | 5 merged PRs + 3 sprints + 2 deploys + 4 weeks cost data |

## Evolution Tools by Claw

### Content Claw

```
Style descriptor → Tone classifier → Approval predictor →
Platform calibrator → Timing optimizer → A/B variant engine →
Client voice adapter → Trend injector
```

### Ops Claw

```
Client triage scorer → Brief quality checker → Deadline risk predictor →
Communication tone calibrator → Scope creep detector v2 →
Relationship health scorer v2
```

### Analytics Claw

```
Engagement baseline model → Anomaly detector v2 → Opportunity scorer v2 →
Retention correlator → Competitor signal tracker → Forward projection engine v2
```

### Finance Claw

```
Scope cost estimator v2 → Pricing floor guardian → Payment risk scorer v2 →
Margin tracker v2 → Tax category classifier v2 → Rate optimization advisor v2
```

### Build Claw

```
PR style enforcer → Issue complexity scorer v2 → Prompt regression tester →
Cost anomaly detector v2 → Dependency audit runner v2 →
Error pattern classifier v2 → Churn signal correlator → Auto-roadmap drafter
```

## Related Pages

- [[tool-generation]] — Tool builder details
- [[pattern-detection]] — Pattern identification
- [[solo-founder]] — Evolution schedule config
