# Ground Truth Hierarchy

**Summary**: Document authority order for resolving conflicts.

**Sources**:
- `raw/AGENTS.md`
- `CLAUDE.md`

**Last updated**: 2026-04-14

**Tags**: #reference #hierarchy #authority

---

## Hierarchy

When documents conflict, this order determines which is authoritative:

| Priority | Source | Authority | Notes |
|----------|--------|-----------|-------|
| 1 | **Claw spec documents** | Internal claw behavior | Defines exact behavior for each claw |
| 2 | **Solo template spec** | Cross-claw coordination | Defines message sequencing, scheduling |
| 3 | **Template YAML files** | Configuration values | Implements specs with actual values |
| 4 | **AGENTS.md** | Quick reference summary | Summarizes specs, doesn't override |
| 5 | **Wiki pages** | Synthesis and navigation | Explains concepts, cites higher authority |
| 6 | **Code** | Implementation reality | Should match specs; if not, it's a bug |

---

## Spec Documents

Ground truth for each claw:

| Spec | File |
|------|------|
| Content Claw | `milimo-claw-docs/reference/MILIMO_CLAW_CONTENT_CLAW_SPEC.md` |
| Ops Claw | `milimo-claw-docs/reference/MILIMO_CLAW_OPS_CLAW_SPEC.md` |
| Analytics Claw | `milimo-claw-docs/reference/MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md` |
| Finance Claw | `milimo-claw-docs/reference/MILIMO_CLAW_FINANCE_CLAW_SPEC.md` |
| Build Claw | `milimo-claw-docs/reference/MILIMO_CLAW_BUILD_CLAW_SPEC.md` |
| Solo Template | `milimo-claw-docs/reference/MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md` |

All symlinked in `raw/` folder for wiki reference.

---

## Conflict Resolution

```
If wiki page conflicts with spec → Spec wins
If AGENTS.md conflicts with spec → Spec wins
If code conflicts with spec → Code is wrong (bug)
```

**Wiki is NEVER the tiebreaker.**

---

## Examples

### Example 1: Content Claw Behavior

**Conflict**: Wiki says Content Claw sends `brief_acknowledged` within 10 minutes, spec says 5 minutes.

**Resolution**: Spec wins. Wiki should be corrected.

### Example 2: Evolution Schedule

**Conflict**: AGENTS.md says evolution runs at 02:00, solo-founder.yaml says 02:05.

**Resolution**: Template YAML wins for schedule times. AGENTS.md is summary.

### Example 3: Code Implementation

**Conflict**: Code implements invoice send on REVIEW approve, spec requires HOLD.

**Resolution**: Spec wins. Code has a critical bug.

---

## Related Pages

- [[message-contracts]] — Message schemas
- [[sequencing-rules]] — Ordering rules
- [[index]] — Wiki table of contents
