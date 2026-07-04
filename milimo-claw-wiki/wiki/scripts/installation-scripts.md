# Installation Scripts

> **CRITICAL WARNING: All claws MUST run through NemoClaw's sandbox isolation layer. The ONLY supported deployment path is `nemoclaw onboard --from` which provides full isolation (Landlock + seccomp + network namespaces + policy engine + OpenShell gateway credential injection). Any deployment that bypasses NemoClaw's isolation — including standalone `docker compose up` or manual `docker run` — is UNSUPPORTED and defeats the entire purpose of MilimoClaw as a secured multi-agent system.**

**Summary**: One-command installer for deploying MilimoClaw into a NemoClaw sandbox.

**Sources**: `install.sh`, [Install OpenClaw Plugins (official)](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html)

**Last updated**: 2026-07-04

**Tags**: #scripts #installation #deployment

---

> **CRITICAL**: Claws MUST run through NemoClaw's sandbox isolation. Only `nemoclaw onboard --from` provides the full NemoClaw security stack — OpenShell gateway, policy engine, Landlock filesystem isolation, egress policy enforcement, process capability dropping, and credential injection. NEVER bypass the OpenShell gateway or policy engine by running claws outside the sandbox. Docker Compose mode is **DEPRECATED and UNSUPPORTED** — it does not provide NemoClaw isolation.

---

## Overview

The MilimoClaw installer supports a single supported installation mode and one iteration-only auxiliary mode:

| Mode | Flag | Mechanism | Status |
|------|------|-----------|--------|
| **Onboard** (default) | _(none)_ | `nemoclaw onboard --from <Dockerfile>` | **SUPPORTED** — first install; clean builds; official path |
| **Runtime deploy** | `--runtime-deploy` | `docker cp` + `kubectl cp` into running NemoClaw sandbox | **Supported** — quick updates; testing; no rebuild |
| ~~**Docker Compose**~~ | _(removed)_ | Standalone `docker compose up` | **DEPRECATED / UNSUPPORTED** — no NemoClaw isolation |

The Onboard mode is the **only supported NemoClaw installation path** per [Install OpenClaw Plugins](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html). It bakes the plugin into a custom sandbox image so it survives `nemoclaw <name> rebuild`. The sandbox is created via `nemoclaw onboard --from`, which provisions the full NemoClaw isolation stack: OpenShell gateway, policy engine, credential injection, Landlock filesystem rules, egress policies, process capability dropping, and no-new-privileges enforcement.

The runtime deploy mode injects files into an already-running NemoClaw sandbox — the claw still operates within the OpenShell gateway and policy engine isolation boundaries. Changes are **lost on rebuild** — use it only for iteration.

Docker Compose mode (standalone `docker compose up`) is **deprecated and unsupported**. It bypasses the NemoClaw isolation stack entirely — no OpenShell gateway, no policy engine, no credential injection, no Landlock enforcement. All claws MUST run through `nemoclaw onboard --from`.

**File**: `install.sh`

---

## Usage

```bash
# Dockerfile mode (default, recommended)
cd /path/to/MilimoClaw
./install.sh --solo --operator-name "YourName" --squad-name "my-squad"

# Runtime deploy mode (quick updates)
./install.sh --solo --runtime-deploy

# Non-interactive (CI/CD)
./install.sh --solo --non-interactive --sandbox-name my-squad

# Dry run (preview without executing)
./install.sh --solo --dry-run
```

---

## CLI Options

| Option | Description |
|--------|-------------|
| `--solo` | Solo mode (all 6 claws active) [default] |
| `--operator-name <name>` | Operator name (default: $USER) |
| `--squad-name <name>` | Squad name (default: milimo-squad) |
| `--warroom-mode <mode>` | War Room mode: full, minimal, disabled |
| `--non-interactive` | Skip all prompts, use defaults |
| `--auto` | Auto-install missing dependencies |
| `--dry-run` | Show what would be done |
| `--runtime-deploy` | Runtime inject into running sandbox (skip Dockerfile build) |
| `--sandbox-name <name>` | Target sandbox name (default: my-assistant) |
| `--uninstall` | Remove MilimoClaw, keep NemoClaw |
| `--version, -v` | Print version and exit |
| `--help, -h` | Show help message |

---

## Onboard Mode (Default — REQUIRED)

This is the only supported path per [Install OpenClaw Plugins](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html). Claws MUST run through `nemoclaw onboard --from` to receive the full NemoClaw isolation stack.

