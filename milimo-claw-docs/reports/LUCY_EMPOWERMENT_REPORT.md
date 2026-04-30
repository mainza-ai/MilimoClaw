# Lucy — Empowerment Report

> **NemoClaw Compliance Notice (2026-04-28)**
>
> This document has been updated to comply with NVIDIA NemoClaw v0.0.28 and OpenShell v0.0.26. Paths referencing `/sandbox/<role>/` or `/sandbox/analytics/reports/` have been migrated to `/sandbox/.openclaw-data/milimo/claws/<role>/` per NemoClaw's Landlock read-only `/sandbox/` enforcement. Credentials are stored in the OpenShell gateway store, not `~/.nemoclaw/credentials.json` (legacy). Network policies should use `protocol: rest` with `enforcement` and `access`/`rules` fields for L7 HTTP inspection. See [docs.nvidia.com/nemoclaw/latest/](https://docs.nvidia.com/nemoclaw/latest/) for authoritative documentation.

> **Goal:** Grant Lucy (the assistant) full capabilities as the primary point of contact and orchestrator of the Milimo Claw system.
>
> **Date:** 2026-04-04
> **Status:** For Review

---

## 1. Who Lucy Is

Lucy is the OpenClaw agent that serves as the conversational interface between the human operator and the six autonomous claw agents (Content, Ops, Analytics, Finance, Build, Assistant). She is configured via:

- **System prompt:** `milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md`
- **Agent config:** `.openclaw/agents/main/config.yaml` (written by `assistant_setup.py`)
- **Workspace files:** `SOUL.md`, `IDENTITY.md`, `USER.md`, `MILIMO_CLAW.md`, `AGENTS.md` in `~/.openclaw/workspace/`
- **Bridge config:** Points to `milimo-blueprint/orchestrator/bridge_cli.py` with a 3-second timeout

She runs inside the MilimoClaw Docker container alongside the gateway on port 18789.

---

## 2. What Lucy Can Currently Do

### Read/Query Operations

| Capability | Bridge Command | Status |
|---|---|---|
| All-claw health status | `collect_health` | Works — reads from filesystem JSON |
| Individual claw health | `health_status` | Works |
| Evolution cycle status | `evolution_status` | Works |
| Blueprint info/list/diff/export/rollback | `blueprint_*` | Works |
| Revenue summary | `revenue_summary` | Works |
| Squad config (creds stripped) | `squad_config` | Works |
| Mesh flow state | `mesh_flow_state` | **STUB** — returns empty data |
| Tool registry | `tool_registry` | Works |
| Marketplace search/download/publish | `marketplace_*` | Works |
| Provenance verify/keygen | `provenance_*` | Works |
| Morning/evening digest | `morning_brief`, `evening_wrap` | Works |
| Deep work activate/resume/status | `activate_deep_work`, `resume_deep_work`, `deep_work_status` | Works |
| GitHub operations (via `gh` CLI) | `github` skill | Ready — authenticated |
| GitHub issues (via `gh-issues`) | `gh-issues` skill | Ready |
| Read files from sandbox | OpenClaw file tool | Works |

### Hard Constraints (Cannot Do)

- Cannot approve, block, or release War Room items
- Cannot write to any claw's filesystem directly
- Cannot send client-facing messages
- Cannot send or transmit invoices
- Cannot merge PRs or trigger deployments
- Cannot modify evolution cycle or blueprint policies

---

## 3. The Critical Gap: Lucy Cannot Instruct Claws

The system prompt template documents bridge commands that **do not exist** in `bridge_cli.py`:

| Documented in Prompt | Exists in Bridge CLI? |
|---|---|
| `bridge: claw_status(role="content")` | No — only `collect_health` and `health_status` |
| `bridge: ops_active_projects()` | No |
| `bridge: content_pending_drafts()` | No |
| `bridge: build_open_prs()` | No |
| `bridge: analytics_latest_report_summary()` | No |
| `bridge: generate_sprint_plan()` | No |
| `bridge: run_opportunity_scoring()` | No |
| `bridge: generate_weekly_report()` | No |
| `bridge: check_all_deadlines()` | No |
| `bridge: run_dependency_audit()` | No |
| `bridge: send_message_to_claw(...)` | **No — this is the biggest gap** |

