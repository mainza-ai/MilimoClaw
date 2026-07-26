# AGENTS.md — Milimo Claw

> This file is a redirect to the canonical AGENTS.md.
> **Any AI coding assistant must read `.agents/AGENTS.md` in full before writing
> or modifying any agent-related code.**
> **Failure to read the canonical file will result in incorrect, incomplete, or
> dangerous changes to a production system. Read it first.**

## Critical Rules (violations cause recurring bugs and wasted effort)

**Before making any changes or proposing a fix, you MUST:**
1. **Gather ALL information** — Read all relevant files, trace data flows, check logs, examine configs, understand the full system. Do not stop after finding one piece of the puzzle. Trace every layer: CLI, runtime, config, network, filesystem, environment variables, git history, upstream dependencies. If you don't have the full picture, you don't understand the problem.
2. **Analyze thoroughly** — Trace root causes step by step. Ask "what changed?" and "why did this ever work?" before asking "how do I fix it?" Consider edge cases, timing, state, and history.
3. **Present findings for review** — Before writing any code, present your complete analysis to the user for approval. Include data sources checked, hypotheses rejected, and why your fix addresses root cause.
4. **No shortcuts** — Every fix must address root cause, not symptom. A fix that doesn't address root cause is technical debt, not a fix.

See `.agents/AGENTS.md` for the complete architecture, agent specifications,
coordination rules, and production-grade coding standards (28 rules).

Key sections in the canonical file:
- Agent architecture and the six claws
- Ground truth hierarchy (spec documents vs code vs wiki)
- Typed message contracts and inter-claw communication
- The War Room and approval thresholds
- Self-evolution cycle
- Squad templates
- Production-grade coding standards (28 rules)
- Debugging quick reference

**This file exists at root level so AI coding tools can discover it.**
**The canonical source is `.agents/AGENTS.md` — always read that file.**
