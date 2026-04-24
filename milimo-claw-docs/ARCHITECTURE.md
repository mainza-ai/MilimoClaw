# Milimo Claw — Architecture Guide

> Technical deep-dive into the multi-sandbox mesh architecture.
> **Last Updated:** 2026-04-04

---

## System Overview

Milimo Claw is a distributed multi-agent system where each agent (claw) runs in its own isolated NemoClaw sandbox. The system has eight architectural layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR LAYER                                                  │
│ War Room TUI · Approval Engine · Audit Trail · Rate Limiter    │
│ Health Dashboard · Push Notifications                          │
├─────────────────────────────────────────────────────────────────┤
│ PAYMENT LAYER                                                   │
│ Stripe Connect · Fee Calculator · Payouts · Invoices           │
│ Webhooks · Connected Accounts                                  │
├─────────────────────────────────────────────────────────────────┤
│ PROVENANCE LAYER                                                │
│ Ed25519 Signer · Signature Verifier · Chain Validator          │
│ Attestation Generator · Performance Badges                     │
├─────────────────────────────────────────────────────────────────┤
│ COORDINATION LAYER                                              │
│ Mesh Coordinator · Gateway Adapter · Typed Contracts           │
│ Region Detector · Latency Monitor · Failover Manager           │
│ Event Normalization (Clawhip pattern)                          │
├─────────────────────────────────────────────────────────────────┤
│ EVOLUTION LAYER                                                 │
│ Tool Generator · Tool Validator · Tool Sandbox · Pattern Detect│
│ Health Collector · Alert Generation                            │
├─────────────────────────────────────────────────────────────────┤
│ INTELLIGENCE LAYER                                              │
│ Privacy Router · Sensitivity Classifier · Inference Routing    │
│ Category-Based Model Selection (OmO pattern)                   │
│ Inference Fallback Chain (OmO pattern)                         │
├─────────────────────────────────────────────────────────────────┤
│ BLUEPRINT LAYER                                                 │
│ Role Configs · Sandbox Policies · Templates · Schema           │
│ Regions Config · Rate Limits · Performance Attestations        │
├─────────────────────────────────────────────────────────────────┤
│ RUNTIME LAYER                                                   │
│ NemoClaw · OpenShell · Docker · Landlock · seccomp             │
│ Relay Server · WebSocket Gateway                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sandbox Isolation Model

Each claw runs inside a NemoClaw sandbox with kernel-level isolation:

| Isolation Layer | Mechanism | What It Protects |
|---|---|---|
| **Filesystem** | Landlock LSM | Each claw can only access its own `/sandbox/<role>` mount |
| **Network** | OpenShell netns + egress policy | Per-claw API allowlists — Finance can't reach social APIs |
| **Process** | seccomp BPF | Blocks privilege escalation, restricts dangerous syscalls |
| **Inference** | Privacy router intercept | Sensitive data routed to local NIM, never to cloud |
| **Communication** | Typed contract validation | Inter-claw messages validated against policy before delivery |

### Filesystem Mounts

```
/sandbox/
├── content/      # Content Claw — brand assets, drafts, style guides
├── clients/      # Ops Claw — client records, project histories
├── analytics/    # Analytics Claw — performance data, reports
│   └── reports/  # Read-only cross-mount for Content Claw
├── finance/ # Finance Claw — invoices, revenue, pricing
├── build/ # Build Claw — codebase, secrets, deploy configs
│   ├── repo/ # Codebase (GitHub mount)
│   ├── context/ # Sprint plans, error patterns, cost tracking
│   ├── prs/ # PR state tracking (drafted/approved/merged)
│   ├── deployments/ # Deploy state (pending/history)
│   ├── docs/ # Changelog, API docs, devlog
│   ├── memory/ # Filesystem memory pattern (Clawhip)
│   └── logs/ # Operational, PR, deploy, cost alerts
└── assistant/ # Assistant Claw — sessions, context, logs
```

