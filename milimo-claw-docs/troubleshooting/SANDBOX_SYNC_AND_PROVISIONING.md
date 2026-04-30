# Sandbox Sync & Provisioning Troubleshooting

**Date:** 2026-04-06
**Status:** Active
**Issue:** Assistant sees stale/truncated files, missing CLI tools, and broken Python environment

---

## Root Cause: Two Separate Environments

MilimoClaw runs in **two completely separate environments** that are easy to confuse:

| Environment | What It Is | How It's Managed |
|---|---|---|
| **Docker Container** (`MilimoClaw`) | Standalone container with baked-in blueprint | `docker exec MilimoClaw ...` |
| **NemoClaw Sandbox** (`my-assistant`) | OpenShell/K3s-managed sandbox pod | `openshell sandbox upload/download my-assistant ...` |

**Critical:** The assistant (Lucy) runs inside the **NemoClaw sandbox** (`my-assistant`), NOT the Docker container. Any fixes applied to the Docker container will NOT be visible to the assistant.

---

## Issue 1: Assistant Sees Truncated bridge_cli.py

### Symptoms
- Assistant reports `bridge_cli.py` is 239 lines and ends with `logger.exception("Failed to diff`
- Host machine shows 1,878 lines — file is complete
- Docker container shows 1,878 lines — file is complete
- Assistant is reading from `/sandbox/milimo-blueprint/orchestrator/bridge_cli.py`

### Root Cause
The sandbox (`my-assistant`) has its own copy of the blueprint files that was deployed at an earlier point in time. Changes made to the host filesystem or Docker container do NOT automatically sync to the sandbox. The sandbox's copy was from before the Phase 2-6 fixes were applied.

### Fix
Upload the corrected file to the sandbox:

```bash
# From host machine
openshell sandbox upload my-assistant \
  /path/to/MilimoClaw/milimo-blueprint/orchestrator/bridge_cli.py \
  /sandbox/milimo-blueprint/orchestrator/bridge_cli.py
```

Also copy to the blueprint version path (where the milimo CLI wrapper reads from):

```bash
openshell sandbox upload my-assistant \
  /path/to/MilimoClaw/milimo-blueprint/orchestrator/ \
  /sandbox/.milimo/blueprints/0.1.0/orchestrator/
```

### Verify
```bash
openshell sandbox download my-assistant \
  /sandbox/milimo-blueprint/orchestrator/bridge_cli.py \
  /tmp/verify_bridge_cli.py

wc -l /tmp/verify_bridge_cli.py
# Should show: 1878
```

---

## Issue 2: milimo CLI Not Found in Sandbox

### Symptoms
- Assistant reports `milimo: command not found`
- `milimo` CLI exists on host at `~/.local/bin/milimo` (macOS binary)
- Not available inside the sandbox

### Root Cause
The `milimo` CLI on the host is a compiled macOS/ARM binary. It cannot run inside the Linux sandbox. The sandbox needs its own Python-based wrapper.

### Fix
Create the wrapper script inside the sandbox:

```bash
# Create locally first
cat > /tmp/milimo-wrapper << 'SCRIPT'
#!/usr/bin/env python3
"""Milimo Claw CLI wrapper — delegates to bridge_cli.py"""
import sys
BLUEPRINT_PATH = "/sandbox/.milimo/blueprints/0.1.0"
if BLUEPRINT_PATH not in sys.path:
    sys.path.insert(0, BLUEPRINT_PATH)
from orchestrator.bridge_cli import main
if __name__ == "__main__":
    main()
SCRIPT
chmod +x /tmp/milimo-wrapper

# Upload to sandbox
openshell sandbox upload my-assistant \
/tmp/milimo-wrapper \
/sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py
```

Add to PATH in shell profiles:

```bash
# Upload updated .bashrc (append to existing)
echo 'export PATH=$HOME/.local/bin:$PATH' | \
  openshell sandbox upload my-assistant /dev/stdin /tmp/path_update.sh

# Then inside sandbox, run: cat /tmp/path_update.sh >> /sandbox/.bashrc
```

### Verify
```bash
openshell sandbox download my-assistant /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py /tmp/verify_milimo
head -3 /tmp/verify_milimo
# Should show the Python wrapper script
```

---

## Issue 3: gh CLI Architecture Mismatch

