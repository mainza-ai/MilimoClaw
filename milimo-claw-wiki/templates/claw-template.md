# Claw Template

**Summary**: Template for documenting a MilimoClaw agent.

**Last updated**: 2026-04-14

**Tags**: #template #claw

---

# {{claw-name}}

**Summary**: One-line description of this claw's role.

**Sources**:
- `milimo-claw-docs/reference/MILIMO_CLAW_{{CLAW}}_CLAW_SPEC.md`
- `milimo-blueprint/roles/{{claw}}-claw.yaml`

**Last updated**: YYYY-MM-DD

**Tags**: #claw #{{claw-name}}

---

## Role

Describe the claw's primary function and responsibilities.

## Sandbox

**Mount**: `/sandbox/{{mount-path}}`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/{{mount}}/` | Primary workspace | Read-write |

## What It Does

- Responsibility 1
- Responsibility 2
- Responsibility 3

## What It Cannot Do

- Restriction 1
- Restriction 2
- Restriction 3

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Action name | REVIEW/HOLD/AUTO | Conditions |

## Inter-Claw Messages

### Sent

| Message Type | To | Trigger |
|--------------|-----|---------|
| `message_type` | recipient-claw | When triggered |

### Received

| Message Type | From | Handler |
|--------------|------|---------|
| `message_type` | sender-claw | How handled |

## Key Modules

- [[{{claw}}-init]] — Filesystem initialization
- [[{{claw}}-scheduler]] — Scheduled tasks
- [[module-name]] — Description

## Evolution Tools

Tools that emerge autonomously over time:

1. Tool 1 → Tool 2 → Tool 3

## Spec Document

Full specification: `raw/MILIMO_CLAW_{{CLAW}}_CLAW_SPEC.md`

## Related Pages

- [[message-contracts]]
- [[approval-thresholds]]
- [[sandbox-isolation]]
- [[{{related-claw}}-claw]]

## See Also

- Implementation prompt: `milimo-claw-docs/prompts/{{CLAW}}_CLAW_IMPLEMENTATION_PROMPT.md`