### How It Works

1. Build TypeScript plugin on host (`npm ci && npm run build`)
2. Prepare a build directory with plugin source + blueprint (macOS xattrs stripped)
3. Generate a `Dockerfile` using `FROM ghcr.io/nvidia/nemoclaw/sandbox-base:latest`
4. The Dockerfile copies plugin into `/sandbox/.openclaw/milimo/` and installs via `openclaw plugins install` (NemoClaw's own plugin pattern)
5. Run `nemoclaw onboard --from <Dockerfile> --name <sandbox>`

### Prerequisites (Onboard mode)

- Docker installed and running
- Node.js >= 22.16 (per [official prerequisites](https://docs.nvidia.com/nemoclaw/latest/get-started/prerequisites.html))
- npm installed
- Python 3 installed
- NemoClaw CLI installed (`nemoclaw` on PATH)

No running sandbox is required — `nemoclaw onboard --from` creates one.

### Generated Dockerfile Pattern

```dockerfile
FROM ghcr.io/nvidia/nemoclaw/sandbox-base:latest

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy Milimo plugin (pre-built dist/ + node_modules/ on host)
COPY milimo/ /opt/milimo/
WORKDIR /opt/milimo

# Install production node_modules (devDeps already stripped by --omit=dev on host)
RUN npm install --omit=dev --ignore-scripts --legacy-peer-deps 2>&1 | tail -5

# Install plugin with --force (idempotent) — FAIL BUILD if this fails
RUN openclaw plugins install --force /opt/milimo \
    && echo "PLUGIN_INSTALL_OK" \
    || (echo "PLUGIN_INSTALL_FAILED" && exit 1)

# Verify plugin is registered before continuing
RUN openclaw plugins list 2>&1 | grep -q "milimo" \
    && echo "PLUGIN_VERIFIED" \
    || (echo "PLUGIN_VERIFICATION_FAILED" && exit 1)

# Copy Milimo blueprint
COPY milimo-blueprint/ /sandbox/.openclaw/milimo/milimo-blueprint/

# Create claw data directories
RUN BASE="/sandbox/.openclaw/milimo/claws" \
    && mkdir -p "$BASE/ops/clients/active" "$BASE/ops/clients/archived" ...

# Install Python dependencies
RUN pip3 install --target /sandbox/.local/lib/python3.11/site-packages ...

# Install GitHub CLI and add to PATH via /etc/profile.d/ (survives Landlock)
RUN ARCH=$(uname -m) \
    && GH_ARCH=$([ "$ARCH" = "aarch64" ] && echo "arm64" || echo "amd64") \
    && GH_VERSION="2.67.0" \
    && GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz" \
    && cd /tmp && curl -sL "$GH_URL" -o gh.tar.gz && tar xzf gh.tar.gz \
    && mkdir -p /sandbox/.openclaw/milimo/bin \
    && cp gh_*_linux_${GH_ARCH}/bin/gh /sandbox/.openclaw/milimo/bin/gh \
    && chmod +x /sandbox/.openclaw/milimo/bin/gh \
    && rm -rf /tmp/gh* \
    && echo 'export PATH="/sandbox/.openclaw/milimo/bin:$PATH"' > /etc/profile.d/milimo.sh \
    && echo "gh CLI installed at /sandbox/.openclaw/milimo/bin/gh"

WORKDIR /opt/nemoclaw
```

Key changes from older pattern:
- **Pre-built node_modules**: `npm install --omit=dev` runs on host; Dockerfile copies them directly (no npm network access needed inside sandbox)
- **`--force` flag**: Idempotent reinstall, safe to re-run
- **Plugin verification**: `openclaw plugins list | grep -q "milimo"` after install — Docker build fails if plugin not registered
- **No `|| true`**: Plugin install errors now fail the build (catches issues early)
- **PATH via `/etc/profile.d/`**: Adds `milimo/bin` to PATH without relying on `/usr/local/bin` (may be read-only under Landlock)

### Build Context

The build context is the Dockerfile's parent directory (a temp dir under `/tmp/milimo-docker-build.*`). It contains:

```
build-dir/
├── Dockerfile
├── milimo/
│   ├── openclaw.plugin.json
│   ├── package.json
│   ├── dist/              # Pre-built TypeScript output (npx tsc on host)
│   └── node_modules/      # Production node_modules (npm install --omit=dev on host)
└── milimo-blueprint/      # Blueprint (orchestrator, policies, templates)
```

> **Note**: The Dockerfile now includes pre-built `node_modules/` (production only, `npm install --omit=dev` on host). This avoids npm network access inside the sandbox during Docker build, making builds faster and more reliable.

### NemoClaw Onboard Args

```bash
nemoclaw onboard --from <build-dir>/Dockerfile --name <sandbox-name>
```

Per [official docs](https://docs.nvidia.com/nemoclaw/latest/reference/commands.html), `--from` requires `--name` in non-interactive mode to avoid silently clobbering the default `my-assistant` sandbox.

**Required Dockerfile ARG for onboarding**: NemoClaw's setup manager patches the staged Dockerfile during onboarding to apply messaging channel plans. The Dockerfile MUST declare:
```dockerfile
ARG NEMOCLAW_MESSAGING_PLAN_B64=
ENV NEMOCLAW_MESSAGING_PLAN_B64=${NEMOCLAW_MESSAGING_PLAN_B64}
```
Without this declaration, onboarding fails with: `Error: Dockerfile is missing ARG NEMOCLAW_MESSAGING_PLAN_B64; cannot apply messaging plan.`

The `install-hermes.sh` `build_docker_image()` function now passes this through automatically (defaults to empty if no messaging plan is configured).

---

## Runtime Deploy Mode

For quick iteration without rebuilding the sandbox image. The sandbox MUST have been created via `nemoclaw onboard --from` first — runtime deploy injects into an existing NemoClaw sandbox (still within isolation boundaries: OpenShell gateway, policy engine, Landlock rules).

### How It Works

1. Build TypeScript plugin on host (`npm ci && npm run build`)
2. Build production `node_modules` on host (`npm install --omit=dev`) — avoids npm network access inside sandbox
3. Package deployable artifacts: `openclaw.plugin.json`, `package.json`, `dist/`, `node_modules/` (prod only)
4. Transfer to `/tmp/milimo-plugin-install/` inside running sandbox via `docker cp` + `kubectl cp`
5. Verify plugin staging: `test -f /tmp/milimo-plugin-install/dist/index.js`
6. Deploy blueprint to `/sandbox/.openclaw/milimo/milimo-blueprint/` (same sandbox isolation boundaries)
7. Deploy assistant template, initialize claw data directories, install Python deps and GitHub CLI
8. Register plugin via `openclaw plugins install --force /tmp/milimo-plugin-install/`
   - Retry with `--dangerously-force-unsafe-install` on failure
   - Verify: `openclaw plugins list | grep milimo` must show `loaded`
   - Verify: `openclaw milimo --help` responds
9. Restart gateway: `openclaw gateway restart` with health check loop (polls `openclaw doctor` for up to 30s)

### Prerequisites (Runtime deploy)

Same as Onboard mode **plus**:
- NemoClaw sandbox must already be running (created via `nemoclaw onboard --from`)
- Gateway container must be reachable

### Warning

Changes made via `--runtime-deploy` are **lost on `nemoclaw <name> rebuild`**. Use Onboard mode for persistent installations. Never use Docker Compose — it bypasses NemoClaw isolation entirely.

---

## Installation Phases (Both Modes)

### Phase 1: Prerequisites

Checks:
- Docker installed and running
- Node.js >= 22.16 (per [official prerequisites](https://docs.nvidia.com/nemoclaw/latest/get-started/prerequisites.html))
- npm installed
- Python 3 installed
- NemoClaw CLI installed (`nemoclaw` on PATH)
- NemoClaw sandbox running (runtime deploy only — Onboard mode creates it via `nemoclaw onboard --from`)

### Phase 2: Build & Deploy

See mode-specific sections above.

### Phase 3: Onboarding

- Write plugin config to `/sandbox/.openclaw/milimo/config.json`
- Write orchestrator config
- Run assistant setup (`assistant_setup.py`)

### Phase 4: Verification

- Check plugin loaded (`openclaw milimo --help`)
- Verify Build Claw modules present
- Validate config

---

## Environment Variables

| Variable | Purpose | Storage |
|----------|---------|---------|
| `NVIDIA_API_KEY` | Inference API | OpenShell gateway (via `nemoclaw onboard`) |
| `GITHUB_TOKEN` | GitHub operations | OpenShell gateway or `gh auth login` |
| `STRIPE_SECRET_KEY` | Payment processing | Session-only (`/etc/environment`) |
| `VERCEL_TOKEN` | Deployments | Session-only |
| `SENTRY_AUTH_TOKEN` | Error monitoring | Session-only |

Per [Credential Storage](https://docs.nvidia.com/nemoclaw/latest/security/credential-storage.html), provider credentials live in the OpenShell gateway store — not on host disk. Environment variables take precedence over gateway-stored values. Session-only env vars in `/etc/environment` do **not** survive `nemoclaw <name> rebuild`.

---

## Directory Structure After Install

```
/tmp/
└── milimo-plugin-install/     # Plugin staging dir — transferred from host, cleaned after install
    ├── openclaw.plugin.json
    ├── package.json
    ├── dist/
    └── node_modules/           # Production node_modules (npm install --omit=dev)

/sandbox/
├── .openclaw/                  # Unified agent config/state (root-owned, read-only at runtime)
│   ├── openclaw.json            # Gateway config (locked 444, not editable by sandbox user)
│   ├── extensions/             # NemoClaw-builtin plugin extensions (stock plugins)
│   ├── plugins.list             # NemoClaw plugin registry
│   ├── workspace/               # Agent workspace (read-only at Landlock level)
│   └── milimo/                  # MilimoClaw data subtree
│       ├── blueprints/0.1.0/  # Symlink → milimo-blueprint/
│       ├── bin/                 # gh CLI, milimo CLI wrapper
│       │   ├── gh              # GitHub CLI v2.67.0
│       │   └── milimo          # Python CLI wrapper → bridge_cli.py
│       ├── config.json         # Plugin config (squadName, operatorName, etc.)
│       ├── claws/              # Per-claw data directories
│       │   ├── ops/            # Ops Claw (clients, projects, calendar, queue, memory, …)
│       │   ├── content/        # Content Claw (drafts, calendar, queue, memory, …)
│       │   ├── analytics/      # Analytics Claw (reports, metrics, queue, memory, …)
│       │   ├── finance/        # Finance Claw (invoices, expenses, revenue, queue, …)
│       │   ├── build/          # Build Claw (prs, deployments, tasks, docs, …)
│       │   └── assistant/      # Assistant Claw (context, memory, logs, tools, …)
│       ├── milimo-blueprint/   # Blueprint (orchestrator, policies, templates)
│       │   └── .venv/          # Python venv (recreated with sandbox Python)
│       ├── mesh/               # Heartbeats, PIDs, alerts
│       └── templates/           # Assistant system prompt template
└── .local/lib/python3.11/site-packages/  # Python packages (directly importable)
```

**Key paths:**
- **Plugin staging**: `/tmp/milimo-plugin-install/` — transient, cleaned after `openclaw plugins install`
- **Plugin install target**: `~/.openclaw/` — `openclaw plugins install` handles placement internally
- **Blueprint**: `/sandbox/.openclaw/milimo/milimo-blueprint/` — deployed from host tarball
- **gh CLI**: `/sandbox/.openclaw/milimo/bin/gh` — PATH added via `/etc/profile.d/milimo.sh` and `/sandbox/.bashrc` (root writes PATH export to `.bashrc`)
- **Python venv**: `/sandbox/.openclaw/milimo/milimo-blueprint/.venv` — recreated with sandbox Python (previously pointed to wrong `/sandbox/milimo-blueprint/` path)

> **Note**: Per official NemoClaw docs, `.openclaw/` is the unified layout. MilimoClaw data lives under `.openclaw/milimo/`. The legacy `.openclaw-data/` layout was removed by NemoClaw's Dockerfile migration block.

---

## macOS tar xattr Handling

macOS `bsdtar` (libarchive) automatically archives extended attributes as `LIBARCHIVE.xattr.*` pax headers. Linux GNU tar inside the sandbox does not understand these headers and emits warnings. The installer strips them with:

```bash
COPYFILE_DISABLE=1 tar czf <archive> --no-xattrs --no-mac-metadata ...
```

---

## Uninstall

```bash
./install.sh --uninstall
```

Removes MilimoClaw files while preserving NemoClaw sandbox.

---

## Related Pages

- [[service-scripts]] — Service management
- [[solo-init]] — Solo template initialization
- [[claw-launcher]] — Claw startup
- [[assistant-system]] — Assistant configuration

---

## See Also

- [Install OpenClaw Plugins (official)](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html) — Official NemoClaw plugin path
- [Sandbox Hardening (official)](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html) — Image security
- `scripts/start-services.sh` — Service startup
- `scripts/uninstall-nemoclaw.sh` — Full uninstall