### Symptoms
- Assistant reports `gh` binary gives "Rosetta error" or "exec format error"
- `gh` was uploaded but doesn't execute

### Root Cause
The sandbox runs **Linux ARM64** (aarch64). Uploading a macOS ARM binary or Linux x86-64 binary will fail. The correct binary is `gh_*_linux_arm64.tar.gz`.

### Fix
Download the correct architecture and upload:

```bash
# On host — download Linux ARM64 binary
cd /tmp
curl -sL https://github.com/cli/cli/releases/download/v2.67.0/gh_2.67.0_linux_arm64.tar.gz -o gh.tar.gz
tar xzf gh.tar.gz

# Verify architecture
file gh_2.67.0_linux_arm64/bin/gh
# Should show: ELF 64-bit LSB executable, ARM aarch64

# Upload to sandbox
openshell sandbox upload my-assistant \
  /tmp/gh_2.67.0_linux_arm64/bin/gh \
  /sandbox/.local/bin/gh
```

### Auto-Detect Architecture (for install.sh)
```bash
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
  GH_ARCH="arm64"
else
  GH_ARCH="amd64"
fi
GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"
```

---

## Issue 4: Python Dependencies Missing in Sandbox

### Symptoms
- Python imports fail: `ModuleNotFoundError: No module named 'yaml'`
- `requests`, `stripe`, `httpx`, `sentry_sdk` all unavailable
- Claws run in "stub mode" because imports fail

### Root Cause
The sandbox's Python installation only has `pip`, `setuptools`, and `wheel`. No third-party packages are pre-installed. The `install.sh` script now handles this, but existing sandboxes need manual provisioning.

### Fix
Install packages into the sandbox's site-packages:

```bash
# On host — install packages to a target directory
mkdir -p /tmp/python_packages
pip3 install --target /tmp/python_packages \
  pyyaml requests stripe httpx sentry-sdk typing_extensions

# Remove any platform-specific .so files (macOS won't work on Linux)
find /tmp/python_packages -name "*.so" -delete

# Upload each package to sandbox
for pkg in yaml requests stripe httpx httpcore anyio certifi idna urllib3 charset_normalizer h11 sentry_sdk typing_extensions; do
  if [ -d "/tmp/python_packages/$pkg" ]; then
    openshell sandbox upload my-assistant \
      "/tmp/python_packages/$pkg" \
      "/sandbox/.local/lib/python3.11/site-packages/$pkg"
  fi
done

# Also upload dist-info metadata
for pkg in pyyaml-6.0.3 requests-2.33.1 stripe-15.0.1 httpx-0.28.1 httpcore-1.0.9 anyio-4.13.0 certifi-2026.2.25 idna-3.11 urllib3-2.6.3 charset_normalizer-3.4.7 h11-0.16.0 typing_extensions-4.15.0 sentry_sdk-2.57.0; do
  if [ -d "/tmp/python_packages/$pkg.dist-info" ]; then
    openshell sandbox upload my-assistant \
      "/tmp/python_packages/$pkg.dist-info" \
      "/sandbox/.local/lib/python3.11/site-packages/$pkg.dist-info"
  fi
done
```

### Verify
```bash
openshell sandbox download my-assistant \
  /sandbox/.local/lib/python3.11/site-packages/ \
  /tmp/verify_packages/

ls /tmp/verify_packages/ | grep -E "yaml|requests|stripe|httpx|sentry"
# Should show: yaml, requests, stripe, httpx, sentry_sdk (+ dist-info)
```

---

## Issue 5: Broken Python Virtual Environment

### Symptoms
- `.venv` points to `/opt/homebrew/opt/python@3.14/bin/python3.14` which doesn't exist in sandbox
- `source .venv/bin/activate` fails or uses wrong Python
- The sandbox has Python 3.11.2, not 3.14

### Root Cause
The `.venv` directory was created on the macOS host with Python 3.14 (Homebrew). When deployed to the sandbox, the symlinks and `pyvenv.cfg` still reference the host's Python path.

### Fix
Recreate the venv inside the sandbox with the sandbox's Python:

```bash
# Upload a fix script
cat > /tmp/fix_venv.sh << 'SCRIPT'
#!/bin/bash
BLUEPRINT_DIR="/sandbox/milimo-blueprint"
VENV_DIR="$BLUEPRINT_DIR/.venv"

# Remove broken venv
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
fi

# Create fresh venv with sandbox Python
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --quiet pyyaml requests stripe httpx sentry-sdk typing_extensions

# Verify
python3 -c "import yaml, requests, stripe, httpx, sentry_sdk; print('venv OK')"
SCRIPT
chmod +x /tmp/fix_venv.sh

# Upload and execute in sandbox
openshell sandbox upload my-assistant /tmp/fix_venv.sh /tmp/fix_venv.sh
# Then inside sandbox: bash /tmp/fix_venv.sh
```

---

## Issue 6: Missing /sandbox/.openclaw-data/milimo/claws/ops Directory

### Symptoms
- Ops claw reports "sandbox not initialized"
- `/sandbox/.openclaw-data/milimo/claws/ops/` doesn't exist
- Ops primary mount path from blueprint is `/sandbox/.openclaw-data/milimo/claws/ops`

### Root Cause
The `install.sh` script now creates sandbox directories, but existing sandboxes may not have been initialized with the correct directory structure.

### Fix
Create the directory structure:

```bash
# Create locally
mkdir -p /tmp/clients_init/{clients/{active,archived},projects/{active,completed},calendar,queue/{hold,review,auto},memory,context,logs,tools}

# Upload to sandbox
openshell sandbox upload my-assistant \
/tmp/clients_init/ \
/sandbox/.openclaw-data/milimo/claws/ops/
```

---

## Issue 7: Banner Renders as Garbage Text

### Symptoms
- `install.sh` banner shows "MEMOGOE" or other garbled text instead of "MILIMOCLAW"

### Root Cause
The original banner used Unicode block-drawing characters (`███╗`, `╚═╝`, etc.) that some terminals/fonts render incorrectly.

### Fix
The banner has been replaced with plain ASCII characters. Update `install.sh` to use the ASCII-only version:

```
M   M  IIIII  L     IIIII  M   M   OOOO    CCCC  L     A   A   W   W
MM MM    I    L       I    MM MM  O    O  C      L    A A A A  W W W
M M M    I    L       I    M M M  O    O  C      L    A A A A  W W W
M   M    I    L       I    M   M  O    O  C      L    A   A   W W W
M   M  IIIII  LLLLL IIIII  M   M   OOOO    CCCC  LLLLL A   A    W W
```

---

## Complete Sandbox Sync Checklist

When deploying changes to an existing sandbox, run through this checklist:

| # | Item | Command |
|---|------|---------|
| 1 | Upload corrected `bridge_cli.py` | `openshell sandbox upload my-assistant <local>/bridge_cli.py /sandbox/milimo-blueprint/orchestrator/bridge_cli.py` |
| 2 | Upload full blueprint to `.milimo/blueprints/0.1.0/` | `openshell sandbox upload my-assistant <local>/orchestrator/ /sandbox/.milimo/blueprints/0.1.0/orchestrator/` |
| 3 | Upload `milimo` CLI wrapper | `openshell sandbox upload my-assistant /tmp/milimo-wrapper /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py` |
| 4 | Upload `gh` CLI (correct arch) | `openshell sandbox upload my-assistant /tmp/gh /sandbox/.local/bin/gh` |
| 5 | Upload Python packages | Upload each package to `/sandbox/.local/lib/python3.11/site-packages/` |
| 6 | Create `/sandbox/.openclaw-data/milimo/claws/ops/` | Upload directory structure |
| 7 | Fix `.venv` | Upload and run `fix_venv.sh` inside sandbox |
| 8 | Verify all uploads | Download back and check line counts/checksums |
| 9 | Clear `__pycache__` after file updates | `docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- find /sandbox/.openclaw-data/milimo/blueprints/0.1.0/orchestrator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null` |
| 10 | Install `requests` package | `docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- pip install --break-system-packages requests` |
| 11 | Verify claw paths are under `.openclaw-data/milimo/claws/` | `docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- ls /sandbox/.openclaw-data/milimo/claws/` |

---

## Using openshell sandbox Commands

The `openshell` CLI is the correct tool for interacting with NemoClaw sandboxes:

```bash
# Upload a file
openshell sandbox upload my-assistant <local-path> <sandbox-path>

# Download a file
openshell sandbox download my-assistant <sandbox-path> <local-path>

# List sandboxes
openshell sandbox list

# Get sandbox details
openshell sandbox get my-assistant
```

