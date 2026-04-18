# Freelance Collective Template

**Summary**: 4-claw mesh for solo dev/design collectives managing pipeline, quoting, and client operations.

**Sources**: `milimo-blueprint/templates/freelance-collective.yaml`

**Last updated**: 2026-04-15

**Tags**: #template #squad #services

---

## Overview

The Freelance Collective template supports distributed freelance teams with a focus on pipeline management, client acquisition, and financial operations.

**Category**: Services & Operations

**Active Claws**:
- [[content-claw]] — Portfolio, proposals, marketing materials
- [[ops-claw]] — Client management, project delivery
- [[finance-claw]] — Quoting, invoicing, payments
- [[analytics-claw]] — Pipeline analytics, utilization

**Inactive**: [[build-claw]]

---

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| deliverable | REVIEW | Client work requires review |
| proposal | REVIEW | Proposals need approval |
| invoice | REVIEW | Invoices require sign-off |
| intake_questionnaire | AUTO | Client intake auto-processes |
| intelligence_report | AUTO | Pipeline reports auto-publish |
| anomaly_alert | REVIEW | Utilization anomalies flagged |

---

## Mesh Rules

| Rule | Value | Description |
|------|-------|-------------|
| allow_finance_routes | true | Finance operations enabled |
| allow_analytics_insights | true | Pipeline analytics active |

---

## Collective Workflow

```
Lead → Ops processes intake (AUTO)
  ↓
Quote → Finance generates quote (REVIEW)
  ↓
Proposal → Content creates proposal (REVIEW)
  ↓
Project → Ops manages delivery (REVIEW for deliverables)
  ↓
Invoice → Finance sends invoice (REVIEW)
  ↓
Analytics → Analytics tracks utilization (AUTO)
```

---

## Use Cases

Ideal for:
- Freelance developer collectives
- Design collaboratives
- Consulting partnerships
- Distributed service teams

---

## Related Pages

- [[template-overview]] — All available squad templates
- [[solo-founder]] — Solo operator template
- [[content-claw]] — Creative claw
- [[ops-claw]] — Operations claw
- [[finance-claw]] — Financial claw
- [[analytics-claw]] — Intelligence claw

---

## See Also

- `milimo-blueprint/templates/freelance-collective.yaml` — Source configuration
