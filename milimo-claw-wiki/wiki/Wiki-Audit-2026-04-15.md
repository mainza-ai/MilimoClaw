# Wiki Audit Report — 2026-04-15

**Summary**: Comprehensive audit of wiki links, orphan pages, and missing concepts.

**Last updated**: 2026-04-15

**Tags**: #audit #meta

---

## Executive Summary

| Metric | Count | Status |
|--------|-------|--------|
| Total wiki pages | 105+ | ✓ |
| Orphan pages | 0 | ✓ |
| Broken links | 24 | ⚠️ Fixable |
| Naming mismatches | 4 | ⚠️ Quick fix |
| Missing module pages | 15 | ⚠️ Need creation |
| Deferred (TypeScript) | 5 | — |

---

## Category 1: Naming Mismatches (4)

Links pointing to pages that exist under different names.

| Broken Link | Actual Page | Fix |
|-------------|-------------|-----|
| `[[debugging]]` | — | Create `development/debugging.md` |
| `[[sandbox-sync]]` | — | Create `troubleshooting/sandbox-sync.md` |
| `[[pattern-detection]]` | — | Create `evolution/pattern-detection.md` |
| `[[signal-dispatcher]]` | `patterns/signal-dispatcher-pattern.md` | Rename or create redirect |

**Source files affected**:
- `[[debugging]]`: conventions.md, index.md, testing.md
- `[[sandbox-sync]]`: common-issues.md, index.md, issues-and-fixes.md
- `[[pattern-detection]]`: evolution-cycle.md, index.md, operation-log.md
- `[[signal-dispatcher]]`: 9 files across claws

---

## Category 2: Missing Module Pages (15)

Modules referenced in claw docs but no wiki page exists.

| Missing Page | Referenced From | Priority |
|--------------|-----------------|----------|
| `[[approval-handler]]` | 7 claw pages | High |
| `[[analytics-scheduler]]` | analytics-claw.md | Medium |
| `[[build-scheduler]]` | build-claw.md | Medium |
| `[[finance-scheduler]]` | finance-claw.md | Medium |
| `[[cost-monitor]]` | build-claw.md | Medium |
| `[[dependency-auditor]]` | build-claw.md | Low |
| `[[doc-maintainer]]` | build-claw.md | Low |
| `[[invoice-generator]]` | payment-risk-scorer.md, stripe-client.md | Medium |
| `[[payment-events-log]]` | payment-risk-scorer.md | Low |
| `[[quarterly-tax-prep]]` | expense-tracker.md | Low |
| `[[timing-optimizer]]` | content-scheduler.md | Low |
| `[[tool-registry]]` | content-generator.md | High |
| `[[pattern-detector]]` | tool-generation.md | Medium |

---

## Category 3: Deferred TypeScript Pages (5)

These require TypeScript expertise and were deferred in the improvement plan.

| Page | Location | Status |
|------|----------|--------|
| `[[warroom-tui]]` | `milimo/src/warroom/` | Deferred |
| `[[cli-commands]]` | `milimo/src/commands/` | Deferred |
| `[[mesh-gateway-client]]` | `milimo/src/mesh/` | Deferred |
| `[[bridge-tools]]` | `milimo/src/lib/bridge-tools.ts` | Deferred |
| `[[onboard-flows]]` | `milimo/src/onboard/` | Deferred |

---

## Category 4: Deferred Config (1)

| Page | Reason |
|------|--------|
| `[[multi-region-config]]` | Source file `regions.yaml` not found in codebase |
| `[[development-scripts]]` | Minor scripts, deferred |

---

## Recommended Actions

### Phase A: Quick Fixes (Estimated: 15 min)

1. **Create missing development pages**:
   - `development/debugging.md`
   - `troubleshooting/sandbox-sync.md`
   - `evolution/pattern-detection.md`

2. **Fix signal-dispatcher naming**:
   - Option A: Rename `signal-dispatcher-pattern.md` → `signal-dispatcher.md`
   - Option B: Create redirect page
   - Recommendation: Rename for consistency

### Phase B: High-Priority Module Pages (Estimated: 30 min)

1. Create `modules/coordination/approval-handler.md` (referenced by 7 pages)
2. Create `modules/build/tool-registry.md`
3. Create `modules/finance/invoice-generator.md`

### Phase C: Scheduler Pages (Estimated: 20 min)

Create scheduler pages for each claw:
- `modules/analytics/analytics-scheduler.md`
- `modules/build/build-scheduler.md`
- `modules/finance/finance-scheduler.md`

### Phase D: Lower Priority (Optional)

- cost-monitor.md
- dependency-auditor.md
- doc-maintainer.md
- payment-events-log.md
- quarterly-tax-prep.md
- timing-optimizer.md

---

## Statistics

| Section | Pages | Links In | Links Out |
|---------|-------|----------|-----------|
| Architecture | 10 | 45+ | 60+ |
| Claws | 6 | 30+ | 50+ |
| Modules | 55+ | 100+ | 150+ |
| Coordination | 5 | 25+ | 40+ |
| Evolution | 3 | 15+ | 20+ |
| Development | 2 | 10+ | 15+ |
| Troubleshooting | 3 | 10+ | 15+ |
| Reference | 4 | 20+ | 30+ |
| Configuration | 4 | 15+ | 20+ |
| Solo | 6 | 25+ | 35+ |
| Templates | 8 | 30+ | 40+ |
| Patterns | 1 | 10+ | 15+ |
| Security | 3 | 12+ | 18+ |
| Operations | 4 | 16+ | 24+ |
| Scripts | 2 | 8+ | 12+ |

---

## Next Audit

Recommended: After Phase A-D fixes complete

---

*Audit performed: 2026-04-15*
