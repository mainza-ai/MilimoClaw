# MilimoClaw One-Command Install Plan (v2.0 — Solo Template Corrected)

## Objective

Replace the current 23-step, 4-phase manual installation process with a single command that handles everything: prerequisites, NemoClaw bootstrap, MilimoClaw deployment, and onboarding.

**Current state:** User must manually install Docker, Node.js, NemoClaw, run a 7-step wizard, build the plugin, cross namespace boundaries with `nsenter`, fix ownership, inject JSON config, deploy support files, and run interactive onboarding.

**Target state:** `curl -fsSL https://milimo.sh/install | bash` — one command, zero manual steps, full sandbox with all 5 claws operational.

---

## Solo Template Corrections (from Spec Documents)

After thorough analysis of `MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md`, `SOLO_TEMPLATE_V2_REMEDIATION_PROMPT.md`, `SOLO_ROLE_SELECTION_FIX_PROMPT.md`, and `ASSISTANT_SETUP_AND_ONBOARDING_UPDATE_PROMPT.md`, the following corrections apply:

### Critical Corrections to Previous Plan

| Previous (Wrong) | Corrected (Per Spec) | Source |
|---|---|---|
| `--role ops` flag during onboard | **No role selection for solo template** — all 5 claws active simultaneously | `SOLO_TEMPLATE_SPEC_V2.md:34-42` |
| Solo template = single claw | Solo template = **all 5 claws** (Content, Ops, Analytics, Finance, Build) in solo-operator mode | `SOLO_TEMPLATE_SPEC_V2.md:44-58` |
| Operator has a claw role | Operator is the **human orchestrator** — claws coordinate among themselves | `SOLO_ROLE_SELECTION_FIX_PROMPT.md:15-28` |
| `solo-founder` template name | Template is **`solo`** (not `solo-founder`) — the spec uses `solo` as the canonical name | `SOLO_TEMPLATE_SPEC_V2.md:12` |
| Onboard asks for role | Onboard **skips role selection entirely** when `--solo` flag is used | `SOLO_ROLE_SELECTION_FIX_PROMPT.md:42-67` |

### Solo Template Architecture (Corrected)

```
Solo Operator (Human)
    │
    ├── Content Claw 🎨  (active — social posts, campaigns, email copy)
    ├── Ops Claw 📋      (active — inquiry triage, client lifecycle, pricing)
    ├── Analytics Claw 📊 (active — weekly reports, anomaly detection, scoring)
    ├── Finance Claw 💰  (active — invoices, Stripe monitoring, revenue)
    └── Build Claw 🔧    (active — GitHub issues, PRs, deploys, monitoring)
```

All 5 claws run concurrently. The solo operator interacts through the War Room TUI and the assistant. There is no "primary claw" — the claws coordinate via the message bus and the orchestrator's privacy router.

### Solo Template Config Structure (Per Spec)

```json
{
  "version": "2.0.0",
  "squad": {
    "name": "forge-squad",
    "template": "solo",
    "mode": "solo",
    "onboarded_at": "2026-04-04T..."
  },
  "operator": {
    "name": "Forge"
  },
  "claws": {
    "content": { "enabled": true, "mount": "/sandbox/content" },
    "ops": { "enabled": true, "mount": "/sandbox/clients" },
    "analytics": { "enabled": true, "mount": "/sandbox/analytics" },
    "finance": { "enabled": true, "mount": "/sandbox/finance" },
    "build": { "enabled": true, "mount": "/sandbox/build" }
  },
  "war_room": { "mode": "minimal" },
  "mesh": { "enabled": false },
  "inference": {
    "provider": "nvidia-prod",
    "model": "nvidia/nemotron-3-super-120b-a12b",
    "baseUrl": "https://inference.local/v1",
    "api": "openai-responses"
  },
  "blueprint_dir": "/sandbox/milimo-blueprint"
}
```

### Assistant System Prompt (Per Spec)

The assistant is **NOT a claw** — it's a conversational interface rendered from a template at setup time. The template variables are:

- `{{assistant_name}}` — e.g., "Forge"
- `{{creature}}` — e.g., "digital honey badger"
- `{{vibe}}` — e.g., "hustle-focused, no-nonsense"
- `{{emoji}}` — e.g., "🦡"
- `{{operator_name}}` — the human operator's name
- `{{squad_name}}` — the squad name

