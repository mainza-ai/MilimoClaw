# Welcome to MilimoClaw Wiki

> *Milimo* (mi-LEE-mo) · Tonga, Zambia · **"works. tasks. labour."**

---

## What Is This?

This Obsidian vault is the **ultimate source of truth** for the MilimoClaw project — a multi-agent autonomous hustle platform built on NVIDIA NemoClaw.

## Quick Start

1. **New here?** Start at [[index]] — the master table of contents
2. **AI assistant?** Read [[CLAUDE]] in full before modifying anything
3. **Looking for a claw?** See [[content-claw]], [[ops-claw]], [[analytics-claw]], [[finance-claw]], [[build-claw]], or [[assistant-lucy]]
4. **Debugging?** Check [[common-issues]] or [[issues-and-fixes]]

## What Is MilimoClaw?

MilimoClaw turns a squad of operators — each running a NemoClaw sandbox on their RTX laptop — into a coordinated AI-powered business operation.

```
┌──────────────────────────────────────────────────────────────────────┐
│ MILIMO CLAW MESH                                                      │
│                                                                        │
│  CONTENT CLAW   OPS CLAW       ANALYTICS CLAW   FINANCE CLAW         │
│  /sandbox/      /sandbox/      /sandbox/        /sandbox/            │
│  content        clients        analytics        finance              │
│  OpenShell GW ── OpenShell GW ── OpenShell GW ── OpenShell GW        │
│                                                                        │
│  BUILD CLAW (tech squads)          ASSISTANT CLAW (Lucy)             │
│  /sandbox/build                    /sandbox/assistant                │
│  OpenShell GW ──────────────────── OpenShell GW ────────────────────┘│
│                                                                        │
│  ════════════════════════════════════════════════════════════════════ │
│  WAR ROOM (TUI) — Every pending action · every claw · one view       │
└──────────────────────────────────────────────────────────────────────┘
```

## The Six Claws

| Claw | Role | Mount |
|------|------|-------|
| [[content-claw]] | Creative department | `/sandbox/content` |
| [[ops-claw]] | Account manager | `/sandbox/clients` |
| [[analytics-claw]] | Intelligence layer | `/sandbox/analytics` |
| [[finance-claw]] | Financial system | `/sandbox/finance` |
| [[build-claw]] | Engineering | `/sandbox/build` |
| [[assistant-lucy]] | Operator interface | `/sandbox/assistant` |

## Key Concepts

- **[[sandbox-isolation]]** — Each claw runs in an isolated NemoClaw sandbox
- **[[message-contracts]]** — All inter-claw communication is typed and validated
- **[[war-room]]** — TUI for viewing all pending actions
- **[[evolution-cycle]]** — Sunday process that generates new tools

## Navigation Tips

1. Use **Cmd/Ctrl+O** to open the quick switcher
2. Click any **[[wiki-link]]** to navigate
3. Use the **graph view** (Cmd/Ctrl+G) to see connections
4. Check **backlinks** in the right panel

## For AI Assistants

If you're an AI working on this codebase:

1. **Read [[CLAUDE]] in full** — This is mandatory
2. **Understand the [[ground-truth-hierarchy]]** — Know which docs are authoritative
3. **Follow the templates** — Use the templates in `templates/` folder
4. **Never modify `raw/`** — This folder contains immutable symlinks

## Project Links

- **Code**: `milimo-blueprint/` (Python orchestrator)
- **CLI**: `milimo/` (TypeScript plugin)
- **Docs**: `milimo-claw-docs/`
- **Specs**: `milimo-claw-docs/reference/`

---

*"The milimo never stops. Work. Without working."*
