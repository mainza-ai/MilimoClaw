# MilimoClaw Plugin Installation Investigation

**Date:** 2026-03-27
**Issue:** Cannot install MilimoClaw plugin into NemoClaw sandbox 'noble'

---

## Summary

The MilimoClaw plugin could not be installed because the plugin had not been built. The `milimo/dist/` directory containing compiled JavaScript did not exist.

---

## Investigation Findings

### 1. Sandbox Status

The 'noble' sandbox was properly configured and running:

```
Sandbox: noble
Model: nvidia/nemotron-3-super-120b-a12b
Provider: nvidia-nim
GPU: yes
Policies: discord, docker, huggingface, jira, npm, outlook, pypi, slack, telegram
Phase: Ready
```

The OpenClaw process was running inside the sandbox (PID 6373).

### 2. Plugin Architecture

OpenClaw uses a plugin system where:

- Plugins are TypeScript modules loaded at runtime
- Each plugin must have an `openclaw.plugin.json` manifest
- Plugins are installed via `openclaw plugins install <path>`
- The plugin's `dist/` directory must contain compiled JavaScript

### 3. Root Cause

The `milimo/` directory structure:

```
milimo/
├── src/              # TypeScript source (exists)
│   ├── index.ts
│   ├── cli.ts
│   ├── commands/
│   └── warroom/
├── dist/             # Compiled JavaScript (MISSING)
├── openclaw.plugin.json
└── package.json
```

The `package.json` specifies:
- `"main": "dist/index.js"` — entry point
- `"openclaw.extensions": ["./dist/index.js"]` — plugin extension

Without the `dist/` directory, OpenClaw cannot load the plugin.

### 4. OpenClaw Plugin Installation Requirements

From OpenClaw documentation:

```bash
# Install from npm
openclaw plugins install @openclaw/voice-call

# Install from local path (requires built plugin)
openclaw plugins install /path/to/plugin
```

For local plugins:
- Must have compiled `dist/` directory
- Must have `openclaw.plugin.json` manifest
- Must have valid `package.json` with correct entry points

---

## Solution

### Step 1: Build the Plugin

```bash
# Navigate to plugin directory
cd /path/to/MilimoClaw/milimo

# Install dependencies
npm install

# Build TypeScript to JavaScript
npm run build

# Verify build
ls -la dist/
```

Expected output:
```
dist/
├── index.js
├── index.d.ts
├── cli.js
├── cli.d.ts
├── commands/
│   └── ...
├── onboard/
│   └── ...
└── warroom/
    └── ...
```

### Step 2: Install into Sandbox

Option A — Direct installation (if sandbox has access):
```bash
# Inside sandbox
openclaw plugins install /path/to/milimo
openclaw restart
```

Option B — Docker rebuild (recommended):
```bash
# Rebuild Docker image with plugin
docker build -t milimo-claw:latest .

# Run new container
docker run -it milimo-claw:latest
```

---

## Technical Details

### NemoClaw Sandbox Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Host Machine (macOS)                                        │
│                                                             │
│  ~/.nemoclaw/                                               │
│  ├── credentials.json  # NVIDIA API credentials             │
│  └── sandboxes.json    # Sandbox configurations             │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Docker Container (openshell-cluster-nemoclaw)          │  │
│  │                                                        │  │
│  │  /sandbox/                    # Sandbox home            │  │
│  │  ├── .openclaw/               # OpenClaw config         │  │
│  │  ├── .openclaw-data/          # OpenClaw data           │  │
│  │  └── .nemoclaw/               # NemoClaw config         │  │
│  │                                                        │  │
│  │  /usr/local/lib/node_modules/openclaw/                 │  │
│  │  ├── extensions/             # Bundled plugins          │  │
│  │  ├── dist/                   # Core OpenClaw            │  │
│  │  └── openclaw.mjs            # Entry point              │  │
│  │                                                        │  │
│  │  Processes:                                           │  │
│  │  - openclaw (PID 6373)       # Main OpenClaw process    │  │
│  │  - openclaw-gateway (PID 6392) # Gateway server         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### OpenClaw Plugin Discovery

OpenClaw discovers plugins from:
1. Bundled extensions: `/usr/local/lib/node_modules/openclaw/extensions/`
2. User extensions: `~/.openclaw/extensions/`
3. Configured plugin paths in `openclaw.json`