The assistant has bridge commands for querying claw status, War Room queue, financials, etc. It **cannot** approve War Room items, write to filesystem, or send client messages.

### Key Design Rules (Non-Negotiable, Per Spec)

1. **Ops Claw**: `pricing_query` MUST be sent and `pricing_response` received BEFORE `project_brief` is sent to any creative claw
2. **Build Claw**: Two SEPARATE two-stage approvals — PR REVIEW approve → HOLD → merge; Deploy is its OWN separate HOLD (merge ≠ deploy)
3. **Finance Claw**: Invoices require TWO separate operator approvals before transmission
4. **Content Claw**: Nothing publishes without operator REVIEW approval
5. **Analytics Claw**: Observes everything, acts on nothing directly — shared `weekly-intelligence.json` feeds all claws

---

## Root Cause Analysis

The fundamental problem is **architectural mismatch**: `install.sh` installs to the host machine (`/opt/milimo`), but the plugin must run inside the sandbox (`/sandbox/extensions/milimo`). These are two completely different filesystems separated by a mount namespace boundary. The installer has no mechanism to bridge this gap.

Additionally, the system requires **three separate runtimes** (NemoClaw sandbox, OpenClaw gateway, MilimoClaw plugin) each with their own config, and none of them share state automatically.

---

## Implementation Plan

### Phase 1: Pre-Build Plugin Bundle (Eliminate Build Step)

The current flow requires `npm install` + `tsc` on the target machine. This fails silently, produces ownership issues, and requires `node_modules` to be transferred separately.

- [ ] **1.1 Create a build script that produces a self-contained deploy bundle** — `scripts/build-bundle.sh` that: runs `npm install --ignore-scripts` in `milimo/`, runs `tsc`, creates a `.tar.gz` containing `dist/`, `node_modules/`, `openclaw.plugin.json`, `package.json` — everything needed to run the plugin without any build step. Set ownership at tar creation time: `--owner=sandbox --group=sandbox`. Target size: ~5MB.
- [ ] **1.2 Create a blueprint bundle** — `scripts/build-blueprint-bundle.sh` that creates a `.tar.gz` of `milimo-blueprint/` excluding `__pycache__`, `.pytest_cache`, and test files. Set ownership: `--owner=sandbox --group=sandbox`. Target size: ~2MB.
- [ ] **1.3 Add bundle versioning** — Each bundle gets a `VERSION` file and SHA256 checksum. The installer verifies checksums before deployment.
- [ ] **1.4 Update CI to produce bundles on every push** — Add a GitHub Actions job that builds both bundles and uploads them as release artifacts. This enables `curl`-based installation without cloning the repo.

**Rationale:** VS Code extensions ship as pre-built `.vsix` bundles. npm ships pre-compiled wheels. Homebrew ships pre-built bottles. MilimoClaw should ship pre-built bundles so the target machine never needs Node.js, npm, or TypeScript.

### Phase 2: Rewrite install.sh as Full Orchestrator

The current `install.sh` only handles Phase 3 of the installation. It needs to become the single orchestrator for all 4 phases.