**Important:** The upload/download commands handle the tar transfer automatically. No need for manual `docker cp` + `kubectl cp` pipelines.

---

## install.sh Now Handles All Provisioning

As of 2026-04-06, `install.sh` includes these provisioning steps that were previously missing:

| Step | What It Does |
|------|-------------|
| 6b | Initialize sandbox directories for all 6 claws |
| 6c | Copy blueprint to `/sandbox/.milimo/blueprints/0.1.0/` |
| 6d | Install Python dependencies (pyyaml, requests, stripe, httpx, sentry-sdk) |
| 6e | Install `gh` CLI with auto-detected architecture (ARM64/AMD64) |
| 6f | Create `milimo` CLI wrapper (`python3 /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py`) and add to PATH |
| 6g | Recreate `.venv` with sandbox Python |

Fresh installs will get all of these automatically. Existing sandboxes need manual sync using the commands above.

---

## Issue 7: Claws Don't Start (Missing Environment Variables / Path Migration)

### Symptoms
- `launcher_status` shows claws as "stopped"
- Build claw specifically shows "missing NVIDIA_API_KEY & GITHUB_REPO"
- Launcher logs show `No module named 'requests'` for all claws
- Launcher logs show `[Errno 13] Permission denied: '/sandbox/.openclaw-data/milimo/claws/build'` or similar
- All claws run in "stub mode" instead of full mode

### Root Cause
The sandbox's shell environment does NOT inherit from the host. The `install.sh` script deploys files but the launcher runs in a fresh process without the API keys from `.env`.

Additionally, Python packages installed via `pip3 install --target` are not in Python's default search path.

**Primary fix (as of 2026-04-28):** Claw data directories have been migrated from `/sandbox/<role>/` to `/sandbox/.openclaw-data/milimo/claws/<role>/` because NemoClaw's Landlock LSM policy marks `/sandbox/` root as read-only. See Issue 9 for full details.

Additionally, the `NEMOCLAW_MODEL` environment variable now triggers sandbox mode, which treats missing API keys as warnings rather than hard errors — so claws can start even without all keys configured.

### Fix
`install.sh` now includes three new provisioning steps (6h, 6i, 6j):

1. **Step 6h — Environment Variable Injection**
   - Reads `.env` from project root
   - Extracts relevant vars (NVIDIA_API_KEY, GITHUB_TOKEN, GITHUB_REPO, STRIPE_SECRET_KEY, VERCEL_TOKEN, SENTRY_AUTH_TOKEN)
   - Appends `export` statements to `/sandbox/.bashrc` and `/sandbox/.profile`
   - Also adds `PYTHONPATH` and `PATH` entries

2. **Step 6i — Python .pth File**
   - Creates `/usr/local/lib/python3.11/dist-packages/milimo-local.pth`
   - Contains `/sandbox/.local/lib/python3.11/site-packages`
   - Makes Python aware of packages installed via `--target`

3. **Step 6j — PID File Cleanup**
   - Removes stale `launcher.pid` from previous runs
   - Prevents "Launcher already running" crash loops

### Manual Fix (if sandbox already exists)
```bash
# Source the updated bashrc and restart the launcher
docker exec openshell-cluster-nemoclaw kubectl exec -n openshell my-assistant -- bash -c '
source /sandbox/.bashrc

# Stop old launcher
pkill -f "claw_launcher" 2>/dev/null || true
sleep 2

# Remove stale PID file
rm -f /sandbox/.milimo/mesh/launcher.pid

# Start fresh with env vars
cd /sandbox/.milimo/blueprints/0.1.0/orchestrator
nohup python3 claw_launcher.py --all --heartbeat-interval 30 --poll-interval 5 --verbose > /sandbox/.milimo/mesh/logs/launcher.log 2>&1 &
'
```

### Verification
```bash
# Check env vars are set
docker exec openshell-cluster-nemoclaw kubectl exec -n openshell my-assistant -- bash -c 'source /sandbox/.bashrc; echo $GITHUB_REPO'

# Check Python can import packages
docker exec openshell-cluster-nemoclaw kubectl exec -n openshell my-assistant -- python3 -c "import requests; print('OK')"

# Check launcher status
docker exec openshell-cluster-nemoclaw kubectl exec -n openshell my-assistant -- bash -c 'source /sandbox/.bashrc; python3 /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py --command launcher_status'
```

---