The `openclaw plugins install` command:
1. Validates the plugin manifest
2. Copies plugin files to `~/.openclaw/extensions/<id>/`
3. Installs npm dependencies (if needed)
4. Requires gateway restart to load new plugins

### Why `npm run build -w milimo` Failed

The MilimoClaw project doesn't use npm workspaces. The root `package.json` doesn't define workspaces, so the `-w` flag doesn't work.

Correct approach:
```bash
# Wrong
npm run build -w milimo

# Correct
cd milimo && npm run build
```

---

## Recommendations

1. **Add pre-commit hook** to verify plugin is built before commits
2. **Add CI check** to ensure `dist/` directory exists for releases
3. **Update documentation** to emphasize building step
4. **Consider adding** a `prepublishOnly` script in package.json

---

## Simplified Installation Procedure

For future installations into NemoClaw sandboxes:

### Method 1: Direct Plugin Install (Recommended)

```bash
# 1. Build the plugin
cd /path/to/MilimoClaw/milimo
npm install && npm run build

# 2. Copy to container
docker cp ./milimo openshell-cluster-nemoclaw:/tmp/milimo

# 3. Copy to sandbox data directory
docker exec openshell-cluster-nemoclaw bash -c \
  'cp -r /tmp/milimo/* /var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/90/fs/sandbox/.openclaw-data/extensions/milimo/'

# 4. Install inside sandbox namespace
docker exec openshell-cluster-nemoclaw nsenter -t 6373 -a -- \
  openclaw plugins install /sandbox/.openclaw-data/extensions/milimo
```

### Method 2: Docker Image Rebuild

For a more permanent solution, rebuild the Docker image with the plugin pre-installed:

```dockerfile
# In Dockerfile
COPY milimo/dist/ /opt/milimo/
COPY milimo/openclaw.plugin.json /opt/milimo/
RUN openclaw plugins install /opt/milimo
```

---

## Resolution (2026-03-27)

### Steps Completed

1. **Built the plugin:**
   ```bash
   cd /Users/mck/Desktop/MilimoClaw/milimo
   npm install
   npm run build
   ```

2. **Copied plugin to container:**
   ```bash
   docker cp /Users/mck/Desktop/MilimoClaw/milimo openshell-cluster-nemoclaw:/tmp/milimo
   ```

3. **Installed plugin inside sandbox:**
   ```bash
   # Enter sandbox namespace
   docker exec openshell-cluster-nemoclaw nsenter -t 6373 -a -- bash

   # Create extension directory
   mkdir -p /sandbox/.openclaw-data/extensions/milimo

   # Copy plugin files (from host container perspective)
   # Files copied to: /var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/90/fs/sandbox/.openclaw-data/extensions/milimo/

   # Install plugin
   openclaw plugins install /sandbox/.openclaw-data/extensions/milimo
   ```

### Plugin Successfully Installed

```
┌─────────────────────────────────────────────────────────────┐
│ Milimo Claw registered                                      │
│                                                             │
│ Squad: not configured                                       │
│ Role: not assigned                                          │
│ Template: not selected                                      │
│ Commands: openclaw milimo <command>                        │
│ Chat: /milimo <command>                                    │
└─────────────────────────────────────────────────────────────┘

Plugins (5/39 loaded)
Source roots:
  stock: /usr/local/lib/node_modules/openclaw/extensions
  global: /root/.openclaw/extensions

│ Milimo Claw │ milimo │ loaded │ global:milimo/dist/index.js │ 0.1.0 │
```

### Available Commands

```
openclaw milimo [options] [command]

Commands:
  blueprint   Blueprint operations
  init        Initialize a new squad or join an existing mesh
  onboard     Interactive setup: configure squad, template, role, and War Room
  squad       Squad lifecycle management
  warroom     Launch the War Room interactive operator dashboard
```

### Next Steps

To complete setup, run:
```bash
openclaw milimo onboard
```

---

## References

- [OpenClaw Plugin Documentation](https://docs.openclaw.ai/plugins/)
- [NemoClaw Architecture](../reference/architecture.md)
- [Quick Start Guide](../guides/QUICK_START_MACOS.md)