- [ ] **2.1 Add Phase 1: Prerequisite auto-detection and guided installation** — Check for Docker (running), Node.js >= 22, Python >= 3.12, `kubectl`, `nemoclaw` CLI. For each missing dependency, provide the exact install command. If `--auto` flag is set, install automatically where possible (e.g., `brew install node` on macOS). The `NVIDIA_API_KEY` check becomes a prompt if not set as env var, not a silent warning.
- [ ] **2.2 Add Phase 2: NemoClaw bootstrap** — If `nemoclaw` CLI is not installed, clone `github.com/NVIDIA/NemoClaw` to a temp directory and run its install script. If NemoClaw is installed but not onboarded, run `nemoclaw onboard --non-interactive` with sensible defaults (model: `nvidia/nemotron-3-super-120b-a12b`, GPU: auto-detect, policy: pypi+npm). Wait for sandbox to reach `Ready` state with a progress spinner.
- [ ] **2.3 Add Phase 3: Sandbox deployment (the critical gap)** — This replaces the manual `nsenter`/`tar`/`chown`/`python -c` workflow. The installer will: (a) detect the sandbox pod name via `nemoclaw my-assistant status`, (b) find the gateway container via `docker ps`, (c) use `docker cp` + `kubectl cp` to transfer bundles into the sandbox, (d) extract to `/sandbox/extensions/milimo/` and `/sandbox/milimo-blueprint/`, (e) ownership is already correct from `--owner=sandbox` in tar creation, (f) register the plugin by injecting config into `/sandbox/.openclaw/openclaw.json` using a Python script (not a one-liner), (g) deploy the assistant system prompt template to `/sandbox/milimo-blueprint/templates/`, (h) verify plugin loaded via `openclaw plugins list`.
- [ ] **2.4 Add Phase 4: Non-interactive Milimo onboarding** — Add a `--non-interactive` flag to `openclaw milimo onboard` that accepts all config via flags/env vars. **CORRECTED per solo spec**: When `--solo` is used, the onboarding does NOT ask for a role. All 5 claws are enabled automatically. The config written includes the `claws` section with all 5 claws enabled. Accepted flags: `--solo`, `--operator-name`, `--squad-name`, `--war-room-mode`, `--yes` (skip confirmation). If flags are not provided, use defaults: squad=`milimo-squad`, operator=`user`, mode=`minimal`.
- [ ] **2.5 Add idempotency** — Running the installer twice should be safe. Detect existing NemoClaw sandbox and skip bootstrap. Detect existing MilimoClaw plugin and check version — skip if same version, upgrade if newer. Print clear status for each step: `[SKIP] NemoClaw sandbox already exists`, `[OK] MilimoClaw v2.0 already installed`, etc.
- [ ] **2.6 Add rollback** — If any phase fails, provide a `milimo uninstall` command that reverses only the steps that completed. Don't destroy the NemoClaw sandbox if MilimoClaw deployment fails — let the user fix and retry.

**Rationale:** Homebrew's `brew install` handles the full dependency chain. Docker's `docker run` handles container lifecycle. The MilimoClaw installer should do the same — one command, full lifecycle, idempotent, rollback-safe.

### Phase 3: Add `--non-interactive` Mode to Milimo Onboard Command

The `openclaw milimo onboard` command currently requires interactive terminal input via `readline`. This blocks automation.

- [ ] **3.1 Add CLI flags to `milimo/src/onboard/wizard.ts`** — `--solo` (enables all 5 claws, skips role selection entirely), `--operator-name <name>`, `--squad-name <name>`, `--war-room-mode <mode>`, `--yes` (skip confirmation). **CORRECTED per SOLO_ROLE_SELECTION_FIX_PROMPT**: When `--solo` is provided, the wizard must NOT display the role selection prompt. Instead, it writes all 5 claws as enabled in the config. The `--role` flag is ignored when `--solo` is set.
- [ ] **3.2 Add env var support** — `MILIMO_SQUAD_NAME`, `MILIMO_OPERATOR_NAME`, `MILIMO_TEMPLATE=solo`, `MILIMO_WARROOM_MODE`. Flags override env vars.
- [ ] **3.3 Update `milimo/src/onboard/config.ts`** — The `loadNemoClawConfig()` function should read inference config from OpenClaw's config file (`/sandbox/.openclaw/openclaw.json`) when NemoClaw's config is missing. This eliminates the need for the manual `.nemoclaw/config.json` workaround.
- [ ] **3.4 Add assistant system prompt generation** — When onboarding completes, render the assistant template from `milimo-blueprint/templates/assistant-system-prompt.md` with the operator's variables (`{{assistant_name}}`, `{{creature}}`, `{{vibe}}`, `{{emoji}}`, `{{operator_name}}`, `{{squad_name}}`). Write the rendered prompt to `/sandbox/milimo-blueprint/templates/rendered-assistant-prompt.md`.
- [ ] **3.5 Add `--dry-run` flag** — Print what would be configured without writing anything. Useful for CI and debugging.

**Rationale:** Every major CLI tool supports non-interactive mode (`apt-get -y`, `npm init -y`, `terraform apply -auto-approve`). The Milimo onboarding should too. The solo template spec explicitly requires that role selection be skipped for solo mode.

### Phase 4: Fix Plugin Registration Reliability

The plugin registration is the most fragile part of the entire system. It fails silently, has ownership issues, and requires manual JSON config injection.