## Issue 8: gh CLI Not Found (Wrong PATH)

### Symptoms
- Build claw fails with: `gh CLI not found. Install with: brew install gh...`
- `which gh` returns nothing
- `ls /sandbox/.local/bin/gh` shows the file exists

### Root Cause
The `gh` binary is installed at `/sandbox/.local/bin/gh`, but the launcher's PATH only includes `/root/.local/bin` (which resolves to `/root/.local/bin`, not `/sandbox/.local/bin`).

### Fix
The environment variable injection (Step 6h) now includes:
```bash
export PATH=/sandbox/.local/bin:$PATH
```

This ensures all tools installed to `/sandbox/.local/bin/` are discoverable.

### Required .env Variables
For all claws to function properly, ensure your `.env` contains:

| Variable | Required By | Format |
|----------|-------------|--------|
| `NVIDIA_API_KEY` | All claws | `nvapi-xxx` |
| `GITHUB_TOKEN` | Build Claw | `ghp_xxx` |
| `GITHUB_REPO` | Build Claw | `owner/repo` (NOT full URL) |
| `STRIPE_SECRET_KEY` | Finance Claw | `sk_test_xxx` |
| `VERCEL_TOKEN` | Build Claw (optional) | `vcp_xxx` |
| `SENTRY_AUTH_TOKEN` | Build Claw (optional) | `sntryu_xxx` |

---

## Issue 9: Claws Fail with Permission Denied on /sandbox/<role>

### Symptoms
- Launcher logs show `[Errno 13] Permission denied: '/sandbox/.openclaw-data/milimo/claws/build'` or `/sandbox/.openclaw-data/milimo/claws/content`, `/sandbox/.openclaw-data/milimo/claws/ops`
- All claws show "stopped" in health endpoint
- `openclaw tui` freezes when trying to interact with claws

### Root Cause
NemoClaw's Landlock LSM policy marks `/sandbox/` root as **read-only**. Only specific subdirectories are writable:
- `/sandbox/.openclaw-data/` — writable (primary data area)
- `/sandbox/.nemoclaw/` — writable (NemoClaw state)
- `/tmp/` — writable
- `/sandbox/.openclaw/workspace/` — writable

The claw data directories (`/sandbox/.openclaw-data/milimo/claws/content/`, `/sandbox/.openclaw-data/milimo/claws/build/`, etc.) sit under `/sandbox/.openclaw-data/` which IS writable. The old paths (`/sandbox/content/`, `/sandbox/build/`, etc.) that sat directly under `/sandbox/` were NOT writable because `/sandbox/` root is read-only. When claws tried `mkdir -p` on those old paths, they got EACCES.

### Fix
All claw data directories have been migrated to `/sandbox/.openclaw-data/milimo/claws/<role>/`:

- `/sandbox/content/` → `/sandbox/.openclaw-data/milimo/claws/content/`
- `/sandbox/clients/` → `/sandbox/.openclaw-data/milimo/claws/ops/` (also renamed from "clients" to "ops")
- `/sandbox/analytics/` → `/sandbox/.openclaw-data/milimo/claws/analytics/`
- `/sandbox/finance/` → `/sandbox/.openclaw-data/milimo/claws/finance/`
- `/sandbox/build/` → `/sandbox/.openclaw-data/milimo/claws/build/`
- `/sandbox/assistant/` → `/sandbox/.openclaw-data/milimo/claws/assistant/`

The centralized `milimo_paths.py` module handles this automatically. All Python modules now use `claw_base(role)` instead of hardcoded paths.

### Manual Fix (if sandbox has old code)
```bash
# 1. Deploy updated milimo_paths.py
docker exec openshell-cluster-nemoclaw kubectl cp milimo_paths.py my-assistant:/sandbox/.openclaw-data/milimo/blueprints/0.1.0/orchestrator/milimo_paths.py -n openshell
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- chmod 644 /sandbox/.openclaw-data/milimo/blueprints/0.1.0/orchestrator/milimo_paths.py

# 2. Deploy updated claw init files (content_init.py, ops_init.py, analytics_init.py, finance_init.py, build_init.py)

# 3. Clear stale bytecode
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- find /sandbox/.openclaw-data/milimo/blueprints/0.1.0/orchestrator -type d -name __pycache__ -exec rm -rf {} +

# 4. Kill old launcher and restart
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- kill $(cat /root/.openclaw-data/milimo/mesh/launcher.pid 2>/dev/null)
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- rm -f /root/.openclaw-data/milimo/mesh/launcher.pid
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- sh -c 'cd /sandbox/.openclaw-data/milimo/blueprints/0.1.0/orchestrator && PYTHONPATH=/sandbox/.openclaw-data/milimo/blueprints/0.1.0 nohup python3 claw_launcher.py --all --daemon > /tmp/launcher.log 2>&1 &'
```

