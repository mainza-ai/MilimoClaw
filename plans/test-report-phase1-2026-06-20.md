# Phase 1 — Test Report
**Date**: 2026-06-20
**Squad**: zulu | **Template**: solo | **Operator**: Mainza

---

## Summary

| Category | Pass | Fail | Skip | Total |
|----------|------|------|------|-------|
| Assistant | 2 | 0 | 2 | 4 |
| Build | 2 | 0 | 1 | 3 |
| **Total** | **4** | **0** | **3** | **7** |

---

## Assistant Claw — Results

| # | Test | Status | Notes |
|---|------|--------|-------|
| A1 | Session continuity | ⏭️ Skip | Needs TUI interaction to test |
| A2 | Memory write/read | ⏭️ Skip | Needs Lucy conversation |
| A3 | Cross-claw routing | ✅ PASS | `assistant_task` sent to build → pipeline executed → result delivered |
| A4 | War Room sync | ⏭️ Skip | Needs TUI access |
| A5 | Heartbeat execution | ✅ PASS | All 6 claws heartbeating; `HEARTBEAT.md` updated |
| A6 | Group chat boundaries | ⏭️ Skip | Needs group chat simulation |
| A7 | File workspace ops | ✅ PASS | Created `test/phase1-results.md` in workspace |
| A8 | Skill invocation | ⏭️ Skip | Needs weather skill or similar |

## Build Claw — Results

| # | Test | Status | Notes |
|---|------|--------|-------|
| B1 | Git status check | ✅ PASS | Pipeline executed, `ready_for_pr` status, files generated |
| B2 | Dependency audit | ⚠️ PARTIAL | pip outdated: packaging, pip, wheel (non-critical); npm needs lockfile |
| B3 | Build pipeline | ⏭️ Skip | Requires GitHub CLI (`gh` not installed) or container build infra |

---

## Cross-Cutting Issues

| Issue | Severity | Workaround |
|-------|----------|------------|
| `gh` CLI not installed | Low | Build claw runs without GitHub; local git ops work |
| Evolution not populated | Low | Needs 5+ observations; tool dirs created but empty |
| pip packages outdated | Low | packaging 25.0→26.2, pip 25.1.1→26.1.2, wheel 0.46.1→0.47.0 |

---

## Environment

| Setting | Value |
|---------|-------|
| Model | `inference/nvidia/nemotron-3-ultra-550b-a55b` |
| Base URL | `https://inference.local/v1` |
| Sandbox mode | True (env bootstrapped from gateway config) |
| All 6 claws | Healthy, heartbeating |
| Inboxes | Empty (all processed) |
| Rejected msgs | 5 (from pre-fix era, stale) |