- [ ] **4.1 Create a dedicated plugin deployment script** — `scripts/deploy-to-sandbox.sh` that handles the entire sandbox deployment: (a) accepts bundle path as argument, (b) detects gateway container and sandbox pod, (c) transfers bundle via `docker cp` + `kubectl cp`, (d) extracts with correct ownership (already set in tar), (e) calls `openclaw plugins install` inside the sandbox, (f) verifies plugin loaded. This script is called by `install.sh` Phase 3 but can also be run standalone for redeployments.
- [ ] **4.2 Fix the ownership issue at the source** — Set the tar archive to have the correct ownership at creation time: `tar --owner=sandbox --group=sandbox -czf bundle.tar.gz ...`. This eliminates the post-extraction `chown` entirely.
- [ ] **4.3 Add plugin health check** — After deployment, run `openclaw plugins list` inside the sandbox and verify Milimo Claw shows as "loaded". If not loaded, attempt auto-repair: re-run `openclaw plugins install`, check file permissions, verify `dist/index.js` exists. If still failing, print a clear error with the exact diagnostic commands to run.
- [ ] **4.4 Create a `milimo reinstall` command** — A CLI command that redeploys the plugin without touching config or blueprints. Useful when the plugin code changes but the squad config should be preserved.

**Rationale:** The current plugin deployment requires 7 manual steps with `nsenter`, PID discovery, and Python one-liners. A dedicated script reduces this to one command with clear error messages.

### Phase 5: Create the `milimo` CLI Wrapper

The `openclaw milimo` command only works inside the sandbox. Users on the host machine have no way to interact with their squad without connecting first.

- [ ] **5.1 Create a thin `milimo` CLI wrapper** — A bash script (or small Node.js CLI) installed globally on the host machine that proxies commands to the sandbox: `milimo health` → `nemoclaw my-assistant connect -- openclaw milimo health`, `milimo warroom` → `nemoclaw my-assistant connect -- openclaw milimo warroom`, `milimo status` → `nemoclaw my-assistant status`. This gives users a single entry point regardless of where they are.
- [ ] **5.2 Add `milimo install` as the primary entry point** — `milimo install` runs the full `install.sh` orchestrator. `milimo uninstall` runs the cleanup. `milimo status` shows the full system state (NemoClaw sandbox, plugin loaded, config valid, all 5 claws).
- [ ] **5.3 Add `milimo doctor`** — Diagnose common issues: plugin not loaded, config missing, inference not configured, blueprint files missing. Print actionable fix commands for each issue found.

**Rationale:** Users shouldn't need to know about `nemoclaw`, `openclaw`, `kubectl`, or `docker exec`. They should type `milimo install` and `milimo warroom`.

### Phase 6: Documentation & Developer Experience

- [ ] **6.1 Update README with one-command install** — Replace the current multi-phase setup guide with the single `curl | bash` command. Keep the detailed breakdown in a separate "Advanced Setup" section.
- [ ] **6.2 Create `QUICKSTART.md`** — A single-page guide: (1) Get NVIDIA API key, (2) Run install command, (3) Launch War Room. That's it. 3 steps, 5 minutes.
- [ ] **6.3 Update solo template documentation** — Ensure `MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md` is reflected accurately in all docs: all 5 claws active, no role selection, solo operator mode.
- [ ] **6.4 Create troubleshooting flowchart** — "Plugin not loaded?" → "Is sandbox running?" → "Is plugin registered?" → "Check ownership" → etc. Decision tree format, not prose.

---

## Target User Experience

```bash
$ curl -fsSL https://milimo.sh/install | bash

  [✓] Node.js 22.14.0
  [✓] Docker running
  [✓] NVIDIA API key configured

  [INFO] Bootstrapping NemoClaw sandbox...
  [✓] Sandbox "my-assistant" ready (142s)

  [INFO] Deploying MilimoClaw plugin...
  [✓] Plugin bundle deployed to /sandbox/extensions/milimo
  [✓] Blueprint economy deployed to /sandbox/milimo-blueprint
  [✓] Plugin registered and loaded

  [INFO] Configuring solo squad (all 5 claws active)...
  [✓] Squad: milimo-squad (solo template)
  [✓] Operator: user
  [✓] Claws: Content, Ops, Analytics, Finance, Build — all enabled
  [✓] Model: nvidia/nemotron-3-super-120b-a12b
  [✓] Assistant system prompt generated

  ──────────────────────────────────────────────────
  MilimoClaw v2.0 — Installation Complete
  ──────────────────────────────────────────────────

  Launch War Room:  milimo warroom
  Check status:     milimo status
  Connect:          nemoclaw my-assistant connect
```

