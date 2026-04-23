# Claw Schema

Defines the structure every role blueprint must follow.

## Purpose

Each role blueprint extends the base NemoClaw blueprint with claw-specific configuration for filesystem, egress, inference, inter-claw messaging, and approval policies.

## File Location

`milimo-blueprint/claw-schema.yaml`

## Required Fields

Every claw role blueprint must define:
- `role` — content | ops | analytics | finance | build | assistant
- `display_name` — Human-readable name
- `description` — What this claw does
- `filesystem_mount` — Primary sandbox directory
- `egress_policy` — Network egress allowlist name
- `inference_routing` — Data type → backend mapping
- `inter_claw_policy` — Message type contracts
- `approval_thresholds` — Per-action approval modes

## Valid Roles

| Role | Description |
|------|-------------|
| `content` | Creative content generation |
| `ops` | Operations and client management |
| `analytics` | Intelligence and reporting |
| `finance` | Invoicing and pricing |
| `build` | Engineering and deployment |
| `assistant` | User interface and coordination |

## Filesystem Rules

- **Mount prefix**: `/sandbox/`
- **Isolation**: Landlock (kernel-enforced)
- **Cross-mounts**: Allowed, read-only

## Inference Backends

| ID | Name | Use Case |
|----|------|----------|
| `cloud` | NVIDIA Cloud Nemotron 120B | Max quality, client-facing |
| `local-nim` | Local NIM on RTX | Private data stays on device |
| `local-vllm` | Local vLLM | Tightest isolation, lightweight |

## Approval Modes

| Mode | Description | Human Required |
|------|-------------|----------------|
| `auto` | Execute immediately, log for review | No |
| `review` | Draft, queue for approval | Yes |
| `hold` | Pause, requires explicit release | Yes |
| `veto` | Any squad member can block | Yes |

## Message Categories

- `brief` — Project/creative briefs
- `query` — Data requests
- `response` — Query responses
- `signal` — Alerts (deadline, risk, anomaly)
- `deliverable` — Completed work products
- `summary` — Periodic reports

## Relationships

- Used by: All role blueprints
- Validates: Template YAML files
- Related: [[mesh-config]] — Message routing

## Source

`milimo-blueprint/claw-schema.yaml`
