# Forward Projector

Generates 4-week forward projections for key metrics.

## Purpose

Provides forward-looking analytics for planning. Requires minimum 8 weeks of historical data for reliable projections. Always returns something — never refuses to project.

## Constants

- **MIN_WEEKS_FOR_RELIABLE_PROJECTION = 8**
- **PROJECTION_WEEKS = 4**

## Confidence Levels

| Weeks Available | Confidence Level |
|-----------------|------------------|
| < 4 weeks | 0.2 (very low) |
| 4-8 weeks | 0.5 (low) |
| 8-16 weeks | 0.75 (medium) |
| ≥ 16 weeks | 0.90 (high) |

## ForwardProjection Data Class

```python
@dataclass
class ForwardProjection:
    metric: str
    projection_weeks: int
    point_estimate: float
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_level: float
    data_weeks_used: int
    risk_flags: list[str]
    generated_at: str
```

## Methods

| Method | Purpose |
|--------|---------|
| `project_all()` | Generate projections for all metrics |
| `project_revenue()` | Project weekly revenue |
| `project_content_engagement(platform)` | Project engagement by platform |
| `project_delivery_velocity()` | Project PRs merged per week |

## Projection Algorithm

1. Calculate recent average (last 4 weeks)
2. Calculate older average (previous weeks)
3. Compute trend: `(recent - older) / older`
4. Cap trend at ±20%
5. Apply trend to recent average

```python
point_estimate = recent_avg * (1 + trend)
```

## Risk Flags

| Flag | Meaning |
|------|---------|
| `Insufficient historical data` | < 4 weeks of data |
| `Declining trend in recent data` | 3+ consecutive declines |
| `High variance in historical data` | std_dev/mean > 0.4 |
| `No historical data available` | Empty dataset |

## Confidence Intervals

Multipliers based on confidence level:
- 0.2 confidence → 2.5× std_dev
- 0.5 confidence → 2.0× std_dev
- 0.75 confidence → 1.5× std_dev
- 0.90 confidence → 1.2× std_dev

## File Locations

Reads from:
- `/sandbox/analytics/data/revenue/weekly-revenue.jsonl`
- `/sandbox/analytics/data/content-performance/{platform}/`
- `/sandbox/analytics/data/delivery-velocity/velocity.jsonl`

## Relationships

- Used by: [[report-generator]] — Includes projections in weekly reports
- Depends on: `AnalyticsFilesystemInit`
- Related: [[baseline-manager]] — Uses similar data sources

## Source

`milimo-blueprint/orchestrator/analytics/forward_projector.py`
