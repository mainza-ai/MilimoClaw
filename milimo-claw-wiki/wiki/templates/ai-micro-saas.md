# AI Micro-SaaS Template

**Summary**: 4-claw mesh for building and operating commercial Vercel/Railway AI applications.

**Sources**: `milimo-blueprint/templates/ai-micro-saas.yaml`

**Last updated**: 2026-04-15

**Tags**: #template #squad #tech-startups

---

## Overview

The AI Micro-SaaS template configures a full commercial product squad optimized for shipping AI-powered applications on modern deployment platforms.

**Category**: Tech Startups (AI Era)

**Active Claws**:
- [[build-claw]] — Engineering, deploys, error monitoring
- [[ops-claw]] — Client lifecycle, support, delivery
- [[analytics-claw]] — Product analytics, usage insights
- [[finance-claw]] — Invoicing, pricing, revenue tracking

---

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| production_deploy | REVIEW | All production deploys require approval |
| invoice_generation | REVIEW | Invoices need squad review |
| architecture_decision | REVIEW | Major technical decisions require sign-off |
| support_reply | AUTO | Support responses auto-send |
| performance_report | AUTO | Analytics reports auto-publish |

---

## Mesh Rules

| Rule | Value | Description |
|------|-------|-------------|
| allow_finance_routes | true | Finance messaging enabled |
| allow_analytics_insights | true | Analytics integration active |
| allow_build_routes | true | Build/deploys allowed |

---

## Escalations

### Security Vulnerability

```yaml
trigger: security_vulnerability_detected
action: VETO
message: "Build claw detected security flaw. Halting all deploys until patched."
```

Any security finding from [[build-claw]] immediately halts all deployment activity.

### API Cost Anomaly

```yaml
trigger: api_cost_anomaly
action: HOLD
message: "Cost per user exceeded margin threshold. Review required."
```

When API costs exceed expected margins, operations pause for review.

---

## Use Cases

Ideal for:
- AI SaaS products on Vercel/Railway
- Paid AI utilities and tools
- Commercial API wrappers
- AI-powered automation platforms

---

## Related Pages

- [[template-overview]] — All available squad templates
- [[solo-founder]] — Solo operator template (all 6 claws)
- [[build-claw]] — Engineering claw
- [[ops-claw]] — Operations claw
- [[analytics-claw]] — Intelligence claw
- [[finance-claw]] — Financial claw

---

## See Also

- `milimo-blueprint/templates/ai-micro-saas.yaml` — Source configuration
