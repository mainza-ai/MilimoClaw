# Instructions for Lucy — New Capabilities & Current Task

> **Date:** 2026-04-05
> **Purpose:** Inform Lucy of her upgraded bridge capabilities and guide her through completing the build claw setup.

---

## New Capabilities

Your bridge commands have been upgraded. You now have 12 new commands that were previously missing from the system.

### Query Commands (5)

| Command | What It Does |
|---------|-------------|
| `bridge: claw_status(role="build")` | Get health, tool count, pending messages, and sandbox state for any claw. Valid roles: content, ops, analytics, finance, build |
| `bridge: ops_active_projects()` | List active client projects from the Ops sandbox |
| `bridge: content_pending_drafts()` | List pending content drafts from the Content sandbox |
| `bridge: build_open_prs()` | List open GitHub PRs using the authenticated gh CLI |
| `bridge: analytics_latest_report_summary()` | Read and summarize the latest intelligence reports from Analytics |

### Action Commands (5)

| Command | What It Does |
|---------|-------------|
| `bridge: send_to_claw(role="build", type="assistant_query", payload={"query": "your question"})` | Send a typed message to any claw through the mesh. Use "assistant_query" for read-only questions. Use "assistant_task" for action requests. All messages go to the War Room for operator approval before the claw acts. |
| `bridge: generate_sprint_plan(instructions="...")` | Write a sprint plan request to the Build claw's sprint context directory |
| `bridge: run_opportunity_scoring()` | Trigger opportunity scoring by writing to the Analytics claw's context |
| `bridge: check_all_deadlines()` | Check deadlines across all claws and report overdue items |
| `bridge: run_dependency_audit()` | Run Python and Node.js dependency audits on the Build claw's repo |

### Infrastructure Commands (2)

| Command | What It Does |
|---------|-------------|
| `bridge: mesh_flow_state()` | See live claw topology, pending message counts, and delivery statistics |
| `bridge: discover_tools()` | List all deployed tools across all claws with versions and last evolution dates |

---

## Your Current Task: Complete the Build Claw Setup

The build claw infrastructure is ready. The gh CLI is authenticated, GitHub skills are active, and network egress to GitHub is configured. Here are the steps to finish the setup:

### Step 1: Initialize the Build Sandbox Filesystem

Run this to create /sandbox/build/ with all required directories:

```
bridge: generate_sprint_plan(instructions="Initialize build sandbox and fetch open GitHub issues for backlog")
```

This will create the full directory structure:
- repo/
- prs/drafted, prs/approved, prs/merged
- deployments/pending, deployments/history
- context/sprint, context/errors, context/costs
- docs/
- logs/
- tasks/
- memory/

### Step 2: Verify the Sandbox Was Created

```
bridge: claw_status(role="build")
```

Check that sandbox_exists is true and sandbox_contents shows the expected directories.

### Step 3: Check for Open GitHub Issues and PRs

```
bridge: build_open_prs()
```

This uses the authenticated gh CLI to list open PRs. You can also instruct the build claw to fetch issues:

```
bridge: send_to_claw(role="build", type="assistant_task", payload={"task_description": "Fetch open GitHub issues and populate the sprint backlog", "deadline": "2026-04-05"})
```

### Step 4: Check Mesh Connectivity

```
bridge: mesh_flow_state()
```

This shows you which claws are registered in the mesh and if there are any pending messages.

### Step 5: Report Status Back

Once all steps are complete, report:
- What was initialized
- What is ready and operational
- What still needs the operator's attention in the War Room

---

## Constraints That Still Apply

- You cannot approve, block, or release War Room items. The operator must do this in the War Room TUI.
- You cannot write directly to claw filesystems. Use send_to_claw or the action trigger commands instead.
- You cannot merge PRs, trigger deployments, or send invoices.
- All messages you send to claws are REVIEW priority. They queue in the War Room for operator approval before execution.
- You cannot send client-facing messages. The Ops Claw handles client communications.

---

## How send_to_claw Works

When you call send_to_claw, the following happens:

1. Your message is validated against the contract system (sender role, recipient role, message type, payload schema).
2. The message is routed through the MeshCoordinator to the target claw's inbox.
3. The message appears in the War Room queue with REVIEW priority.
4. The operator reviews and approves the message in the War Room TUI.
5. Once approved, the claw processes the message and acts on it.

Message types you can use:
- assistant_query: For read-only status requests. Payload must include "query". Optional: "context", "priority_hint".
- assistant_task: For action requests. Payload must include "task_description" and "deadline". Optional: "context", "priority_hint", "attachments".

Example:
```
bridge: send_to_claw(role="ops", type="assistant_query", payload={"query": "What active projects have deadlines this week?", "context": "weekly planning"})
```
