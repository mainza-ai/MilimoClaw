# Content Agency Template

**Summary**: 3-claw mesh optimized for social media management, copywriting, and marketing campaigns.

**Sources**: `milimo-blueprint/templates/content-agency.yaml`

**Last updated**: 2026-04-15

**Tags**: #template #squad #creative

---

## Overview

The Content Agency template configures a mesh focused on content creation, client management, and campaign analytics. Designed for agencies managing multiple client brands.

**Category**: Creative & Content

**Active Claws**:
- [[content-claw]] — Content creation, copywriting, social media
- [[ops-claw]] — Client management, intake, delivery
- [[analytics-claw]] — Campaign performance, insights

**Inactive**: [[finance-claw]], [[build-claw]]

---

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| deliverable | REVIEW | All client-facing work requires review |
| proposal | REVIEW | Client proposals need approval |
| intake_questionnaire | AUTO | Intake forms auto-process |
| intelligence_report | AUTO | Analytics reports auto-publish |
| anomaly_alert | REVIEW | Performance anomalies need attention |

---

## Mesh Rules

| Rule | Value | Description |
|------|-------|-------------|
| allow_finance_routes | false | Finance messaging disabled |
| allow_analytics_insights | true | Content-Analytics integration |

---

## Client Workflow

```
Intake → Ops processes intake_questionnaire (AUTO)
  ↓
Proposal → Content creates proposal (REVIEW required)
  ↓
Brief → Content generates content (REVIEW for deliverables)
  ↓
Delivery → Ops delivers to client (REVIEW required)
  ↓
Analytics → Analytics tracks performance (AUTO)
```

---

## Use Cases

Ideal for:
- Social media agencies
- Content marketing firms
- Copywriting services
- Brand management consultancies

---

## Related Pages

- [[template-overview]] — All available squad templates
- [[solo-founder]] — Solo operator template
- [[content-claw]] — Creative claw
- [[ops-claw]] — Operations claw
- [[analytics-claw]] — Intelligence claw

---

## See Also

- `milimo-blueprint/templates/content-agency.yaml` — Source configuration
