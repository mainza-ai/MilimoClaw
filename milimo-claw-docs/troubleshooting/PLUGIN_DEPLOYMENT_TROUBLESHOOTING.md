> ⚠️ **DEPRECATED** — Resolved issues from the old deployment flow. No longer actionable.
>
> Kept for historical reference only.

---

# Milimo Claw Plugin Deployment Troubleshooting

**Date:** 2026-03-27
**Status:** ✅ RESOLVED
**Issue:** Deploying Milimo Claw plugin to NemoClaw sandbox

---

## Summary

This document tracks the attempts to deploy the Milimo Claw plugin (with the solo role selection fix) to a NemoClaw sandbox for testing. The deployment process is complex due to the sandbox's isolation mechanisms (mount namespaces, overlayfs, and filesystem policies).

**Resolution:** The plugin was successfully deployed and loaded. Four root causes were identified:
1. **Missing `node_modules`** — The tar archive omitted runtime dependencies (`blessed`, `commander`, `ws`, `yaml`, `zod`), causing the plugin to load in `error` state.
2. **Wrong install path in `openclaw.json`** — The config pointed `sourcePath`/`installPath` to `/tmp` (world-writable, mode 777), which OpenClaw's security policies block.
3. **Wrong user context** — Plugin was installed under `/root/.openclaw/` (root user), but `nemoclaw connect` runs as the `sandbox` user (uid 999, home `/sandbox`) which cannot access `/root/`. The plugin must be at `/sandbox/extensions/milimo/` and registered in `/sandbox/.openclaw/openclaw.json`.
4. **Solo template showed role selection** — A readline race condition caused the "Operating solo?" confirmation to malfunction, dropping the solo-founder template into mesh mode and prompting the user to select a single claw instead of activating all six.

---

## Fixes Applied

### Fix 1: `solo` variable not updated (original const → let fix)

**File:** `milimo/src/commands/onboard.ts`

**The Bug:** The `solo` variable was declared with `const`, so the mesh mode branch could never update it to `false`.

**The Fix:** Changed `const` to `let` and added `solo = false` in the mesh branch.

```diff
-const solo = opts.solo ?? selectedTemplate?.solo ?? true;
+let solo = opts.solo ?? selectedTemplate?.solo ?? true;
 if (!opts.solo && !nonInteractive) {
   const soloConfirm = await promptConfirm("Operating solo?", true);
   if (!soloConfirm) {
-    // Shows mesh info BUT NEVER UPDATES `solo`
+    solo = false;  // ← FIX: Update the variable
   }
 }
```

**Status:** ✅ Deployed and working.

---

### Fix 2: Solo template incorrectly shows role selection

**File:** `milimo/src/commands/onboard.ts`

**The Bug:** Even after Fix 1, selecting the Solo Founder template and answering "Y" to "Operating solo?" still triggered the mesh mode role selection prompt ("Select [1-5]"). Root cause: a readline race condition in Node.js where multiple sequential `readline.createInterface()` calls on the same stdin buffer cause input leakage between prompts. The "Y" answer to the solo confirm was consumed by the next prompt (squad name), leaving the solo confirm returning an empty string.

**The Fix:** Skip the solo confirmation prompt entirely when the selected template declares `solo: true`. A template called "Solo Founder" is solo by definition — asking the user to confirm is redundant and triggers the race condition.

```diff
 let solo = opts.solo ?? selectedTemplate?.solo ?? true;
-if (!opts.solo && !nonInteractive) {
+if (selectedTemplate?.solo) {
+    // Template is definitively solo — no confirmation needed
+    if (!nonInteractive) {
+      logger.info(`Template "${selectedTemplate.displayName}" runs all claws on one machine.`);
+    }
+} else if (!opts.solo && !nonInteractive) {
     const soloConfirm = await promptConfirm("Operating solo?", true);
     if (!soloConfirm) {
       solo = false;
     }
 }
```

**Result:** Solo Founder now correctly activates all six claws without asking for role selection.

**Status:** ✅ Deployed and working.

---

### Fix 3: Assistant setup fails inside sandbox

**File:** `milimo-blueprint/orchestrator/assistant_setup.py`