---

## Verification Criteria

1. **Fresh machine test** — On a machine with only Docker and Node.js installed, `curl -fsSL https://milimo.sh/install | bash` completes successfully with zero manual intervention
2. **Idempotency test** — Running the installer a second time completes in <10 seconds with all steps showing `[SKIP]` or `[OK]`
3. **Rollback test** — Killing the installer mid-Phase 3, then running `milimo uninstall` leaves the system clean (no orphaned files, no broken NemoClaw sandbox)
4. **Plugin verification** — After install, `openclaw plugins list` inside the sandbox shows "Milimo Claw (loaded)"
5. **All 5 claws operational** — `openclaw milimo health` shows all 5 claws with green status
6. **War Room launches** — `openclaw milimo warroom` opens the TUI without errors
7. **Python tests pass** — `python -m pytest milimo-blueprint/tests/` passes with 1192+ tests
8. **Bundle integrity** — SHA256 checksum of deployed bundles matches the build output
9. **Solo template correctness** — Config has all 5 claws enabled, no role field, `mode: "solo"`
10. **Assistant prompt rendered** — `/sandbox/milimo-blueprint/templates/rendered-assistant-prompt.md` exists with correct variable substitutions

---

## Potential Risks and Mitigations

1. **NemoClaw onboarding requires interactive model selection** — The `nemoclaw onboard` wizard may not support `--non-interactive` mode
   - *Mitigation*: If non-interactive mode isn't available, use `expect` scripting or create a minimal NemoClaw config file directly. Document this as a known limitation.

2. **Docker Desktop on macOS has limited kubectl access** — The k3s cluster runs inside a Docker container, making `kubectl` commands from the host unreliable
   - *Mitigation*: Always route kubectl commands through `docker exec <gateway-container> kubectl`. The deploy script already does this.

3. **Bundle size grows over time** — Including `node_modules` in the bundle means it grows with every dependency update
   - *Mitigation*: Use `npm prune --production` before bundling. Target <10MB. If it grows beyond that, switch to a Docker image-based distribution.

4. **OpenClaw plugin API changes** — Future OpenClaw versions may change the plugin registration mechanism
   - *Mitigation*: Pin OpenClaw version in the Dockerfile and bundle. Test against latest OpenClaw in CI weekly.

5. **NVIDIA API key requirement** — Users must have an NVIDIA API key, which requires signing up at build.nvidia.com
   - *Mitigation*: The installer prompts for the API key with a clickable link. Offer a "demo mode" that uses a free tier or mock inference for testing.

6. **Solo template role confusion** — Users may expect to pick a claw role even in solo mode
   - *Mitigation*: The `--solo` flag explicitly skips role selection. The installer output clearly states "all 5 claws active" to prevent confusion.

---

## Alternative Approaches

1. **Docker Image Distribution**: Instead of bundling and deploying to the sandbox, publish a MilimoClaw Docker image that NemoClaw can use as its sandbox base. Users would run `nemoclaw onboard --image ghcr.io/mainza-ai/milimo-claw:latest`. This is the cleanest approach but requires NemoClaw to support custom sandbox images.

2. **OpenClaw Plugin Registry**: Publish MilimoClaw to an OpenClaw plugin registry so installation becomes `openclaw plugins install milimo`. This requires OpenClaw to have a public registry, which may not exist yet.

3. **Homebrew Formula**: Create a `milimo-claw` Homebrew formula that handles the entire installation chain. This works great on macOS but doesn't help Linux users.

4. **Keep current approach, fix the gaps**: Instead of a full rewrite, fix the specific gaps: add sandbox deployment to `install.sh`, add `--non-interactive` to onboard, fix plugin registration. This is the lowest-risk approach but doesn't solve the fundamental UX problem.

---

## Recommended Approach

**Phase 1-4 should be implemented immediately** — they address the root causes of the installation friction without requiring external changes (OpenClaw registry, NemoClaw custom images).

**Phase 5 (CLI wrapper) should be implemented next** — it gives users a clean entry point.

**Phase 6 (documentation) should be implemented last** — it communicates the improved experience.

The Docker Image Distribution (Alternative 1) is the ideal long-term solution and should be pursued in parallel as a research item with the NemoClaw team.