Each claw has **read-write** access only to its own mount. Cross-mounts are explicitly declared and **read-only**.

---

## Inter-Claw Communication

### Message Contract System

All inter-claw communication uses **typed contracts** — structured payloads with defined schemas:

```python
@dataclass
class ClawMessage:
    sender_role: str       # e.g. "ops"
    recipient_role: str    # e.g. "content"
    message_type: str      # e.g. "brief"
    payload: dict          # Structured data
    squad_id: str          # Squad identifier
    message_id: str        # Unique message ID
    timestamp: str         # ISO 8601
```

### Message Matrix

The **message matrix** defines which types each role can send to which recipient:

| From \ To | Content | Ops | Analytics | Finance | Build | Assistant | War Room |
|---|---|---|---|---|---|---|---|
| **Content** | — | deliverable | query | — | — | — | deliverable |
| **Ops** | brief, signal | — | — | query, signal | brief | — | signal, deliverable |
| **Analytics** | response, summary | signal | — | summary | response, signal | — | signal, summary |
| **Finance** | — | response, signal | summary | — | — | — | signal, deliverable |
| **Build** | summary | signal, deliverable | query | — | — | — | signal, deliverable |
| **Assistant** | — | — | — | — | — | — | signal |

Messages not in this matrix are **dropped and logged**. There is no freeform text between claws.

### Event Normalization (Clawhip Pattern)

All incoming messages are normalized to canonical event format at ingress:

```python
def normalize_message(raw: dict) -> dict:
    return {
        "event": f"build.{raw['message_type']}",
        "source": raw.get("sender_role", "unknown"),
        "repo_name": raw.get("payload", {}).get("project_id"),
        "timestamp": raw["timestamp"],
        "metadata": raw.get("payload", {}),
    }
```

### Valid Message Types

| Type | Description | Requires Approval |
|---|---|---|
| `brief` | Project or creative brief | No |
| `query` | Data request | No |
| `response` | Query response with data | No |
| `signal` | Alert — deadline, risk, completion | No |
| `deliverable` | Completed work product | **Yes** |
| `summary` | Periodic report | No |
| `overdue_alert` | SLA overdue warning | No |

---

## Mesh Coordinator

The `MeshCoordinator` manages the squad topology:

- **Registration** — Claws register with the mesh on initialization
- **Routing** — Messages validated against contracts, then delivered to recipient inbox
- **Health monitoring** — Periodic heartbeats; unhealthy claws marked and War Room notified
- **Topology persistence** — Mesh state saved to disk as `topology.json`
- **Retry logic** — Automatic reconnection with exponential backoff
- **Health check loop** — Automated periodic health verification

### Gateway Adapter

The mesh supports multiple transport modes via the `GatewayAdapter` interface:

| Transport | Use Case | Description |
|---|---|---|
| **File-based** | Development/Fallback | Uses local filesystem queues when gateway unavailable |
| **Unix Socket** | Single Host | Inter-sandbox communication on same machine via OpenShell |
| **WebSocket** | Multi-Host | Distributed mesh across different machines |

### Mesh States

| State | Description | Accepts Messages |
|---|---|---|
| `online` | Claw is active and healthy | ✅ |
| `finals-mode` | Claw is in maintenance mode | ✅ (limited) |
| `unhealthy` | Missed heartbeats | ⚠️ Queued |
| `offline` | Explicitly stopped | ❌ |

---

## Self-Evolution Engine

The evolution engine runs a weekly 5-stage pipeline:

```
OBSERVE → IDENTIFY → PROPOSE → BUILD → DEPLOY
   │          │          │         │        │
   │          │          │         │        └─ Register tool, notify War Room
   │          │          │         └─ Generate code, backtest, validate
   │          │          └─ Create tool proposal from pattern
   │          └─ Detect recurring patterns in operation log
   └─ Read 7 days of operation log
```

### Tool Generator

Generates Python tool code from specifications using LLM:

```python
from tool_generator import ToolGenerator, ToolSpec

spec = ToolSpec(
    name="tone_classifier",
    tool_type="classifier",
    description="Classifies content tone",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
    output_schema={"type": "object", "properties": {"tone": {"type": "string"}}},
)

generator = ToolGenerator()
result = generator.generate(spec)
```

### Tool Validator

AST-based security validation before deployment:

- Checks for forbidden imports (subprocess, socket, urllib, etc.)
- Validates type hints and docstrings
- Enforces code length limits
- Detects dangerous patterns (eval, exec, __import__)

### Tool Sandbox

Isolated execution environment for testing:

- Subprocess isolation with resource limits
- Memory and execution time constraints
- Network and filesystem access controls
- Test case validation before deployment

---

## Privacy Router

The privacy router intercepts every inference call and routes based on data sensitivity:

```
Inference Request → Sensitivity Classifier → Routing Decision
                         │
                    ┌────┴────┐
                    │ Policy  │
                    │ Lookup  │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
☁️ Cloud 🔒 Local 🔐 Local
NEMOCLAW_MODEL NIM vLLM
```

**Key constraints:**
- Finance Claw: **ALL** inference → Local NIM. No exceptions.
- Build Claw: Source code, secrets → Local NIM. Boilerplate → Cloud OK.
- Unknown data types → Local NIM fallback.
- Locked routes cannot be overridden by squad policy.

### Category-Based Model Selection (OmO Pattern)

The Build Claw uses semantic categories to route inference calls to optimal models:

| Category | Model | Temperature | Use Case |
|---|---|---|---|
| `code_generation` | Local NIM | 0.1 | Source code, patches |
| `pr_review` | Cloud (NEMOCLAW_MODEL) | 0.3 | PR descriptions, reviews |
| `deploy_planning` | Cloud (NEMOCLAW_MODEL) | 0.2 | Deploy strategies |
| `doc_writing` | Cloud (NEMOCLAW_MODEL) | 0.7 | Changelogs, devlogs |
| `issue_scoring` | Cloud (NEMOCLAW_MODEL) | 0.2 | Complexity estimation |

### Inference Fallback Chain (OmO Pattern)

All inference calls use exponential backoff across a fallback chain:

```python
INFERENCE_FALLBACK_CHAIN = [
    "primary_model",
    "claude-sonnet-4-6",
    "gemini-3.1-pro",
]
```

---

## War Room Architecture

The War Room is **not** a sandbox — it's the human oversight layer sitting above the mesh.

```
┌─────────────────────────────────────────────────┐
│ WAR ROOM                                         │
│                                                  │
│ ┌─────────────┐ ┌──────────────┐ ┌────────┐    │
│ │ Pending     │ │ Approval     │ │ Audit  │    │
│ │ Action      │ │ Engine       │ │ Trail  │    │
│ │ Queue       │ │ (4 modes)    │ │ (JSONL)│    │
│ └──────┬──────┘ └──────┬───────┘ └────┬───┘    │
│        │               │              │        │
│        └────────────────┼─────────────┘        │
│                         │                      │
│         ┌───────────────┴───────────────┐     │
│         │ Rate Limiter                   │     │
│         │ (Free: 10/day, 3/hour burst)  │     │
│         └───────────────────────────────┘     │
│                         │                      │
│         Human Decision                         │
│         approve · veto · hold · delegate       │
└─────────────────────────────────────────────────┘
```

### Approval Modes

| Mode | Behavior | Use Case |
|---|---|---|
| **AUTO** | Claw acts immediately, logs for review | Low-stakes routine actions |
| **REVIEW** | Queued for human approval before execution | Client communications, PR creation |
| **HOLD** | Paused, requires explicit squad confirmation | PR merge, deployment |
| **VETO** | Any squad member can block, requires re-vote | Invoices >$500, payment execution |

### Build Claw Two-Stage Approval

The Build Claw has a **critical two-stage approval** flow that differs from other claws:

1. **PR Creation** → REVIEW approval → moves to HOLD
2. **PR Merge** → HOLD release → merges to main (REVIEW approval does NOT merge)
3. **Deployment** → Separate HOLD → release triggers deploy (merge ≠ deploy)

### Rate Limiting

Auto-approvals are rate-limited by tier:

| Tier | Daily Limit | Burst Limit | Burst Window |
|------|-------------|-------------|--------------|
| Free | 10 | 3 | 1 hour |
| Pro | Unlimited | N/A | N/A |

Rate limit status is visible in the War Room via `getRateLimitStatus()`.

---

## Component Map

| Component | Language | Location | Purpose |
|---|---|---|---|
| Plugin entry | TypeScript | `milimo/src/index.ts` | OpenClaw plugin registration |
| CLI registrar | TypeScript | `milimo/src/cli.ts` | Commander.js subcommand wiring |
| Init command | TypeScript | `milimo/src/commands/init.ts` | Squad initialization |
| Squad commands | TypeScript | `milimo/src/commands/squad.ts` | Status, Finals Mode, Resume |
| Blueprint commands | TypeScript | `milimo/src/commands/blueprint.ts` | Fork, Diff, Publish, Rollback |
| Slash handler | TypeScript | `milimo/src/commands/slash.ts` | In-chat `/milimo` commands |
| War Room TUI | TypeScript | `milimo/src/warroom/warroom.ts` | Interactive operator dashboard |
| Approval engine | TypeScript | `milimo/src/warroom/approval.ts` | 4-mode approval with escalation |
| Rate limiter | TypeScript | `milimo/src/warroom/rate-limiter.ts` | Token bucket rate limiting |
| Audit logger | TypeScript | `milimo/src/warroom/audit.ts` | JSONL audit trail |
| Gateway client | TypeScript | `milimo/src/mesh/gateway-client.ts` | Mesh communication with HKDF |
| Privacy router | Python | `milimo-blueprint/orchestrator/privacy_router.py` | Sensitivity classification + routing |
| Contracts | Python | `milimo-blueprint/orchestrator/contracts.py` | Message contract validation |
| Mesh coordinator | Python | `milimo-blueprint/orchestrator/mesh.py` | Topology, routing, health |
| Evolution cycle | Python | `milimo-blueprint/orchestrator/evolution_cycle.py` | Weekly self-evolution pipeline |
| Tool builder | Python | `milimo-blueprint/orchestrator/tool_builder.py` | Dynamic tool generation + validation |
| Solo init | Python | `milimo-blueprint/orchestrator/solo_init.py` | Solo mode initialization |
| Assistant setup | Python | `milimo-blueprint/orchestrator/assistant_setup.py` | Assistant system prompt rendering |
| **Build Claw** | Python | `milimo-blueprint/orchestrator/build/` | 13 modules — engineering automation |
| **Content Claw** | Python | `milimo-blueprint/orchestrator/content/` | 11 modules — creative output |
| **Ops Claw** | Python | `milimo-blueprint/orchestrator/ops/` | 11 modules — client/project management |
| **Analytics Claw** | Python | `milimo-blueprint/orchestrator/analytics/` | 12 modules — intelligence layer |
| **Finance Claw** | Python | `milimo-blueprint/orchestrator/finance/` | 12 modules — financial operations |
| **Assistant Claw** | Python | `milimo-blueprint/orchestrator/assistant/` | Conversational interface — operator ↔ claws |

---

## Build Claw Architecture

### Module Structure