The bridge CLI currently has 22 commands, all of which are **read-only status queries or lifecycle operations**. None of them inject messages into the mesh or instruct individual claws to perform actions.

---

## 4. Architecture — Why the Gap Exists

```
OPERATOR LAYER
┌──────────────┐    ┌──────────────┐    ┌────────────────┐
│  War Room TUI │    │   Lucy       │    │  milimo CLI    │
│  (Blessed)    │    │  (OpenClaw)  │    │  (TypeScript)  │
│               │    │              │    │                │
│  Approve/     │    │  Read-only   │    │  squad status  │
│  Block/       │    │  observation │    │  finals-mode   │
│  Edit actions │    │  via bridge  │    │  assistant     │
└───────┬───────┘    └──────┬───────┘    └───────┬────────┘
        │                   │                    │
        │ direct TUI        │ spawnSync          │ CLI commands
        │ access            │ python3 bridge     │
        ▼                   ▼                    ▼

BRIDGE LAYER
┌──────────────────────────────────────────────────────────┐
│  bridge_cli.py (22 commands — ALL READ-ONLY)             │
│  - evolution_status, blueprint_*, health_*, revenue_*    │
│  - NO claw instruction commands                          │
│  - NO mesh topology queries (mesh_flow_state is stub)    │
│  - NO message injection into mesh                        │
└──────────────────────────────────────────────────────────┘
        │                   │
        │ reads from        │ (no write path to claws)
        │ filesystem        │
        ▼                   ▼

COORDINATION LAYER
┌──────────────────────┐    ┌────────────────────────────┐
│  MeshCoordinator      │    │  ContractValidator         │
│  - register_claw()    │    │  - validate(ClawMessage)   │
│  - send_message()     │    │  - requires_approval()     │
│  - heartbeat()        │    │  - 30+ message type schemas│
│  - get_pending()      │    │                            │
│  - ack_message()      │    │                            │
└──────────┬───────────┘    └────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  GatewayAdapter (pluggable transport)                     │
│  - UnixSocketGateway  (single host)                       │
│  - WebSocketGateway   (multi-host)                        │
│  - FileBasedGateway   (fallback — default)                │
└──────────────────────────────────────────────────────────┘
           │
           ▼
RUNTIME LAYER (NemoClaw Sandboxes)
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Content │ │ Ops │ │Analytics │ │ Finance │ │ Build │ │Assistant│
│ Claw │ │ Claw │ │ Claw │ │ Claw │ │ Claw │ │ Claw │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

The architecture was designed with a clear separation: claws are autonomous, the War Room is the human control surface, and Lucy is a conversational observer. This is safe but leaves Lucy powerless to act as an orchestrator.

---

## 5. What Needs to Change — Recommendations

### Priority 1: Add Claw Instruction Bridge Commands

Add new commands to `bridge_cli.py` that let Lucy send typed messages through the mesh to individual claws:

```python
# New command: send_to_claw
"send_to_claw": handle_send_to_claw

def handle_send_to_claw(args: dict) -> dict:
    """Route a message from the assistant to a specific claw via the MeshCoordinator."""
    role = args["role"]          # "content", "ops", "analytics", "finance", "build"
    message_type = args["type"]  # e.g., "query", "task_assignment", "status_request"
    payload = args.get("payload", {})

    # Validate role
    if role not in VALID_ROLES:
        return error(f"Invalid role: {role}")

    # Build a ClawMessage with sender="assistant"
    message = ClawMessage(
        sender="assistant",
        recipient_role=role,
        message_type=message_type,
        payload=payload,
        priority="REVIEW",  # Requires operator approval before claw acts
    )

    # Route through MeshCoordinator
    mesh = MeshCoordinator.load()
    result = mesh.send_message(message)
    return {"success": True, "data": {"message_id": result.message_id, "status": result.status}}
