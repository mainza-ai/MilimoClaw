# Solo Founder Template

**Summary**: Solo operator template with all 6 claws for single-machine deployment.

**Sources**:
- `raw/SOLO_TEMPLATE_SPEC.md`
- `milimo-blueprint/templates/solo-founder.yaml`

**Last updated**: 2026-04-23

**Tags**: #templates #solo #founder

---

## Overview

The solo-founder template is the primary template for development and testing. It includes all 6 claws running on a single operator's machine.

## Configuration

```yaml
# solo-founder.yaml
template_id: solo-founder
name: Solo Founder
  description: Full 6-claw setup for solo operators
claws:
  - content
  - ops
  - analytics
  - finance
  - build
  - assistant
```

## Evolution Schedule

Staggered schedule ensures each claw runs on fresh Analytics intelligence:

| Time | Action |
|------|--------|
| Sunday 01:00 | Analytics: baseline recalculation |
| Sunday 02:00 | Analytics: weekly intelligence report |
| Sunday 02:05 | Content: evolution cycle |
| Sunday 02:15 | Ops: evolution cycle |
| Sunday 02:25 | Analytics: evolution cycle |
| Sunday 02:35 | Build: evolution cycle |
| Sunday 03:00 | Finance: weekly revenue summary + evolution cycle |

## Cost Guard

- Daily cloud token budget: 50,000
- Alert at 80%
- Fallback strategy: `lighter_prompt`
- Never block a claw action — always fallback

## Deep Work Mode

When enabled, per-claw behavior:

| Claw | Still Runs | Paused |
|------|------------|--------|
| Content | Nothing | Draft generation, publishing |
| Ops | Auto-responses | New client intake |
| Analytics | Passive collection | New experiments |
| Finance | Invoice sends, payment monitoring | New project initiations |
| Build | Issue triage, error monitoring | New PRs, deploys |
| Assistant | Query responses, digest delivery | Proactive notifications |

## Approval Thresholds

Configured in `solo-founder.yaml`:

- All client-facing content: REVIEW
- Financial actions: Two-stage (REVIEW + HOLD)
- Code deploys: Two-stage (PR + Deploy HOLD)
- Routine operations: AUTO

## Usage

```bash
# Initialize with solo template
milimo init --solo --operator-name "Your Name" --squad-name "my-squad"

# Or during onboarding
./install.sh --solo --operator-name "Your Name" --squad-name "my-squad"
```

## Filesystem Structure

```
/sandbox/
├── content/        # Content Claw workspace
├── clients/        # Ops Claw workspace
├── analytics/      # Analytics Claw workspace
│   └── reports/    # Shared intelligence (read-only to other claws)
├── finance/        # Finance Claw workspace
└── build/          # Build Claw workspace
```

## Related Pages

- [[template-overview]] — All templates
- [[evolution-cycle]] — Evolution system
- [[war-room]] — Approval interface
- [[content-claw]] — Content Claw
- [[ops-claw]] — Ops Claw
- [[analytics-claw]] — Analytics Claw
- [[finance-claw]] — Finance Claw
- [[build-claw]] — Build Claw
- [[assistant-lucy]] — Assistant (Lucy)