**The Bug:** The system prompt template path was hardcoded as a relative path (`milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md`) and the agent config output used `Path(".openclaw")` (CWD-relative). Neither resolves correctly inside the sandbox.

**The Fix:**
1. Added `find_template()` function that searches multiple candidate paths (relative dev path, plugin dir, `~/.milimo/`)
2. Changed `OPENCLAW_AGENTS_DIR` to use `Path.home() / ".openclaw"` so it resolves to `/sandbox/.openclaw/` inside the sandbox
3. Copied the template file to `/sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md`

**Status:** ✅ Deployed and working.

---

## Architecture Overview

### NemoClaw Sandbox Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ Host Machine (macOS/Linux)                                      │
│                                                                 │
│ Docker Container: openshell-cluster-nemoclaw                    │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ OpenShell Gateway + K3s + Containerd                       │   │
│ │                                                           │   │
│ │ Sandbox Process (runs OpenClaw as user: sandbox, uid 999) │   │
│ │ ┌─────────────────────────────────────────────────────┐   │   │
│ │ │ Mount Namespace (isolated filesystem)               │   │   │
│ │ │                                                     │   │   │
│ │ │ /sandbox/extensions/milimo/  ← PLUGIN LOCATION     │   │   │
│ │ │ ├── dist/           # Compiled TypeScript           │   │   │
│ │ │ ├── node_modules/   # Runtime dependencies          │   │   │
│ │ │ ├── openclaw.plugin.json  # Plugin manifest         │   │   │
│ │ │ └── package.json    # NPM config                    │   │   │
│ │ │                                                     │   │   │
│ │ │ /sandbox/.openclaw/openclaw.json  ← SANDBOX CONFIG  │   │   │
│ │ │ /root/.openclaw/openclaw.json     ← ROOT CONFIG     │   │   │
│ │ │   (not used by sandbox user!)                       │   │   │
│ │ └─────────────────────────────────────────────────────┘   │   │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Paths

| Location | Path | Description |
|----------|------|-------------|
| Local source | `/Users/mck/Desktop/MilimoClaw/milimo/` | Development directory |
| Local dist | `/Users/mck/Desktop/MilimoClaw/milimo/dist/` | Compiled output |
| Container root | `/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/` | Container snapshots |
| **Plugin install (working)** | **`/sandbox/extensions/milimo/`** | **✅ Writable, readable by sandbox user** |
| Sandbox config | `/sandbox/.openclaw/openclaw.json` | Config used by `nemoclaw connect` sessions (sandbox user) |
| Root config | `/root/.openclaw/openclaw.json` | Config used by root-level nsenter (NOT sandbox user) |
| Sandbox data extensions | `/sandbox/.openclaw-data/extensions/` | Symlinked from `.openclaw/extensions` — overlayfs blocks writes |
| Root extensions | `/root/.openclaw/extensions/milimo/` | Only accessible as root, NOT sandbox user |

---

## Steps That Worked

### 1. Building the Plugin Locally ✅

```bash
cd /Users/mck/Desktop/MilimoClaw/milimo
npm run build
```

**Result:** Successfully compiled TypeScript to `dist/`. Fix verified at `dist/commands/onboard.js:164`.

### 2. Creating Sandbox via NemoClaw Onboard ✅

```bash
NVIDIA_API_KEY="nvapi-..." NEMOCLAW_RECREATE_SANDBOX=1 nemoclaw onboard --non-interactive
```

**Result:** Sandbox `my-assistant` created successfully with:
- Model: ${NEMOCLAW_MODEL}
- Provider: nvidia-nim
- Policies: pypi, npm
- Phase: Ready

### 3. Connecting to Sandbox ✅

```bash
nemoclaw my-assistant connect
```

**Result:** SSH tunnel established, interactive shell available in sandbox namespace.

### 4. Transferring Files via Pipe ✅

The sandbox has its own mount namespace, so the container's `/tmp` is separate from the sandbox's `/tmp`. The solution:

```bash
# Create tar locally
cd /Users/mck/Desktop/MilimoClaw/milimo
tar czf /tmp/milimo-plugin.tar.gz dist openclaw.plugin.json package.json

# Pipe into sandbox namespace (find PID first)
docker exec openshell-cluster-nemoclaw nsenter -t <SANDBOX_PID> -a -- bash -c 'cat > /tmp/milimo-plugin.tar.gz'
```

