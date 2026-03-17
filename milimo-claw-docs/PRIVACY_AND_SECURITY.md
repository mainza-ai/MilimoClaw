# Milimo Claw — Privacy & Security

> How Milimo Claw protects your data, your squad, and your clients.

---

## Design Principle

Milimo Claw operates on a single trust principle: **sensitive data never leaves the machine unless explicitly policy-allowed.** This is enforced at the kernel level, not by prompts or software convention.

---

## The Privacy Router

The privacy router sits between the claw and all inference backends. Every inference call is intercepted, classified by data type, and routed to the appropriate backend:

### Routing Table

| Data Type | Backend | Rationale |
|---|---|---|
| Client proposals, public content drafts | ☁️ Cloud Nemotron 120B | Maximum quality for client-facing work |
| Trend data, market research | ☁️ Cloud Nemotron 120B | Public data, cloud quality preferred |
| Internal squad comms, client contact details | 🔒 Local NIM | Private business data stays on device |
| Contract review, legal-adjacent content | 🔒 Local NIM | Never touches cloud |
| Financial records, payment details | 🔒 Local NIM only | Architectural constraint — no cloud endpoint |
| Source code, API keys, environment variables | 🔒 Local NIM | Code is IP — never leaves the machine |
| Production logs with user data | 🔒 Local NIM | User data privacy is non-negotiable |
| Personal notes, private context | 🔐 Local vLLM | Tightest isolation |
| Credentials, passwords | 🔐 Local vLLM | Maximum security |

### Routing Behavior

- **Transparent routing** — the claw doesn't know which backend was used
- **Fallback safety** — unknown/unclassified data types automatically route to Local NIM
- **Locked routes** — financial, credential, and personal data routes cannot be overridden by squad policy
- **Role overrides** — Finance Claw forces ALL inference to Local NIM regardless of data type

### Configuration

The default policy is defined in `milimo-blueprint/privacy_policy.yaml`. Squads can customize non-locked routes during `milimo init`.

---

## Sandbox Isolation

### Filesystem Isolation (Landlock)

Each claw's filesystem access is restricted by Landlock LSM — a Linux kernel security module:

| Claw | Read-Write | Read-Only |
|---|---|---|
| Content | `/sandbox/content`, `/tmp` | `/sandbox/analytics/reports` |
| Ops | `/sandbox/clients`, `/tmp` | System libraries only |
| Analytics | `/sandbox/analytics`, `/tmp` | System libraries only |
| Finance | `/sandbox/finance`, `/tmp` | System libraries only |
| Build | `/sandbox/build`, `/tmp` | System libraries only |

**Key guarantees:**
- The Content Claw **cannot** read `/sandbox/clients` (Ops data)
- The Finance Claw **cannot** read `/sandbox/build` (source code)
- No claw can access another claw's primary mount
- These restrictions are **kernel-level** — no instruction can bypass them

### Process Isolation (seccomp)

Each sandbox runs with a seccomp BPF profile that:
- Blocks privilege escalation (`setuid`, `setgid`)
- Restricts dangerous syscalls
- Runs as an unprivileged `sandbox` user
- Cannot modify its own security policy

### Network Isolation

Each claw has its own network egress policy — a whitelist of external APIs it can reach:

| Claw | Allowed Endpoints |
|---|---|
| **Content** | Social APIs (publishing only), stock assets, SEO tools |
| **Ops** | Email APIs, scheduling tools, project management |
| **Analytics** | Platform analytics (read-only), market data feeds |
| **Finance** | Payment processors (read-only), accounting APIs |
| **Build** | GitHub, Vercel, Railway, npm, PyPI, Sentry |

**What's blocked:**
- Finance cannot reach social platforms
- Content cannot reach payment processors
- Build cannot reach client communication channels
- No claw can reach endpoints not in its allowlist

---

## Inter-Claw Trust

### Typed Contract Enforcement

All inter-claw communication uses typed message contracts:

1. Every message has a declared `sender_role`, `recipient_role`, and `message_type`
2. The message is validated against the sender's **outbound** policy and the recipient's **inbound** policy
3. Messages with unauthorized types are **dropped and logged** (not delivered)
4. There is no freeform text between claws

**Example:** The Content Claw cannot instruct the Finance Claw to change a pricing rule — that message type does not exist in Finance Claw's inbound policy.

### Audit Trail

Every action taken by every claw is logged with:
- Timestamp (ISO 8601)
- Claw ID and role
- Action type
- Decision (approved/rejected/auto)
- Operator ID
- Full payload

Stored as JSONL at `~/.milimo/audit/<squadId>/audit.jsonl`. Supports full replay.

---

## War Room: Human Oversight

The War Room provides the human control layer:

- **REVIEW** threshold actions are paused until a squad member approves
- **HOLD** actions require explicit confirmation from the squad
- **VETO** actions require squad-wide consensus to proceed
- **Escalation rules** defined in `mesh_config.yaml` (e.g., invoices >$500 → VETO)
- Any squad member can disable any claw tool instantly

---

## Finals Mode Security

When activated, Finals Mode hot-reloads all sandbox egress policies to a maintenance-only configuration:

- Outgoing auto-responses only (no new communications)
- No new client intake
- Payment collection continues but no new invoicing
- Analytics in passive mode (no experiments)
- All policies restore to pre-finals state on resume

---

## Why This Matters for Students

College students sharing client work, payment details, and personal data in a business context have real exposure if that data leaks. Milimo Claw provides:

- **Enterprise-grade data segregation** with zero configuration overhead
- **Kernel-level isolation** — not just software promises
- **Auditable decision trail** — every AI action is logged and reviewable
- **Institutional trust story** — universities can recommend Milimo Claw because sensitive data is architecturally isolated

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
