# Response to Lucy — Build Claw Status (Updated)

Lucy, here is the updated status with corrections to your report.

---

## What You Got Right

1. **Squad config** — zulu squad, solo-founder template, 6 active claws — correct
2. **Mesh topology** — all 6 claws registered — correct
3. **Build sandbox** — initialized with directory structure — correct
4. **Pending message** — feature_brief from ops in build inbox — correct

## What Has Changed Since Your Report

### Bridge Commands — You Were Wrong About This

You reported seeing only 22 commands. This was caused by **stale Python bytecode cache files** (`__pycache__`). The container had two copies of the blueprint:

| Path | Lines | Status |
|------|-------|--------|
| `/opt/milimo-blueprint/orchestrator/bridge_cli.py` | 1395 | Updated |
| `/sandbox/.milimo/blueprints/0.1.0/orchestrator/bridge_cli.py` | 1395 | Updated |

Both copies are now synced to 1395 lines. The `__pycache__` directories contained old `.pyc` files from the 755-line version that Python was loading instead of the source. I cleared all pycache directories and the bridge now has **34 commands** (22 original + 12 new):

**New query commands:**
- `claw_status(role)` — Detailed health, tools, pending messages, sandbox state
- `ops_active_projects()` — Active client projects from Ops
- `content_pending_drafts()` — Pending content drafts from Content
- `build_open_prs()` — Open GitHub PRs via gh CLI
- `analytics_latest_report_summary()` — Latest intelligence reports

**New action commands:**
- `send_to_claw(role, type, payload)` — Send typed messages through the mesh to claws
- `generate_sprint_plan(instructions)` — Trigger sprint plan generation
- `run_opportunity_scoring(criteria)` — Trigger opportunity scoring
- `check_all_deadlines()` — Check deadlines across all claws
- `run_dependency_audit()` — Python + Node.js dependency audit

**Infrastructure commands:**
- `mesh_flow_state()` — Live topology, pending message counts, delivery stats
- `discover_tools()` — All deployed tools across all claws with versions

### War Room Routing — Fixed

Your message to the build claw was bypassing the War Room entirely. Messages requiring approval were being written directly to the claw's inbox instead of routing through the War Room first. This is now fixed:

- **mesh.py** — Messages with `requires_approval=True` now go to `~/.milimo/mesh/inbox/war_room/` first
- **mesh_config.yaml** — Added `assistant` role to the message matrix with routes to all claws
- **approval.ts** — Fixed path resolution to check `/sandbox/.milimo/mesh/` (container) before falling back to `~/.milimo/mesh/` (host)
- **cli.ts** — Added `--list` flag for non-interactive War Room queries
- **assistant_setup.py** — Fixed to use absolute paths via `Path(__file__).resolve().parent.parent` instead of relative `milimo-blueprint/` paths
- **Blueprint symlink** — Created `/sandbox/.milimo/blueprints/0.1.0/milimo-blueprint` → `/opt/milimo-blueprint` so relative paths resolve correctly from any working directory

**You can now check the War Room with:**
```
openclaw milimo warroom --operator mck --list
```

This currently shows **1 pending message** (assistant_task from you to build claw).

### War Room TUI — Now Works In Container

The War Room TUI had three path mismatches that are now fixed:
1. `ApprovalEngine` mesh directory — checks `/sandbox/.milimo/mesh/` first
2. `getClawHealth()` — checks sandbox path for registry + heartbeats
3. `fetchRevenueData()` — checks sandbox path for finance data
4. `loadEscalationRules()` — tries container blueprint path as fallback

### NVIDIA API Key — Configured

The dedicated build claw API key is set:
- `BUILD_CLAW_NVIDIA_API_KEY` — configured in container environment
- `NVIDIA_API_KEY` — also set as fallback

### gh CLI — Authenticated

- Installed: `gh version 2.89.0`
- Authenticated as: `MilimoClaw` with full repo scopes
- GitHub skills: `github` and `gh-issues` both ready

### Claws — Now Have Heartbeat System

Created `claw_launcher.py` which provides:
- **HeartbeatEmitter** — writes `~/.milimo/mesh/heartbeats/{role}.json` every 10 seconds
- **InboxPoller** — checks for new messages every 5 seconds
- **Build Claw startup** — initializes filesystem, wires dependencies, starts heartbeat + polling

**To start the build claw:**
```
docker exec MilimoClaw python3 -c "
import sys, os; sys.path.insert(0, '/sandbox/.milimo/blueprints/0.1.0')
os.environ['SQUAD_ID'] = 'zulu'
from orchestrator.claw_launcher import start_build_claw
claw, hb, poller = start_build_claw()
import time
while True: time.sleep(1)
"
```

**To start all 6 claws:**
```
docker exec MilimoClaw python3 /sandbox/.milimo/blueprints/0.1.0/orchestrator/claw_launcher.py --all --verbose
```

## Oh-My-OpenAgent (oh-my-openagent) — Status

During implementation, we cloned `https://github.com/code-yeongyu/oh-my-openagent` (dev branch) into the build claw sandbox at `/sandbox/build/repo/`. This is the **oh-my-opencode** (now renamed to oh-my-openagent) coding agent harness that the build claw uses for autonomous coding tasks.

### What oh-my-openagent Is

oh-my-openagent is a multi-agent coding framework built on top of OpenCode. It provides:

- **Sisyphus** — Main autonomous coding agent (ultrawork mode)
- **Prometheus** — Strategic planner
- **Atlas** — Todo orchestrator
- **Hephaestus** — Deep autonomous worker
- **Oracle** — Architecture and debugging
- **Explore** — Fast codebase grep/search
- **Librarian** — Docs/code search
- **Multimodal Looker** — Vision/screenshots

### What It Requires

oh-my-openagent depends on **OpenCode** as its runtime harness. OpenCode is the terminal AI coding interface that oh-my-openagent plugins into. The relationship is:

```
OpenCode (runtime harness)
  └── oh-my-openagent plugin (multi-agent framework)
        └── Sisyphus, Prometheus, Atlas, etc. (agents)
```

### Current State In The Container

| Component | Status |
|-----------|--------|
| **OpenCode binary** | NOT installed |
| **Bun runtime** | NOT installed (oh-my-openagent CLI ships standalone binaries, but installer may need it) |
| **oh-my-openagent repo** | Cloned to `/sandbox/build/repo/` (dev branch) |
| **OpenCode config** | Not configured (`~/.config/opencode/opencode.json` does not exist) |
| **oh-my-openagent plugin** | Not installed in OpenCode config |

### What Needs To Happen

For the build claw to use oh-my-openagent for coding tasks:

1. **Install OpenCode** — The runtime harness. Install from https://opencode.ai/docs
   ```
   # Inside the container:
   # Follow the OpenCode installation guide
   ```

2. **Install oh-my-openagent plugin** — Run the installer:
   ```
   # Inside the container:
   npx oh-my-opencode install --no-tui --claude=no --openai=no --gemini=no --copilot=no
   ```
   Since we have the NVIDIA API key but no Claude/OpenAI/Gemini/Copilot subscriptions, the installer needs to be configured for NVIDIA/Nemo models. This may require custom model configuration in the plugin config.

3. **Configure auth for NVIDIA provider** — OpenCode needs to know about the NVIDIA API key:
   ```
   opencode auth login
   # Select NVIDIA/NVIDIA NIM provider
   # Use NVIDIA_API_KEY or BUILD_CLAW_NVIDIA_API_KEY
   ```

4. **Configure model mappings** — The oh-my-openagent agents expect Claude/GPT models by default. We need to override them to use NVIDIA models:
   ```jsonc
   // In oh-my-openagent plugin config (~/.config/opencode/oh-my-openagent.json)
   {
     "agents": {
       "sisyphus": { "model": "nvidia/<model-name>" },
       "prometheus": { "model": "nvidia/<model-name>" },
       // ... other agents
     }
   }
   ```

### Important Note

The oh-my-openagent agents are optimized for Claude and GPT model families. NVIDIA models may not behave identically. The Sisyphus agent specifically "strongly recommends Opus 4.6 model" and "using other models may result in significantly degraded experience" per the oh-my-openagent documentation.

However, the build claw's **Python-based autonomous agent** (`build_claw.py`) works independently of oh-my-openagent. It handles:
- GitHub issue fetching and triage
- PR creation, review, and merging
- Deployment tracking
- Error and cost tracking

The oh-my-openagent integration is for **autonomous coding tasks** — when the build claw needs to actually write code, not just manage GitHub workflows.

## Answers to Your Questions

### Q1: Do I need to wait for War Room approval?

No — your feature_brief message is already in the build claw inbox. It was routed directly because it came from ops (not assistant), and ops-to-build feature_briefs don't require approval per the message matrix. The build claw just needs to be running to process it.

### Q2: Should I install OpenCode?

**Correction from my previous answer:** Yes, you should install OpenCode IF the build claw needs to use oh-my-openagent for autonomous coding tasks. The build claw's Python agent (`build_claw.py`) works without OpenCode for GitHub management (issues, PRs, deployments), but oh-my-openagent requires OpenCode as its runtime harness.

**Recommendation:** Install OpenCode and oh-my-openagent to give the build claw full autonomous coding capability. The NVIDIA API key is already configured.

### Q3: Are the bridge commands already added?

Yes — all 34 commands are registered and working. Your container had a stale blueprint (755 lines vs 1395 on host). The sync is now complete.

## Your Immediate Next Steps

1. **Check the War Room:**
   ```
   openclaw milimo warroom --operator mck --list
   ```

2. **Start the build claw:**
   Run the claw launcher script shown above. This will initialize the sandbox, start the heartbeat, and begin processing the inbox.

3. **Install OpenCode:**
   Follow the installation guide at https://opencode.ai/docs inside the container.

4. **Install oh-my-openagent plugin:**
   ```
   npx oh-my-opencode install --no-tui --claude=no --openai=no --gemini=no --copilot=no
   ```
   Then configure NVIDIA model mappings in the plugin config.

5. **Verify the build claw is alive:**
   ```
   bridge: claw_status(role="build")
   ```
   Check that `heartbeat_age_seconds` is under 15.

6. **Check mesh connectivity:**
   ```
   bridge: mesh_flow_state()
   ```

7. **Discover all available tools:**
   ```
   bridge: discover_tools()
   ```

## Constraints That Still Apply

- You cannot approve War Room items — the operator must approve
- You cannot write directly to claw filesystems — use `send_to_claw` or action trigger commands
- You cannot merge PRs, deploy, or send invoices
- All messages you send to claws are REVIEW priority — they queue in the War Room for operator approval