**Key insight:** `docker exec -i` with pipe works because stdin is shared across namespaces.

### 5. Extracting Files Inside Sandbox ✅

```bash
docker exec openshell-cluster-nemoclaw nsenter -t <SANDBOX_PID> -a -- bash -c 'cd /tmp && tar xzf milimo-plugin.tar.gz'
```

**Result:** Files extracted to `/tmp/dist/`, `/tmp/openclaw.plugin.json`, `/tmp/package.json`.

---

## Steps That Did NOT Work

### 1. Direct Copy to Container Path ❌

```bash
docker cp ./dist openshell-cluster-nemoclaw:/tmp/milimo-dist/
docker exec openshell-cluster-nemoclaw bash -c 'cp -r /tmp/milimo-dist/* /var/lib/rancher/.../snapshots/90/fs/sandbox/.openclaw-data/extensions/milimo/dist/'
```

**Problem:** Files copied to the overlayfs upperdir are NOT visible inside the sandbox namespace due to overlayfs caching. The sandbox's view of the filesystem is established when the sandbox process starts.

### 2. Restarting Gateway to Reload Files ❌

```bash
docker exec openshell-cluster-nemoclaw kill -HUP <GATEWAY_PID>
```

**Problem:** This killed the gateway process and caused the sandbox to crash. The sandbox requires a full restart cycle, not a signal reload.

### 3. Installing from World-Writable Path ❌

```bash
docker exec openshell-cluster-nemoclaw nsenter -t <SANDBOX_PID> -a -- openclaw plugins install -l /tmp
```

**Error:**
```
plugins: plugin: blocked plugin candidate: world-writable path (/tmp, mode=777)
plugins: plugin: blocked plugin candidate: suspicious ownership (... uid=506, expected uid=0 or root)
```

**Problem:** OpenClaw's security checks reject plugins from world-writable directories and files with non-root ownership.

### 4. npm install During Plugin Install ❌

```bash
openclaw plugins install /tmp
```

**Problem:** The `npm install` step for dependencies times out. The sandbox has limited resources and network access, making dependency installation very slow.

### 5. Writing to `/sandbox/.openclaw-data/extensions/` ❌

```bash
touch /sandbox/.openclaw-data/extensions/test.txt
```

**Error:** `Directory not empty`

**Problem:** There's an overlayfs or filesystem policy issue preventing writes to this directory from within the sandbox, despite it appearing empty.

---

## Root Cause Analysis

The plugin deployment failed for three reasons:

### 1. Missing `node_modules` (Primary Cause)

The original tar archive only included `dist/`, `openclaw.plugin.json`, and `package.json`. The plugin has 5 runtime dependencies that were not bundled:

| Dependency | Purpose |
|------------|---------|
| `blessed` | Terminal UI for War Room dashboard |
| `commander` | CLI command parsing |
| `ws` | WebSocket client for mesh coordination |
| `yaml` | YAML config/template parsing |
| `zod` | Runtime schema validation |

Without `node_modules`, the plugin's `require()` calls failed at load time, causing OpenClaw to report the plugin as `error` status.

### 2. Wrong Install Path in `openclaw.json` (Secondary Cause)

The `openclaw plugins install /tmp` command (from an earlier attempt) registered the plugin with `/tmp` as both `sourcePath` and `installPath`. OpenClaw's security checks reject plugins from:
- **World-writable directories** — `/tmp` has mode `777`
- **Non-root ownership** — Files piped from macOS retained uid `506`

### 3. Root vs Sandbox User Context (Tertiary Cause)

The sandbox has **two separate users** with **two separate OpenClaw configs**:

| User | UID | Home | Config | Used by |
|------|-----|------|--------|---------|
| `root` | 0 | `/root` | `/root/.openclaw/openclaw.json` | `nsenter` commands from host |
| `sandbox` | 999 | `/sandbox` | `/sandbox/.openclaw/openclaw.json` | `nemoclaw connect` sessions |

