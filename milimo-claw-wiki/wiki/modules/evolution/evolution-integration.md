# Evolution Integration

**Summary**: Scheduler that orchestrates the weekly evolution cycle for all 5 claws, reading metrics and triggering tool deployment.

**Sources**: `milimo-blueprint/orchestrator/evolution_integration.py`

**Last updated**: 2026-04-17

**Tags**: #evolution #scheduler #orchestration

---

## Overview

`EvolutionIntegration` connects the [[evolution-cycle]] with the rest of MilimoClaw. It registers evolution cycles for all claws, uses the real `NvidiaInferenceClient` (not mock), reads metrics from `MetricsCollector`, and runs on a configurable schedule (default: weekly).

## Key Class

### EvolutionIntegration

```python
from evolution_integration import EvolutionIntegration

integration = EvolutionIntegration(
    squad_id="my-squad",
    blueprint_dir=Path("/path/to/blueprint"),
    interval_days=7,
)
integration.start()
```

**Methods**:

| Method | Description |
|--------|-------------|
| `register_claw(claw_role, log_dir)` | Register evolution cycle for a specific claw |
| `start()` | Start scheduler with periodic triggering |
| `stop()` | Stop the evolution scheduler |
| `trigger_now(claw_role, dry_run)` | Manually trigger evolution cycles |
| `get_metrics_summary()` | Get performance metrics for all claws |
| `get_status()` | Current scheduler status |

## Configuration

Default `EvolutionConfig` values when registering claws:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `cycle_interval_days` | 7 | Weekly runs |
| `window_days` | 7 | Analysis window |
| `minimum_actions` | 20 | Minimum actions before evolution |
| `cross_signal_lookback_days` | 14 | Cross-claw signal lookback |
| `min_confidence` | 0.6 | Minimum pattern confidence |
| `max_patterns` | 5 | Max patterns per cycle |
| `backtest_window_weeks` | 4 | Backtest history length |
| `min_improvement_percent` | 5.0 | Minimum improvement threshold |
| `max_tools_per_claw` | 30 | Tool limit per claw |
| `require_proposal_approval` | `True` | Evolution changes need approval |
| `notify_war_room` | `True` | Notify War Room of changes |

## Default Registered Claws

On `start()`, registers cycles for:
- `build`
- `content`
- `ops`
- `analytics`
- `finance`

## Startup Behavior

1. Register all 5 claw evolution cycles
2. Check for missed cycles during downtime
3. If no history exists, run initial dry-run
4. If last run was > `interval_days + 1` ago, trigger immediately
5. Schedule next run via `threading.Timer`

## Trigger Now

```python
# Trigger all claws
results = integration.trigger_now()

# Trigger specific claw
results = integration.trigger_now(claw_role="content")

# Dry run (validate but don't deploy)
results = integration.trigger_now(claw_role="build", dry_run=True)
```

**Returns**: `list[CycleResult]` with:
- `stage_reached` — How far the cycle got
- `proposal` — Tool proposal if created
- `tool_deployed` — Deployed tool with `performance_delta`
- `skipped_reason` — Why cycle was skipped

## Metrics Summary

```python
summary = integration.get_metrics_summary()
# Returns:
# {
#   "build": { "total_actions": 150, "avg_approval_rate": 0.82, ... },
#   "content": { ... },
#   ...
# }
```

Reads from `~/.milimo/metrics/{claw_role}/` via `MetricsCollector`.

## Status

```python
status = integration.get_status()
# Returns:
# {
#   "running": True,
#   "squad_id": "my-squad",
#   "interval_days": 7,
#   "registered_claws": ["build", "content", "ops", "analytics", "finance"],
#   "total_cycles_run": 12,
#   "last_cycle": { ... },
#   "scheduler_status": { ... }
# }
```

## Dependencies

- `evolution_cycle.EvolutionCycle` — Core evolution logic
- `evolution_cycle.EvolutionScheduler` — Cycle scheduling
- `inference_client.NvidiaInferenceClient` — Real LLM inference
- `metrics_collector.MetricsCollector` — Performance metrics

## Related Pages

- [[evolution-cycle]] — Sunday 5-stage evolution pipeline
- [[tool-generator]] — LLM-based tool code generation
- [[sandbox-runner]] — Isolated backtest execution
- [[metrics-collector]] — Performance metrics collection

## See Also

- `milimo-blueprint/orchestrator/evolution_integration.py` — Source file
- `milimo-blueprint/orchestrator/evolution/evolution_cycle.py` — Evolution cycle logic
