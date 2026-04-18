# intake-manager

**Summary**: Client inquiry triage and intake processing for Ops Claw.

**Sources**: `milimo-blueprint/orchestrator/ops/intake_manager.py`

**Last updated**: 2026-04-14

**Tags**: #module #ops-claw

---

## Purpose

Intercepts and triages all incoming client inquiries, scoring by budget (40%), scope (30%), and fit (30%).

## Location

**File**: `milimo-blueprint/orchestrator/ops/intake_manager.py`

## Key Classes

### IntakeManager

Handles client intake and triage.

```python
class IntakeManager:
    def __init__(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        inference_client: InferenceClient,
    ):
        self._fs = fs
        self._log = operational_log
        self._client = inference_client

    def triage_inquiry(self, inquiry: ClientInquiry) -> TriageResult:
        """Score and categorize client inquiry."""
        pass

    def get_pricing_before_brief(self, inquiry: ClientInquiry) -> None:
        """Send pricing_query to Finance Claw."""
        pass
```

## Triage Scoring

Weights for scoring:

| Factor | Weight |
|--------|--------|
| Budget | 40% |
| Scope | 30% |
| Fit | 30% |

## Sequencing

Non-negotiable: Send `pricing_query` and receive `pricing_response` before sending `project_brief`.

```python
def process_approved_client(self, client: Client) -> None:
    # 1. Query Finance for pricing
    pricing = self.query_pricing(client.scope)

    # 2. Wait for pricing_response
    response = self.wait_for_pricing_response(timeout=600)  # 10 min

    # 3. Only then send project_brief
    if response:
        self.send_project_brief(client, response.pricing)
```

## Dependencies

- [[ops-init]] — Filesystem
- [[pricing-engine]] — Finance Claw pricing

## Related Pages

- [[ops-claw]] — Parent claw
- [[finance-claw]] — Pricing queries
- [[sequencing-rules]] — Pricing before brief