The initial fix installed the plugin to `/root/.openclaw/extensions/milimo/` and updated `/root/.openclaw/openclaw.json`. This worked when testing via `nsenter` (runs as root), but **`nemoclaw connect` drops you into the sandbox as the `sandbox` user** which:
- Cannot read `/root/` (mode `drwx------`, root-only)
- Uses `/sandbox/.openclaw/openclaw.json` as its config
- Had no plugin entries in its config

Additionally, `openclaw plugins install --link` fails inside the sandbox because `/sandbox/.openclaw/extensions` is a symlink to `/sandbox/.openclaw-data/extensions`, and OpenClaw requires a real directory (not a symlink) as the extensions base.

**Solution:** Install plugin to `/sandbox/.openclaw-data/milimo/extensions/` (writable under `.openclaw-data`, not a symlink, not world-writable) with `sandbox:sandbox` ownership, and register it in `/sandbox/.openclaw/openclaw.json`.

### 4. Solo Template Onboard Dropped to Mesh Mode (Quaternary Cause)

After deployment, running `openclaw milimo onboard` and selecting the Solo Founder template still asked the user to pick a single claw role (1-6) instead of activating all six claws.

**Symptoms:**
- User selects "Solo Founder" template
- User answers "Y" to "Operating solo?"
- Wizard immediately shows "Mesh mode — which claw are you running on this machine?"
- User forced to select a single role instead of getting all 6 claws

**Root cause:** Node.js readline race condition. The onboard wizard creates a new `readline.createInterface()` for every prompt (confirm, input, select) and closes it immediately after. When multiple readline interfaces are created/destroyed rapidly on the same stdin, buffered input leaks between prompts. The "Y" answer gets consumed by the squad name prompt, and the solo confirm returns empty — which evaluates as `false`, setting `solo = false`.

**Solution:** Skip the solo confirmation prompt entirely when the template declares `solo: true`. The Solo Founder template IS solo by definition — there is no scenario where the user selects "Solo Founder" but wants mesh mode.

### 5. Assistant Setup Path Resolution (Quinary Cause)

The `assistant_setup.py` script used relative paths that only work when CWD is the project root on the host machine. Inside the sandbox, these paths don't resolve.

**Solution:** Use `Path.home()` for config and output paths. Search multiple candidate locations for the template file. Copy the template into `~/.milimo/` during deployment.

---

## ✅ Working Solution

The complete, verified deployment procedure from host to loaded plugin:

### Step 1: Build the Plugin Locally

```bash
cd /Users/mck/Desktop/MilimoClaw/milimo
npm install
npm run build
```

### Step 2: Create a Complete Tar Archive

> **Critical:** Include `node_modules` and use `--no-mac-metadata` to avoid macOS `._*` resource fork files.

```bash
cd /Users/mck/Desktop/MilimoClaw/milimo
COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-full.tar.gz \
  --no-mac-metadata \
  dist openclaw.plugin.json package.json node_modules
```

### Step 3: Find the Sandbox PID

```bash
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}')
echo "Sandbox PID: $PID"
```

### Step 4: Pipe Archive into Sandbox Namespace

```bash
cat /tmp/milimo-plugin-full.tar.gz | \
  docker exec -i openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  bash -c 'cat > /tmp/milimo-plugin-full.tar.gz'
```

### Step 5: Extract, Copy, and Fix Ownership

> **Important:** Plugin must go to `/sandbox/extensions/milimo/` — NOT `/root/.openclaw/extensions/`.
> The `sandbox` user (used by `nemoclaw connect`) cannot access `/root/`.

```bash
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c '
  # Extract to temp
  mkdir -p /tmp/milimo-extract
  cd /tmp/milimo-extract
  tar xzf /tmp/milimo-plugin-full.tar.gz --warning=no-unknown-keyword

  # Copy to sandbox-accessible extensions directory
  mkdir -p /sandbox/extensions/milimo
  rm -rf /sandbox/extensions/milimo/*
  cp -r dist openclaw.plugin.json package.json node_modules \
    /sandbox/extensions/milimo/

  # Fix ownership (sandbox:sandbox — the user that runs openclaw)
  chown -R sandbox:sandbox /sandbox/extensions/milimo

  # Clean up macOS resource fork files if any leaked through
  find /sandbox/extensions/milimo -name "._*" -delete
'
```

### Step 6: Update Sandbox `openclaw.json` Config