### Verification
```bash
# Check health endpoint
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- curl -s http://localhost:8081/health

# Check claw directories
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- ls /sandbox/.openclaw-data/milimo/claws/

# Check heartbeat files
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- ls /root/.openclaw-data/milimo/mesh/heartbeats/
```

---

## Issue 10: Updated Python Files Not Taking Effect (Stale Bytecode)

### Symptoms
- Deployed updated `.py` files to sandbox but claws still show old errors
- Launcher logs show errors from old code (e.g., `Permission denied: '/sandbox/.openclaw-data/milimo/claws/build'` even after path fix)
- `py_compile` on the source file succeeds but runtime behavior doesn't match

### Root Cause
Python caches compiled bytecode in `__pycache__/` directories as `.pyc` files. When you update a `.py` file, Python may still load the cached `.pyc` if the modification time check doesn't trigger recompilation (can happen with `kubectl cp` which may not update mtime correctly, or when copying as a different user).

### Fix
Clear all `__pycache__` directories in the blueprint after deploying changes:

```bash
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- \
  find /sandbox/.openclaw-data/milimo/blueprints/0.1.0/orchestrator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

Then restart the launcher.

**Important:** Always clear `__pycache__` after deploying updated Python files to the sandbox.

---

## Issue 11: Build Claw Fails with "No module named 'requests'"

### Symptoms
- Launcher log: `ClawLauncher: exception starting build: No module named 'requests'`
- All other claws run in "stub mode": `could not import X claw: No module named 'requests' (running in stub mode)`
- Build claw shows "stopped" while others show "running"

### Root Cause
The `requests` library is required by multiple claw modules (Vercel client, Sentry client, GitHub client, etc.). The sandbox Python installation does not include it by default.

### Fix
Install `requests` in the sandbox:

```bash
docker exec openshell-cluster-nemoclaw kubectl exec my-assistant -n openshell -- \
  pip install --break-system-packages requests
```

For `install.sh`, ensure Step 6d includes `requests` in the pip install command.

---

## Key Lessons Learned

1. **Two environments, not one** — The Docker container and NemoClaw sandbox are completely separate. Fixes must be applied to the sandbox where the assistant runs.
2. **No automatic sync** — Changes to host files or Docker containers do NOT propagate to the sandbox. Use `openshell sandbox upload/download` to sync.
3. **Architecture matters** — Binaries must match the sandbox's architecture (Linux ARM64), not the host's (macOS ARM64).
4. **Python venvs don't travel** — A `.venv` created on the host is useless in the sandbox. Recreate it inside the sandbox.
5. **Python packages must be uploaded** — The sandbox has no third-party packages. Install them to a target directory and upload each one.
6. **Verify by downloading back** — Always download files back from the sandbox to confirm uploads succeeded. The `openshell sandbox download` command is your verification tool.
7. **install.sh is the source of truth** — All provisioning steps should be in `install.sh` so fresh installs get everything automatically.
8. **Env vars must be explicitly injected** — The sandbox doesn't inherit host env vars. Use `install.sh` Step 6h to inject them into shell profiles.
9. **Python needs .pth files** — Packages installed to non-standard locations need a `.pth` file for discovery.
10. **PATH must include /sandbox/.local/bin** — Tools installed via `install.sh` go to `/sandbox/.local/bin/`, not `/root/.local/bin/`. The milimo CLI is now invoked as `python3 /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py`.
11. **Claw data goes to `.openclaw-data/milimo/claws/`** — `/sandbox/<role>` is read-only under Landlock. All claw data is now under `/sandbox/.openclaw-data/milimo/claws/<role>/`. Use `claw_base(role)` from `milimo_paths.py`.
12. **Always clear `__pycache__`** after deploying updated Python files — stale bytecode causes mysterious old-code behavior.
13. **`requests` is a required dependency** — all claws need it; install in sandbox with `pip install --break-system-packages requests`.
