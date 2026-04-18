# Event Promotion Template

**Summary**: Fast-paced 3-claw mesh for promoting events, managing attendee communications, and tracking engagement.

**Sources**: `milimo-blueprint/templates/event-promotion.yaml`

**Last updated**: 2026-04-15

**Tags**: #template #squad #marketing

---

## Overview

The Event Promotion template is optimized for time-sensitive event marketing. Supports rapid campaign execution and real-time engagement tracking.

**Category**: Marketing & Sales

**Active Claws**:
- [[content-claw]] — Event promotion, campaigns, announcements
- [[ops-claw]] — Attendee management, communications
- [[analytics-claw]] — Engagement tracking, ticket analytics

**Inactive**: [[finance-claw]], [[build-claw]]

---

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| deliverable | REVIEW | Event materials need review |
| campaign_blast | REVIEW | Campaign blasts require approval |
| intake_questionnaire | AUTO | Event intake auto-processes |
| intelligence_report | AUTO | Engagement reports auto-publish |
| anomaly_alert | REVIEW | Engagement anomalies flagged |

---

## Mesh Rules

| Rule | Value | Description |
|------|-------|-------------|
| allow_finance_routes | false | Finance messaging disabled |
| allow_analytics_insights | true | Real-time engagement tracking |

---

## Event Timeline Workflow

```
T-30 days: Content creates promotional campaign (REVIEW)
T-14 days: Campaign blast to mailing lists (REVIEW)
T-7 days:  Content creates reminder content (REVIEW)
T-1 day:   Ops sends final attendee communications (AUTO)
T+0:       Analytics tracks live engagement (AUTO)
T+1:       Analytics generates event report (AUTO)
```

---

## Use Cases

Ideal for:
- Event promotion agencies
- Conference marketing
- Webinar and virtual event promotion
- Local event marketing

---

## Related Pages

- [[template-overview]] — All available squad templates
- [[solo-founder]] — Solo operator template
- [[content-claw]] — Creative claw
- [[ops-claw]] — Operations claw
- [[analytics-claw]] — Intelligence claw

---

## See Also

- `milimo-blueprint/templates/event-promotion.yaml` — Source configuration
