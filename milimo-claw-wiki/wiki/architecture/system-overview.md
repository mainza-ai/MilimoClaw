# System Overview

**Summary**: Eight-layer architecture of MilimoClaw multi-agent system.

**Sources**:
- `raw/ARCHITECTURE.md`
- `raw/AGENTS.md`

**Last updated**: 2026-04-23

**Tags**: #architecture #overview

---

## Architecture Layers

MilimoClaw has eight architectural layers, each with specific responsibilities:

```
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR LAYER                                                  │
│ War Room TUI · Approval Engine · Audit Trail · Rate Limiter   │
│ Health Dashboard · Push Notifications                          │
├─────────────────────────────────────────────────────────────────┤
│ PAYMENT LAYER                                                   │
│ Stripe Connect · Fee Calculator · Payouts · Invoices          │
│ Webhooks · Connected Accounts                                   │
├─────────────────────────────────────────────────────────────────┤
│ PROVENANCE LAYER                                                │
│ Ed25519 Signer · Signature Verifier · Chain Validator         │
│ Attestation Generator · Performance Badges                      │
├─────────────────────────────────────────────────────────────────┤
│ COORDINATION LAYER                                              │
│ Mesh Coordinator · Gateway Adapter · Typed Contracts           │
│ Region Detector · Latency Monitor · Failover Manager          │
│ Event Normalization (Clawhip pattern)                          │
├─────────────────────────────────────────────────────────────────┤
│ EVOLUTION LAYER                                                 │
│ Tool Generator · Tool Validator · Tool Sandbox · Pattern Detect│
│ Health Collector · Alert Generation                            │
├─────────────────────────────────────────────────────────────────┤
│ INTELLIGENCE LAYER                                              │
│ Privacy Router · Sensitivity Classifier · Inference Routing   │
│ Category-Based Model Selection (OmO pattern)                   │
│ Inference Fallback Chain (OmO pattern)                         │
├─────────────────────────────────────────────────────────────────┤
│ BLUEPRINT LAYER                                                 │
│ Role Configs · Sandbox Policies · Templates · Schema           │
│ Regions Config · Rate Limits · Performance Attestations        │
├─────────────────────────────────────────────────────────────────┤
│ RUNTIME LAYER                                                   │
│ NemoClaw · OpenShell · Docker · Landlock · seccomp            │
│ Relay Server · WebSocket Gateway                               │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Operator Layer

Human interface for monitoring and control.

- **War Room TUI**: Terminal UI for viewing all pending actions
- **Approval Engine**: REVIEW/HOLD/AUTO decision processing
- **Audit Trail**: Complete operation logging
- **Rate Limiter**: Prevents system overload
- **Health Dashboard**: Real-time system health
- **Push Notifications**: Alert delivery

### 2. Payment Layer

Financial integration with Stripe.

- **Stripe Connect**: Multi-party payments
- **Fee Calculator**: Platform fee computation
- **Payouts**: Operator payment processing
- **Invoices**: Automated billing
- **Webhooks**: Payment event handling

### 3. Provenance Layer

Cryptographic verification of all actions.

- **Ed25519 Signer**: Message signing
- **Signature Verifier**: Verification of signatures
- **Chain Validator**: Validates action chains
- **Attestation Generator**: Creates performance attestations
- **Performance Badges**: Reputation system

### 4. Coordination Layer

Inter-claw communication and mesh management.

- **Mesh Coordinator**: Central message routing
- **Gateway Adapter**: OpenShell gateway interface
- **Typed Contracts**: Message schema validation
- **Region Detector**: Multi-region support
- **Latency Monitor**: Performance tracking
- **Failover Manager**: Redundancy handling

### 5. Evolution Layer

Self-improvement system.

- **Tool Generator**: Creates new tools via inference
- **Tool Validator**: Tests proposed tools
- **Tool Sandbox**: Safe testing environment
- **Pattern Detection**: Identifies recurring patterns
- **Health Collector**: Monitors system health

### 6. Intelligence Layer

AI inference and data routing.

- **Privacy Router**: Routes based on sensitivity
- **Sensitivity Classifier**: Labels data types
- **Inference Routing**: Cloud vs local NIM (NEMOCLAW_MODEL)
- **Model Selection**: Category-based model choice

### 7. Blueprint Layer

Configuration and policy management.

- **Role Configs**: Claw role definitions
- **Sandbox Policies**: Security policies
- **Templates**: Squad templates
- **Schema**: Data schemas

### 8. Runtime Layer

Execution environment.

- **NemoClaw**: NVIDIA sandbox runtime
- **OpenShell**: Inter-sandbox communication
- **Docker**: Container runtime
- **Landlock**: Filesystem isolation
- **seccomp**: Syscall filtering


## Assistant (Lucy)

The [[assistant-lucy]] is the conversational interface that bridges users to all claws. While not a dedicated layer, Lucy operates across the Operator and Coordination layers:

- **User Interface**: Natural language interaction via Telegram
- **Message Routing**: Dispatches `assistant_query` and `assistant_task` to appropriate claws
- **Silent Responses**: Returns diagnostic output when claws return empty results
- **Runtime Coordination**: Implemented in `assistant/lucy.py` as `LucyAssistant` class

## Data Flow

```
User Request
    │
    ▼
┌─────────────────┐
│ Operator Layer  │ ◄── Human approval
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Coordination    │ ◄── Message routing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Intelligence    │ ◄── Inference
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Blueprint       │ ◄── Config lookup
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Runtime         │ ◄── Execution
└─────────────────┘
```

## Related Pages

- [[sandbox-isolation]] — Runtime isolation details
- [[inter-claw-communication]] — Coordination layer deep-dive
- [[privacy-router]] — Intelligence layer routing
- [[mesh-coordinator]] — Coordination layer internals
