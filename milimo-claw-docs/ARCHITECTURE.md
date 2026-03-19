# Milimo Claw — Architecture Guide

> Technical deep-dive into the multi-sandbox mesh architecture.

---

## System Overview

Milimo Claw is a distributed multi-agent system where each agent (claw) runs in its own isolated NemoClaw sandbox. The system has six architectural layers:

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
├─────────────────────────────────────────────────────────────────┤
│ EVOLUTION LAYER                                                 │
│ Tool Generator · Tool Validator · Tool Sandbox · Pattern Detect│
│ Health Collector · Alert Generation                            │
├─────────────────────────────────────────────────────────────────┤
│ INTELLIGENCE LAYER                                              │
│ Privacy Router · Sensitivity Classifier · Inference Routing    │
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
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR LAYER │
│ War Room TUI · Approval Engine · Audit Trail · Rate Limiter │
│ Health Dashboard · Push Notifications │
├─────────────────────────────────────────────────────────────────┤
│ PAYMENT LAYER │
│ Stripe Connect · Fee Calculator · Payouts · Invoices │
│ Webhooks · Connected Accounts │
├─────────────────────────────────────────────────────────────────┤
│ PROVENANCE LAYER │
│ Ed25519 Signer · Signature Verifier · Chain Validator │
│ Attestation Generator · Performance Badges │
├─────────────────────────────────────────────────────────────────┤
│ COORDINATION LAYER │
│ Mesh Coordinator · Typed Contracts · Health Monitor │
│ Region Detector · Latency Monitor · Failover Manager │
├─────────────────────────────────────────────────────────────────┤
│ INTELLIGENCE LAYER │
│ Privacy Router · Sensitivity Classifier · Inference Routing │
├─────────────────────────────────────────────────────────────────┤
│ BLUEPRINT LAYER │
│ Role Configs · Sandbox Policies · Templates · Schema │
│ Regions Config · Rate Limits │
├─────────────────────────────────────────────────────────────────┤
│ RUNTIME LAYER │
│ NemoClaw · OpenShell · Docker · Landlock · seccomp │
│ Relay Server · WebSocket Gateway │
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
├── finance/      # Finance Claw — invoices, revenue, pricing
└── build/        # Build Claw — codebase, secrets, deploy configs
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

| From \ To | Content | Ops | Analytics | Finance | Build | War Room |
|---|---|---|---|---|---|---|
| **Content** | — | deliverable | query | — | — | deliverable |
| **Ops** | brief, signal | — | — | query, signal | brief | signal, deliverable |
| **Analytics** | response, summary | signal | — | summary | response, signal | signal, summary |
| **Finance** | — | response, signal | summary | — | — | signal, deliverable |
| **Build** | summary | signal, deliverable | query | — | — | signal, deliverable |

Messages not in this matrix are **dropped and logged**. There is no freeform text between claws.

### Valid Message Types

| Type | Description | Requires Approval |
|---|---|---|
| `brief` | Project or creative brief | No |
| `query` | Data request | No |
| `response` | Query response with data | No |
| `signal` | Alert — deadline, risk, completion | No |
| `deliverable` | Completed work product | **Yes** |
| `summary` | Periodic report | No |

---

## Mesh Coordinator

The `MeshCoordinator` manages the squad topology:

- **Registration** — Claws register with the mesh on initialization
- **Routing** — Messages validated against contracts, then delivered to recipient inbox
- **Health monitoring** — Periodic heartbeats; unhealthy claws marked and War Room notified
- **Topology persistence** — Mesh state saved to disk as `topology.json`

### Gateway Adapter

The mesh supports multiple transport modes via the `GatewayAdapter` interface:

| Transport | Use Case | Description |
|---|---|---|
| **File-based** | Development/Fallback | Uses local filesystem queues when gateway unavailable |
| **Unix Socket** | Single Host | Inter-sandbox communication on same machine via OpenShell |
| **WebSocket** | Multi-Host | Distributed mesh across different machines |

```python
# Gateway adapter selection
gateway = create_gateway(GatewayConfig(
    endpoint="unix:///var/run/openshell/gateway.sock",  # or tcp://host:port
    mesh_secret="squad-secret",
    squad_id="my-squad",
    role="content",
))
```

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
        ☁️ Cloud    🔒 Local    🔐 Local
      Nemotron      NIM        vLLM
        120B
```

**Key constraints:**
- Finance Claw: **ALL** inference → Local NIM. No exceptions.
- Build Claw: Source code, secrets → Local NIM. Boilerplate → Cloud OK.
- Unknown data types → Local NIM fallback.
- Locked routes cannot be overridden by squad policy.

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
| **REVIEW** | Queued for human approval before execution | Client communications, PR merges |
| **HOLD** | Paused, requires explicit squad confirmation | Brand voice changes, offboarding |
| **VETO** | Any squad member can block, requires re-vote | Invoices >$500, payment execution |

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
| Privacy router | Python | `milimo-blueprint/orchestrator/privacy_router.py` | Sensitivity classification + routing |
| Contracts | Python | `milimo-blueprint/orchestrator/contracts.py` | Message contract validation |
| Mesh coordinator | Python | `milimo-blueprint/orchestrator/mesh.py` | Topology, routing, health |
| Gateway adapter | Python | `milimo-blueprint/orchestrator/gateway_adapter.py` | Multi-transport gateway |
| Tool generator | Python | `milimo-blueprint/orchestrator/tool_generator.py` | LLM-based code generation |
| Tool validator | Python | `milimo-blueprint/orchestrator/tool_validator.py` | AST security validation |
| Tool sandbox | Python | `milimo-blueprint/orchestrator/tool_sandbox.py` | Isolated tool execution |
| Evolution cycle | Python | `milimo-blueprint/orchestrator/evolution_cycle.py` | Weekly self-evolution pipeline |
| Blueprint manager | Python | `milimo-blueprint/orchestrator/blueprint_manager.py` | Version control & export |

---

## Testing Architecture

### Unit Tests

- **JavaScript:** 76 tests covering plugin exports, config parsing, blueprint validation
- **Python:** 73 tests covering privacy routing, contracts, mesh coordination

### Integration Tests

Located in `test/integration/`:

| Test File | Coverage |
|-----------|----------|
| `harness.js` | Test utilities for TS ↔ Python boundary |
| `blueprint-manager.test.js` | Version, export, diff, rollback |
| `mesh-coordinator.test.js` | Registration, routing, gateway |
| `privacy-router.test.js` | Classification, routing decisions |
| `evolution-cycle.test.js` | Cycle stages, registry |

### CI/CD

GitHub Actions workflow (`.github/workflows/integration.yml`) runs:
- Lint checks (ESLint, Ruff)
- Unit tests (Node.js 18/20, Python 3.11/3.12)
- Integration tests
- Security scan (npm audit, bandit)

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
