# ADR 003: Milimo-Core Packaging Strategy

**Status**: Accepted
**Date**: 2026-06-27
**Deciders**: Mainza Kangombe

## Context

`milimo-core` is the shared orchestrator library extracted from `milimo-blueprint/orchestrator/`. It contains all 6 claws + shared infrastructure. The packaging decision affects:
- Dockerfile build process
- CI/CD pipeline
- Local development workflow
- External adoption potential

## Decision

**Local editable install (`pip install -e`) for development; PyPI release for distribution post-Phase 5.**

## Implementation

### Development (Current)
- `milimo-core/` is a local package with `pyproject.toml`
- Dockerfile: `COPY ../milimo-core/ /opt/milimo-core/ && pip install /opt/milimo-core/`
- Local dev: `pip install -e ../milimo-core` in project venv
- Root `pyproject.toml` uses `uv` workspace:
  ```toml
  [tool.uv.workspace]
  members = ["milimo-core", "milimo-blueprint", "milimo-hermes-plugin"]
  ```

### Distribution (Post-Phase 5)
- Publish to PyPI when: API stable, `CHANGELOG.md` written, semantic versioning established, external interest observed
- Dockerfile would change to: `pip install milimo-core>=0.2.0`
- Version pinned in `milimo-compatibility.json`

## Rationale

1. **No premature versioning burden** — Publishing to PyPI before API stability creates maintenance overhead (semver, deprecation windows, release notes) with no benefit. The HeartMuLa pattern works when the package is genuinely ready.

2. **CI/CD works identically** — Both Docker build and CI install from local source via editable install. No PyPI credentials needed in CI.

3. **External adoption signal** — Publishing to PyPI signals "this is a stable library others can build on." That happens after Phase 5 when the protocol interfaces are proven.

## Consequences

- `milimo-core` version stays at `0.1.0-dev` until Phase A complete, then tagged `v0.1.0`
- `CHANGELOG.md` written **before** tagging, not after
- Workspace layout resolves `uv.lock` conflicts

## Related ADRs
- ADR 001: Subagent Isolation Model
- ADR 004: Sandbox Naming
