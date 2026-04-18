# Design Studio Template

**Summary**: 3-claw mesh focused on client deliverables, formal proposals, and financial operations.

**Sources**: `milimo-blueprint/templates/design-studio.yaml`

**Last updated**: 2026-04-15

**Tags**: #template #squad #creative

---

## Overview

The Design Studio template is a 3-claw configuration emphasizing creative work, client management, and strict financial oversight. Includes veto power for high-value invoices.

**Category**: Creative & Content

**Active Claws**:
- [[content-claw]] — Creative deliverables, design work
- [[ops-claw]] — Client management, project delivery
- [[finance-claw]] — Invoicing, payments, pricing

**Inactive**: [[analytics-claw]], [[build-claw]]

---

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| deliverable | REVIEW | Client-facing creative needs review |
| invoice_generation | REVIEW | Invoices require approval |
| invoice_send | VETO | Any squad member can block invoice |
| payment_alert | AUTO | Payment alerts surface immediately |
| proposal | REVIEW | Proposals tying scope to pricing |

---

## Mesh Rules

| Rule | Value | Description |
|------|-------|-------------|
| allow_finance_routes | true | Finance operations enabled |
| allow_analytics_insights | false | No behavioral analytics |

---

## Escalations

### High-Value Invoice

```yaml
trigger: invoice_over_1000
action: HOLD
message: "High-value invoice requires unanimous squad sign-off."
```

Invoices over $1000 require consensus before sending.

---

## Veto Power

The `invoice_send: VETO` threshold means:
- Any single squad member can block an invoice
- Requires unanimous approval to proceed
- Protects against billing errors or disputes

---

## Use Cases

Ideal for:
- Design agencies
- Brand studios
- Freelance design collectives
- Creative consultancies

---

## Related Pages

- [[template-overview]] — All available squad templates
- [[solo-founder]] — Solo operator template
- [[content-claw]] — Creative claw
- [[ops-claw]] — Operations claw
- [[finance-claw]] — Financial claw

---

## See Also

- `milimo-blueprint/templates/design-studio.yaml` — Source configuration