```

This requires:
- Adding `"assistant"` to `VALID_ROLES` in `contracts.py:42`
- Defining which message types the assistant can send to each claw in the authorization matrix
- Setting all assistant-originated messages to `REVIEW` priority (operator must approve)

### Priority 2: Add Claw-Specific Query Commands

Implement the missing bridge commands that the system prompt already documents:

| Command | What It Does | Data Source |
|---|---|---|
| `claw_status` | Get detailed status of one claw | Read from `~/.milimo/health/` + mesh topology |
| `ops_active_projects` | List active client projects | Read from `/sandbox/clients/` |
| `content_pending_drafts` | List pending content drafts | Read from `/sandbox/content/` |
| `build_open_prs` | List open PRs | Query GitHub via `gh pr list` |
| `analytics_latest_report_summary` | Summarize latest intelligence | Read from `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| `generate_sprint_plan` | Trigger sprint plan generation | Call build claw's sprint planner |
| `run_opportunity_scoring` | Run opportunity scoring | Call analytics claw's scorer |
| `generate_weekly_report` | Generate weekly report | Aggregate from all claws |
| `check_all_deadlines` | Check deadlines across claws | Read from claw context files |
| `run_dependency_audit` | Audit dependencies | Call build claw's auditor |

### Priority 3: Fix the mesh_flow_state Stub

The `handle_mesh_flow_state()` function at `bridge_cli.py:266-278` returns empty data. It should read from the `MeshCoordinator`'s live topology:

```python
def handle_mesh_flow_state(args: dict) -> dict:
    mesh = MeshCoordinator.load()
    topology = mesh.topology
    return {
        "nodes": topology.get("nodes", {}),
        "pending_messages": mesh.get_pending_messages(),
        "health": mesh.get_health_summary(),
    }
```

### Priority 4: Register Bridge Commands as OpenClaw Tools

Currently Lucy accesses the bridge via `spawnSync` subprocess calls (fragile, 3-second timeout). The Milimo plugin (`milimo/src/index.ts`) should register bridge commands as proper OpenClaw tools so Lucy can discover and invoke them natively with proper error handling and longer timeouts.

### Priority 5: Give Lucy Tool Discovery

Add a `bridge: discover_tools()` command so Lucy can query what capabilities each claw currently has, including tools deployed through the weekly evolution cycle. This lets Lucy adapt her responses based on what the claws can actually do right now.

### Priority 6: Extend the System Prompt

The system prompt template at `milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md` needs to be updated to:
- Reflect the actual bridge commands that exist (remove aspirational ones that don't)
- Add documentation for the new `send_to_claw` command
- Clarify the approval flow (Lucy sends a request, operator approves via War Room, claw executes)
- Add instructions for handling failures and timeouts

---

## 6. Implementation Effort Estimate

| Priority | Task | Effort | Risk |
|---|---|---|---|
| 1 | Add `send_to_claw` bridge command + contract updates | 2-3 days | Low — uses existing mesh infrastructure |
| 2 | Implement 10 missing query commands | 3-4 days | Low — mostly filesystem reads |
| 3 | Fix `mesh_flow_state` stub | 0.5 days | None |
| 4 | Register bridge as OpenClaw tools | 2-3 days | Medium — requires plugin API knowledge |
| 5 | Add `discover_tools` command | 1 day | Low |
| 6 | Update system prompt template | 1 day | Low |

**Total:** ~10-13 days of focused work

---

## 7. Current State of Lucy's Environment (Live Check)

| Component | Status | Details |
|---|---|---|
| Node.js | Available | v22.1, npm 10.9.4 |
| Python | Available | 3.11.2 |
| Git | Available | 2.39.5 |
| OpenClaw | Installed | v2026.3.11 |
| gh CLI | Authenticated | MilimoClaw account, full repo scopes |
| GitHub skill | Ready | `openclaw-bundled` |
| gh-issues skill | Ready | `openclaw-bundled` |
| skill-creator | Ready | `openclaw-bundled` |
| Build sandbox | NOT initialized | `/sandbox/build/` does not exist |
| OpenCode | NOT installed | Not in container |
| Bridge/mesh coordinator | NOT running | Needs to be started |
| NVIDIA API Key | Set | In container environment |
| Gateway | Running | Port 18789, auto-pair active |

---

## 8. Summary

Lucy is a **read-only observer** with a well-documented system prompt that describes capabilities she doesn't actually have. The bridge CLI provides status queries but no action dispatching. The mesh coordinator and contract system are fully built but inaccessible to Lucy.

To make Lucy the true primary orchestrator, she needs:
1. A pathway to send typed messages to claws through the mesh (with operator approval gates)
2. The missing query commands her system prompt already describes
3. Live mesh topology data instead of stubs
4. Native tool registration instead of fragile subprocess calls

The infrastructure to support all of this already exists — it just needs to be wired up.