The sandbox user reads its config from `/sandbox/.openclaw/openclaw.json` (NOT `/root/.openclaw/openclaw.json`). We need to inject plugin entries into the existing sandbox config:

```bash
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- python3 -c "
import json
with open('/sandbox/.openclaw/openclaw.json') as f:
    config = json.load(f)

config['plugins'] = {
    'load': {
        'paths': ['/sandbox/extensions/milimo']
    },
    'entries': {
        'milimo': {
            'enabled': True
        }
    },
    'installs': {
        'milimo': {
            'source': 'path',
            'sourcePath': '/sandbox/extensions/milimo',
            'installPath': '/sandbox/extensions/milimo',
            'version': '0.1.0',
            'installedAt': '2026-03-27T18:50:00.000Z'
        }
    }
}

with open('/sandbox/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print('Sandbox config updated successfully')
"
```

> **Note:** This preserves the existing model/gateway/agent config and only adds the `plugins` section.
> The config file is owned by root but readable by sandbox. We write as root (via nsenter).

### Step 7: Verify Plugin Loads (as sandbox user)

Test as the sandbox user (same context as `nemoclaw connect`):

```bash
# Check plugin status (should show "loaded")
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  su - sandbox -c "openclaw plugins list 2>&1" | grep milimo

# Verify commands are available
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  su - sandbox -c "openclaw milimo --help 2>&1" | tail -20

# Verify the solo fix is present
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  grep -n "solo = false" /sandbox/extensions/milimo/dist/commands/onboard.js
```

Or connect interactively and test directly:
```bash
nemoclaw my-assistant connect
# Inside sandbox:
openclaw milimo --help
openclaw milimo onboard
```

**Expected output for plugin list:**
```
│ Milimo Claw  │ milimo   │ loaded   │ ~/extensions/milimo/dist/index.js │ 0.1.0 │
```

---

## One-Liner Quick Deploy (Copy-Paste Ready)

For subsequent deployments after the initial setup:

```bash
# Full redeploy from host (run from MilimoClaw/milimo directory)
cd /Users/mck/Desktop/MilimoClaw/milimo && \
  npm run build && \
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-full.tar.gz --no-mac-metadata dist openclaw.plugin.json package.json node_modules && \
  PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}') && \
  cat /tmp/milimo-plugin-full.tar.gz | docker exec -i openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c 'cat > /tmp/milimo-plugin-full.tar.gz' && \
  docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c '
    mkdir -p /tmp/milimo-extract && cd /tmp/milimo-extract && \
    tar xzf /tmp/milimo-plugin-full.tar.gz --warning=no-unknown-keyword && \
    mkdir -p /sandbox/extensions/milimo && \
    rm -rf /sandbox/extensions/milimo/* && \
    cp -r dist openclaw.plugin.json package.json node_modules /sandbox/extensions/milimo/ && \
    chown -R sandbox:sandbox /sandbox/extensions/milimo && \
    find /sandbox/extensions/milimo -name "._*" -delete
  ' && \
  echo "✅ Plugin deployed successfully"
```

---

## Useful Commands Reference

### Find Sandbox Process

```bash
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}')
echo "Sandbox PID: $PID"
```

### Check Plugin Files in Sandbox

```bash
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- ls -la /sandbox/extensions/milimo/
```

### Verify Runtime Dependencies

```bash
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  ls /sandbox/extensions/milimo/node_modules/ | grep -E '^(blessed|commander|ws|yaml|zod)$'
```

### Check Plugin Load Status (as sandbox user)

```bash
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  su - sandbox -c "openclaw plugins list 2>&1" | grep milimo
```

### Verify Solo Fix in Deployed Files

```bash
# Verify solo template skips confirmation (new fix)
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  grep -c "definitively solo" /sandbox/extensions/milimo/dist/commands/onboard.js
# Should return 1

# Verify old const→let fix is present
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  grep -n "let solo = " /sandbox/extensions/milimo/dist/commands/onboard.js
```

### Verify Assistant Template is Available

```bash
# Check template file exists in sandbox
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  ls -la /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md

# Check assistant_setup.py is deployed
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  ls -la /sandbox/milimo-blueprint/orchestrator/assistant_setup.py
```

### Sandbox Status

