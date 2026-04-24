# Solo Evolution

**Summary**: Weekly self-evolution scheduler for solo founders with staggered timing and activity thresholds.

**Sources**: `milimo-blueprint/orchestrator/solo_evolution.py`

**Last updated**: 2026-04-23

**Tags**: #solo #evolution #scheduler

---

## Purpose

Schedules and manages per-claw evolution cycles with staggered timing and activity thresholds.

## Evolution Schedule

Default staggered timing (Sunday):

| Claw | Time |
|------|------|
| Analytics baseline | 01:00 |
| Analytics report | 02:00 |
| Content | 02:05 |
| Ops | 02:15 |
| Analytics evolution | 02:25 |
| Build | 02:35 |
| Finance | 03:00 |
| Assistant | 03:15 |

## Activity Thresholds

Each claw must meet minimum activity before evolving:

| Claw | Threshold Field | Default |
|------|------------------|---------|
| Content | min_approved_posts | 10 |
| Ops | min_client_interactions | 5 |
| Analytics | min_data_weeks | 2 |
| Finance | min_invoices | 3 |
| Build | min_prs_merged | 3 |
| Assistant | min_queries_dispatched | 15 |

### Content Claw Additional Thresholds

- `rejected_drafts_min`: 3
- `performance_data_weeks_min`: 1

## Main Functions

| Function | Purpose |
|----------|---------|
| `schedule_evolution()` | Calculate next evolution schedule |
| `parse_evolution_schedule()` | Extract per-claw times from config |
| `check_claw_evolution_ready()` | Check if specific claw can evolve |
| `check_content_evolution_thresholds()` | Content-specific threshold check |
| `get_evolution_summary()` | Human-readable summary |

## EvolutionSchedule Data Class

```python
@dataclass
class EvolutionSchedule:
    claw: str
    enabled: bool
    day: str
    time: str
    threshold_field: str
    threshold_value: int
    performance_threshold: int
    next_run: datetime | None
```

## EvolutionStatus Data Class

```python
@dataclass
class EvolutionStatus:
    claw: str
    can_evolve: bool
    reason: str
    current_activity: int
    required_activity: int
    last_evolution: datetime | None
```

## Next Run Calculation

```python
days_until = (target_day - now.weekday()) % 7
if days_until == 0 and target_time <= now:
    days_until = 7
next_run = now + timedelta(days=days_until)
```

## Relationships

- Uses: [[evolution-config]] — Global settings
- Uses: [[evolution-cycle]] — Execution logic
- Related: [[solo-init]] — Configuration loading
- Related: [[assistant-lucy]] — Assistant evolution cycle

## Source

`milimo-blueprint/orchestrator/solo_evolution.py`
