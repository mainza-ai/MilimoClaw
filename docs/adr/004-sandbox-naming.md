# ADR 004: Sandbox Naming Convention

**Status**: Accepted
**Date**: 2026-06-27
**Deciders**: Mainza Kangombe

## Context

NemoClaw prevents same-name reuse when an existing sandbox uses a different agent. If an operator previously ran `nemohermes onboard` (creating sandbox `hermes`) and later installs MilimoClaw, the default sandbox name `hermes` would collide.

## Decision

**Default sandbox name: `milimo-hermes`** (not `hermes`).

## Implementation

- Dockerfile: `ENV NEMOCLAW_SANDBOX_NAME=milimo-hermes`
- Install script: `--name milimo-hermes` passed to `nemohermes onboard`
- Blueprint: `agent_profiles.hermes-milimo.sandbox.name = "milimo-hermes"`
- Documentation: Explicitly call out collision avoidance

## Rationale

1. **Prevents first-run failure** — Operators who tried NemoClaw quickstart get a working Milimo install without manual intervention.

2. **Enables side-by-side profiles** — `milimo-openclaw-sandbox` (OpenClaw) and `milimo-hermes` (Hermes) can run simultaneously. `nemoclaw list` shows agent type for each.

3. **Brand consistency** — `milimo-*` prefix identifies MilimoClaw sandboxes in multi-project environments.

## Related ADRs
- ADR 001: Subagent Isolation Model
- ADR 003: Milimo-Core Packaging