```bash
nemoclaw my-assistant status
nemoclaw my-assistant logs --tail 50
```

### Restart Everything (Full Reset)

```bash
# Destroy sandbox
nemoclaw my-assistant destroy --yes

# Recreate sandbox
NVIDIA_API_KEY="nvapi-..." NEMOCLAW_RECREATE_SANDBOX=1 nemoclaw onboard --non-interactive

# Connect (opens interactive shell)
nemoclaw my-assistant connect
```

---

## Error Messages Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `unknown command 'milimo'` | Plugin not registered in sandbox user's config | Update `/sandbox/.openclaw/openclaw.json` (not `/root/.openclaw/`) |
| `plugin status: error` | Missing `node_modules` — runtime deps can't resolve | Include `node_modules` in tar archive |
| Solo template shows role selection (1-5) | Readline race condition — solo confirm answer consumed by next prompt | Fixed: solo templates now skip the confirmation prompt entirely |
| `Directory not empty` | Overlayfs blocks writes to `/sandbox/.openclaw-data/extensions/` | Use `/sandbox/extensions/` instead |
| `Invalid extensions directory: base directory must be a real directory` | Extensions path is a symlink | Use `/sandbox/extensions/` (a real dir, not symlinked) |
| `world-writable path` | Plugin installed from `/tmp` (mode 777) | Copy to non-world-writable directory |
| `suspicious ownership` | Files owned by non-root user (e.g. uid 506 from macOS) | `chown -R sandbox:sandbox <path>` |
| `plugin not found` | Plugin not registered in config | Update the correct `openclaw.json` for the user context |
| `Permission denied` accessing `/root/.openclaw/` | Sandbox user (uid 999) can't read root's home | Install to `/sandbox/extensions/milimo/` instead |
| `nsenter: stat of /proc/<PID>/ns/user failed` | Process died or wrong PID | Find new PID: `ps aux \| grep "sleep infinity"` |
| `npm install timeout` | Slow dependency installation inside sandbox | Pre-install deps on host and include `node_modules` in archive |
| macOS `._*` resource fork files | `tar` on macOS adds metadata files | Use `COPYFILE_DISABLE=1` and `--no-mac-metadata` flags |
| `dangerous code patterns` warning | OpenClaw scans for credential harvesting | Informational warning, plugin still loads |
| `System prompt template not found` | `assistant_setup.py` can't find template in sandbox | Copy template to `~/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md` |

---

## Key Lessons Learned

1. **Know the user context:** `nemoclaw connect` runs as `sandbox` (uid 999, home `/sandbox`), NOT root. Always deploy plugins to a sandbox-accessible path.
2. **Two separate configs exist:** `/sandbox/.openclaw/openclaw.json` is used by sandbox sessions; `/root/.openclaw/openclaw.json` is only for root. Update the correct one.
3. **Always include `node_modules`** in the tar archive. The sandbox has limited network access and `npm install` times out.
4. **Use `COPYFILE_DISABLE=1 tar --no-mac-metadata`** on macOS to prevent `._*` resource fork files from contaminating the archive.
5. **Never use `/tmp` as the plugin install path** — OpenClaw's security rejects world-writable directories. Use `/sandbox/extensions/milimo/`.
6. **Use `/sandbox/extensions/`** not `/sandbox/.openclaw-data/extensions/` — the latter has overlayfs issues and symlink problems that block `openclaw plugins install`.
7. **Use pipe transfer** (`cat | docker exec -i nsenter`) to cross the mount namespace boundary — `docker cp` writes to the container's overlayfs, not the sandbox's namespace.
8. **Ownership must match the running user** — `sandbox:sandbox` for sandbox sessions, `root:root` for root-level access.
9. **Skip redundant prompts for declarative templates** — If a template declares `solo: true`, do not ask the user to confirm. Node.js readline race conditions between sequential prompts can cause answers to leak between questions.
10. **Deploy support files alongside the plugin** — The assistant system prompt template and `assistant_setup.py` must be copied to the sandbox separately. They are not part of the plugin archive but are required for onboard completion.
11. **Use `Path.home()` not relative paths in Python scripts** — Inside the sandbox, CWD is `/sandbox` and relative paths to project directories don't exist. Always use home-relative or absolute paths.
