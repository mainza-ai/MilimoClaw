# opportunity-scorer

**Summary**: Identifies and scores growth opportunities from trend data.

**Sources**: `milimo-blueprint/orchestrator/analytics/opportunity_scorer.py`

**Last updated**: 2026-04-14

**Tags**: #module #analytics-claw

---

## Purpose

Identifies growth opportunities by analyzing trend data and comparing against squad portfolio.

## Location

**File**: `milimo-blueprint/orchestrator/analytics/opportunity_scorer.py`

## Key Classes

### OpportunityScorer

Scores and prioritizes opportunities.

```python
class OpportunityScorer:
    def __init__(
        self,
        privacy_router: PrivacyRouter,
        fs: AnalyticsFilesystemInit,
    ):
        self._router = privacy_router
        self._fs = fs

    def score_opportunities(self) -> List[Opportunity]:
        """Score all detected opportunities."""
        pass

    def check_high_confidence(self, opportunity: Opportunity) -> bool:
        """Check if confidence > 0.85."""
        return opportunity.confidence > 0.85
```

## Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Potential impact | 40% | Revenue/engagement potential |
| Squad readiness | 35% | Ability to execute |
| Timing | 25% | Market timing score |

## High-Confidence Dispatch

If confidence > 0.85:
- Dispatch `performance_intel` immediately
- Don't wait for weekly report
- Content Claw receives priority signal

## Schedule

Runs daily at 06:00.

## Storage

Opportunities stored at:
`/sandbox/.openclaw-data/milimo/claws/analytics/reports/opportunity-scores.json`

## Evolution

Opportunity scorer v2 evolves at week 9+.

## Dependencies

- [[privacy-router]] — Trend analysis inference
- [[report-generator]] — Report integration

## Related Pages

- [[analytics-claw]] — Parent claw
- [[evolution-cycle]] — Tool evolution
- [[report-generator]] — Weekly reports