```
orchestrator/build/
├── __init__.py              — Package exports
├── build_init.py            — Filesystem init, inference fallback chain, category routing
├── build_claw.py            — Main entry point, component wiring
├── build_scheduler.py       — Timer-based scheduling, missed job recovery
├── signal_dispatcher.py     — Event normalization, renderer/sink separation, SLA timer
├── approval_handler.py      — Two-stage REVIEW→HOLD, file-based task persistence
├── issue_manager.py         — GitHub issues, sprint planning, velocity tracking
├── code_generator.py        — Hash-anchored code generation, AST-aware search
├── pr_manager.py            — PR lifecycle with two-stage REVIEW→HOLD→merge
├── deploy_manager.py        — Separate HOLD flow, background execution
├── error_monitor.py         — ErrorPattern/ErrorEvent, tmux monitoring hooks
├── cost_monitor.py          — Baseline calculation, drift detection
├── dependency_auditor.py    — Vulnerability assessment, security PR routing
└── doc_maintainer.py        — Changelog/devlog generation, shipping summaries
```

### Enhancements from External Projects

| Feature | Source | Module |
|---|---|---|
| Inference fallback chain | oh-my-openagent | build_init.py |
| Category-based model selection | oh-my-openagent | build_init.py |
| Hash-anchored code generation | oh-my-openagent | code_generator.py |
| Task dependency storage | oh-my-openagent | approval_handler.py |
| Background execution | oh-my-openagent | deploy_manager.py, pr_manager.py |
| Session recovery | oh-my-openagent | build_init.py |
| Typed event normalization | clawhip | signal_dispatcher.py |
| Renderer/sink separation | clawhip | signal_dispatcher.py |
| Tmux session monitoring | clawhip | error_monitor.py |
| Filesystem memory pattern | clawhip | All modules with `_log` lists |

---

## Testing Architecture

### Unit Tests

- **JavaScript:** 318 tests covering plugin exports, config parsing, blueprint validation, encryption, approval engine, War Room TUI
- **Python:** 1192 tests covering all 6 claws, orchestrator core, Build Claw (116 tests), integration tests

### Integration Tests

Located in `milimo-blueprint/tests/`:

| Test File | Coverage |
|-----------|----------|
| `test_build_unit.py` | Build Claw unit tests (101 tests) |
| `test_build_mvr_integration.py` | Build Claw MVR sequence (15 tests) |
| `test_content_unit.py` | Content Claw unit tests |
| `test_ops_unit.py` | Ops Claw unit tests |
| `test_analytics_unit.py` | Analytics Claw unit tests |
| `test_finance_unit.py` | Finance Claw unit tests |
| `test_mesh_coordinator.py` | Mesh coordination, registration, routing |
| `test_privacy_router.py` | Classification, routing decisions |
| `test_evolution_cycle.py` | Cycle stages, registry |
| `test_feature_brief_acknowledged.py` | Build Claw SLA timer tests |
| `test_assistant_setup.py` | System prompt rendering |
| `test_solo_init.py` | Solo mode initialization |
| `test_finance_init.py` | Finance logging and payment events |

### CI/CD

GitHub Actions workflow (`.github/workflows/integration.yml`) runs:
- Lint checks (ESLint, Ruff)
- Unit tests (Node.js 18/20, Python 3.11/3.12)
- Integration tests
- Security scan (npm audit, bandit)

---

## Security Architecture

### MilimoClaw-Specific Security Fixes

| Issue | Fix | File |
|---|---|---|
| Hardcoded JWT secret | Throws if `JWT_SECRET` env var is unset | `milimo-server/src/server.ts` |
| CORS `origin: true` | Restricted to `ALLOWED_ORIGINS` env var | `milimo-server/src/server.ts` |
| WebSocket no auth | JWT required for all WS connections | `milimo-server/src/server.ts` |
| Refresh token not validated | Proper token store with expiration + rotation | `milimo-server/src/routes/auth.ts` |
| Weak mesh key derivation | HKDF replaces byte-cycling | `milimo/src/mesh/gateway-client.ts` |
| k8s SYS_ADMIN capability | Dropped to ALL + only SYSLOG | `k8s/sandbox-pod.yaml` |
| Fallback messages unencrypted | AES-256-GCM encryption for file queue | `milimo/src/mesh/gateway-client.ts` |

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
