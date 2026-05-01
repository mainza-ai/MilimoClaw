# pricing-engine

**Summary**: Scope cost estimation and pricing response generation.

**Sources**: `milimo-blueprint/orchestrator/finance/pricing_engine.py`

**Last updated**: 2026-04-28

**Tags**: #module #finance-claw

---

## Purpose

Estimates project costs and generates pricing responses for Ops Claw queries.

## Location

**File**: `milimo-blueprint/orchestrator/finance/pricing_engine.py`

## Key Classes

### PricingEngine

Handles pricing queries and estimates.

```python
class PricingEngine:
    def __init__(
        self,
        privacy_router: PrivacyRouter,
        fs: FinanceFilesystemInit,
    ):
        self._router = privacy_router
        self._fs = fs

    def estimate_scope(self, query: PricingQuery) -> PricingEstimate:
        """Estimate scope cost from query."""
        pass

    def generate_response(self, estimate: PricingEstimate) -> PricingResponse:
        """Generate pricing_response message."""
        pass

    def calibrate_from_history(self) -> None:
        """Calibrate from estimate vs actual data."""
        pass
```

## Pricing Query Flow

1. **Receive** `pricing_query` from Ops Claw
2. **Load** pricing rules from `/sandbox/.openclaw/milimo/claws/finance/pricing/rules.json`
3. **Run** scope cost estimation
4. **Check** historical estimates vs actuals
5. **Respond** within 10 minutes
6. **Write** estimate to `pricing/estimates/{project_id}.json`

## Privacy Routing

Scope estimation routes to **Local NIM (NEMOCLAW_MODEL)**:
- `data_type: "scope_cost_estimation"`
- Contains project and client context
- Never sent to cloud in production

## Pricing Rules

Stored in `/sandbox/.openclaw/milimo/claws/finance/pricing/rules.json`:
- Floor rates
- Ceiling rates
- Scope weights
- Complexity multipliers

## Response SLA

Maximum 10 minutes. Respond with `data_quality: "estimated"` if taking longer.

## Evolution

Scope cost estimator v2 evolves at week 3+.

## Dependencies

- [[privacy-router]] — Inference routing
- [[finance-claw]] — Parent claw

## Related Pages

- [[finance-claw]] — Parent claw
- [[invoice-manager]] — Invoice generation
- [[message-contracts]] — pricing_query schema
