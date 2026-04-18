# Campus AI Tool Template

**Summary**: 3-claw mesh for developing viral campus utilities and student-focused AI tools.

**Sources**: `milimo-blueprint/templates/campus-ai-tool.yaml`

**Last updated**: 2026-04-15

**Tags**: #template #squad #tech-startups

---

## Overview

The Campus AI Tool template is a lean 3-claw configuration for building AI utilities targeting university students. Optimized for rapid viral growth within campus networks.

**Category**: Tech Startups (AI Era)

**Active Claws**:
- [[build-claw]] — Development and deployment
- [[content-claw]] — Marketing, announcements, outreach
- [[ops-claw]] — User operations, support

**Inactive**: [[analytics-claw]], [[finance-claw]]

---

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| feature_deploy | REVIEW | New features require approval |
| app_announcement | REVIEW | Public announcements need review |
| user_outreach | AUTO | User outreach auto-sends |

---

## Mesh Rules

| Rule | Value | Description |
|------|-------|-------------|
| allow_build_routes | true | Build operations enabled |
| allow_finance_routes | false | Finance messaging disabled |
| allow_analytics_insights | false | No analytics integration |

---

## Escalations

### University Terms Violation Risk

```yaml
trigger: university_terms_violation_risk
action: VETO
message: "Build claw flagged feature as potential violation of campus data guidelines."
```

Features that may violate campus data policies are immediately blocked.

---

## Use Cases

Ideal for:
- Campus-specific AI tools
- Student productivity utilities
- University-focused apps
- Viral campus products

---

## Related Pages

- [[template-overview]] — All available squad templates
- [[solo-founder]] — Solo operator template
- [[build-claw]] — Engineering claw
- [[content-claw]] — Creative claw
- [[ops-claw]] — Operations claw

---

## See Also

- `milimo-blueprint/templates/campus-ai-tool.yaml` — Source configuration
