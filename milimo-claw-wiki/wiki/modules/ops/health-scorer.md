# health-scorer

**Summary**: Client relationship health scoring and monitoring.

**Sources**: `milimo-blueprint/orchestrator/ops/health_scorer.py`

**Last updated**: 2026-04-14

**Tags**: #module #ops-claw

---

## Purpose

Scores client relationship health and sends weekly health signals to Analytics Claw.

## Location

**File**: `milimo-blueprint/orchestrator/ops/health_scorer.py`

## Key Classes

### HealthScorer

Calculates and tracks client health scores.

```python
class HealthScorer:
    def __init__(
        self,
        fs: OpsFilesystemInit,
        mesh: MeshClient,
    ):
        self._fs = fs
        self._mesh = mesh

    def score_client(self, client_id: str) -> HealthScore:
        """Calculate health score for client (0-10)."""
        pass

    def check_all_clients(self) -> List[HealthScore]:
        """Score all active clients."""
        pass

    def send_weekly_signal(self) -> None:
        """Send client_health_signal to Analytics."""
        pass
```

## Health Score Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Response time | 30% | Time to respond to messages |
| Revision frequency | 25% | How often revisions requested |
| Communication sentiment | 25% | Sentiment analysis of comms |
| Scope adherence | 20% | Staying within agreed scope |

## Scoring Thresholds

- **Score ≥ 7.0**: Healthy client
- **Score 6.0-7.0**: Monitor closely
- **Score < 6.0**: Alert to War Room, send `client_health_signal`

## Weekly Signal

Every week, regardless of score:
- Sends `client_health_signal` to Analytics Claw
- Includes: client_id, health_score, health_factors, recommended_action

## Dependencies

- [[project-manager]] — Project context
- [[analytics-claw]] — Signal recipient

## Related Pages

- [[ops-claw]] — Parent claw
- [[analytics-claw]] — Signal recipient
- [[message-contracts]] — client_health_signal schema
