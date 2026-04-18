# Payment Risk Scorer

Scores client payment risk before invoice is shown to operator.

## Purpose

Analyzes client payment history to assess risk. Provides risk scores before invoice presentation. Purely internal — no external API calls.

## Risk Score Scale

| Score | Risk Level | Meaning |
|-------|------------|---------|
| 7.0–10.0 | `low` | Reliable payer |
| 4.0–7.0 | `medium` | Moderate risk |
| 0.0–4.0 | `high` | Payment concerns |

## PaymentRiskScore Data Class

```python
@dataclass
class PaymentRiskScore:
    client_id: str
    score: float
    risk_level: str
    factors: list[str]
    invoices_analyzed: int
    on_time_rate: float
    avg_days_late: float
    overdue_count: int
    data_quality: str
```

## Methods

| Method | Purpose |
|--------|---------|
| `score(client_id)` | Calculate payment risk score |

## Scoring Algorithm

1. Load client payment history from `payment-events.log`
2. If no history: return neutral score (5.0, "medium", "no_history")
3. Calculate metrics:
   - `on_time_rate` — Payments within 14 days
   - `avg_days_late` — Average delay beyond 14 days
   - `overdue_count` — Overdue events
4. Send to inference with `data_type="payment_risk_scoring"`
5. On inference failure: use rule-based scoring

### Rule-Based Scoring

```python
base = on_time_rate * 10
if overdue_count >= 3: base -= 3
elif overdue_count >= 2: base -= 2
elif overdue_count >= 1: base -= 1
return max(0.0, min(10.0, base))
```

## Risk Factors

Generated as plain-English explanations:
- "Low on-time rate (60%)"
- "Multiple overdue invoices (3)"
- "Average 12 days late"
- "Good payment history" (default when no issues)

## Data Quality

| Quality | Meaning |
|---------|---------|
| `complete` | Full payment history available |
| `no_history` | New client, no payment data |

## Dependencies

- `PaymentEventsLog` — Payment history storage
- `InferenceClient` — LLM inference

## Relationships

- Used by: [[invoice-generator]] — Risk assessment before invoice creation
- Reads from: [[payment-events-log]] — Payment history

## Source

`milimo-blueprint/orchestrator/finance/payment_risk_scorer.py`
