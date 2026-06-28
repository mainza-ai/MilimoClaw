# ADR 002: War Room for Hermes Profile

**Status**: Accepted
**Date**: 2026-06-27
**Deciders**: Mainza Kangombe

## Context

The War Room is the primary operator interface for MilimoClaw — showing HOLD queue, claw status, cost guard, and evolution cycle state. In OpenClaw profile, it's a TUI widget. Hermes profile has a web dashboard at port 18789.

## Decision

**Option B**: Build a standalone War Room HTML page served at `/warroom` endpoint, not embedded in the Hermes dashboard TUI tab.

## Rationale

1. **`/opt/hermes/ui-tui` is not a public API** — NemoClaw builds dashboard assets into the sandbox image. The internal bundle format is undocumented and can change without notice. Building against it creates fragile coupling.

2. **htmx + partial HTML is simpler** — The War Room polls `milimo_warroom` tool for live state. htmx handles this with zero build step:
   ```html
   <div hx-get="/warroom/status" hx-trigger="every 5s" hx-swap="innerHTML">
   <button hx-post="/warroom/approve" hx-vals='{"item_id": "INV-001"}'>
   ```

3. **Deployment simplicity** — Single static HTML file served from `/opt/hermes/warroom/`. No npm, no bundler, no build step. Works identically on local and headless remote (via `CHAT_UI_URL`).

4. **Operator preference** — Solo founders typically keep War Room open in a dedicated browser tab alongside the Hermes dashboard. Separate tab = no context switching.

## Implementation

- `milimo-hermes-plugin/warroom/warroom.html` — standalone HTML with htmx CDN include
- Dockerfile copies to `/opt/hermes/warroom/`
- Hermes API serves static files from `/opt/hermes/warroom/`
- Tools: `milimo_warroom` returns JSON; partial HTML fragments for htmx swaps

## Related ADRs
- ADR 001: Subagent Isolation Model (delegation model)
- ADR 003: Milimo-Core Packaging (local editable install)
