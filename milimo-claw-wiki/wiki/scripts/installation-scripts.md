# Installation Scripts

**Summary**: One-command installer for deploying MilimoClaw into a NemoClaw sandbox.

**Sources**: `install.sh`, [Install OpenClaw Plugins (official)](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html)

**Last updated**: 2026-04-29

**Tags**: #scripts #installation #deployment

---

## Overview

The MilimoClaw installer supports two installation modes:

| Mode | Flag | Mechanism | When to use |
|------|------|-----------|-------------|
| **Dockerfile** (default) | _(none)_ | `nemoclaw onboard --from <Dockerfile>` | First install; clean builds; official path |
| **Runtime deploy** | `--runtime-deploy` | `docker cp` + `kubectl cp` into running sandbox | Quick updates; testing; no rebuild |

The Dockerfile mode is the **official NemoClaw plugin installation path** per [Install OpenClaw Plugins](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html). It bakes the plugin into a custom sandbox image so it survives `nemoclaw <name> rebuild`.

The runtime deploy mode injects files into a running sandbox. Changes are **lost on rebuild** — use it only for iteration.

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

## Dockerfile Mode (Default)

This is the official path per [Install OpenClaw Plugins](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html).

### How It Works

1. Build TypeScript plugin on host (`npm ci && npm run build`)
2. Prepare a build directory with plugin source + blueprint (macOS xattrs stripped)
3. Generate a `Dockerfile` using `ARG SANDBOX_BASE=ghcr.io/nvidia/nemoclaw/sandbox-base:latest`
4. The Dockerfile copies plugin into `/sandbox/.openclaw-data/extensions/milimo/` and runs `openclaw doctor --fix`
5. Run `nemoclaw onboard --from <Dockerfile> --name <sandbox>`

### Prerequisites (Dockerfile mode)

- Docker installed and running
- Node.js >= 22.16 (per [official prerequisites](https://docs.nvidia.com/nemoclaw/latest/get-started/prerequisites.html))
- npm installed
- Python 3 installed
- NemoClaw CLI installed (`nemoclaw` on PATH)

No running sandbox is required — `nemoclaw onboard --from` creates one.

### Generated Dockerfile Pattern

```dockerfile
ARG SANDBOX_BASE=ghcr.io/nvidia/nemoclaw/sandbox-base:latest
FROM ${SANDBOX_BASE}

# Copy Milimo plugin source
COPY milimo/ /opt/milimo/
WORKDIR /opt/milimo
RUN npm ci --no-audit --no-fund && npm run build
RUN mkdir -p /sandbox/.openclaw-data/extensions \
    && cp -a /opt/milimo /sandbox/.openclaw-data/extensions/milimo \
    && openclaw doctor --fix

# Copy Milimo blueprint
COPY milimo-blueprint/ /sandbox/.openclaw-data/milimo/milimo-blueprint/

# Create claw data directories
RUN BASE="/sandbox/.openclaw-data/milimo/claws" \
    && mkdir -p "$BASE/ops/clients/active" "$BASE/ops/clients/archived" ...

# Install Python dependencies
RUN pip3 install --target /sandbox/.local/lib/python3.11/site-packages ...

# Install GitHub CLI
RUN ARCH=$(uname -m) ...

WORKDIR /opt/nemoclaw
```

This follows the official pattern from the [plugin install docs](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html): `ARG SANDBOX_BASE`, `COPY` plugin, `npm ci && npm run build`, copy to `/sandbox/.openclaw-data/extensions/`, `openclaw doctor --fix`, final `WORKDIR /opt/nemoclaw`.

### Build Context

The build context is the Dockerfile's parent directory (a temp dir under `/tmp/milimo-docker-build.*`). It contains:

```
build-dir/
├── Dockerfile
├── milimo/           # Plugin source (node_modules excluded)
└── milimo-blueprint/ # Blueprint (.__pycache__ excluded)
```

macOS xattrs are stripped via `--no-xattrs --no-mac-metadata` + `COPYFILE_DISABLE=1` to prevent `LIBARCHIVE.xattr.*` pax headers that Linux GNU tar cannot parse.

### NemoClaw Onboard Args

```bash
nemoclaw onboard --from <build-dir>/Dockerfile --name <sandbox-name>
```

Per [official docs](https://docs.nvidia.com/nemoclaw/latest/reference/commands.html), `--from` requires `--name` in non-interactive mode to avoid silently clobbering the default `my-assistant` sandbox.

---

## Runtime Deploy Mode

For quick iteration without rebuilding the sandbox image.

### How It Works

1. Build TypeScript plugin on host
2. Transfer plugin source to running sandbox via `docker cp` + `kubectl cp`
3. Build plugin inside sandbox
4. Deploy blueprint, assistant template, and support files
5. Initialize claw data directories
6. Install Python dependencies and GitHub CLI
7. Create milimo CLI wrapper and backward-compat symlinks
8. Inject environment variables
9. Register plugin via `openclaw plugins install`
10. Restart gateway

### Prerequisites (Runtime deploy)

Same as Dockerfile mode **plus**:
- NemoClaw sandbox must already be running
- Gateway container must be reachable

### Warning

Changes made via `--runtime-deploy` are **lost on `nemoclaw <name> rebuild`**. Use Dockerfile mode for persistent installations.

---

## Installation Phases (Both Modes)

### Phase 1: Prerequisites

Checks:
- Docker installed and running
- Node.js >= 22.16 (per [official prerequisites](https://docs.nvidia.com/nemoclaw/latest/get-started/prerequisites.html))
- npm installed
- Python 3 installed
- NemoClaw sandbox running (runtime deploy only — Dockerfile mode creates it)

### Phase 2: Build & Deploy

See mode-specific sections above.

### Phase 3: Onboarding

- Write plugin config to `/sandbox/.openclaw-data/milimo/config.json`
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
/sandbox/
├── .milimo/ → symlink to .openclaw-data/milimo
├── .openclaw/ → read-only (root-owned, chattr +i)
│   ├── extensions/milimo/ → built plugin source
│   ├── workspace/ → symlink into .openclaw-data/ (writable)
│   └── openclaw.json → read-only at runtime
├── .openclaw-data/ → persistent writable subtree
│   ├── extensions/milimo/ → built plugin source (mirrored)
│   └── milimo/
│       ├── blueprints/0.1.0/ → symlink to milimo-blueprint/
│       ├── bin/ → gh CLI, milimo wrapper
│       ├── config.json → plugin + orchestrator config
│       ├── claws/
│       │   ├── ops/ → Ops Claw mount (clients, projects, calendar, queue, memory, …)
│       │   ├── content/ → Content Claw mount (drafts, calendar, queue, memory, …)
│       │   ├── analytics/ → Analytics Claw mount (reports, metrics, queue, memory, …)
│       │   ├── finance/ → Finance Claw mount (invoices, expenses, revenue, queue, …)
│       │   ├── build/ → Build Claw mount (prs, deployments, tasks, docs, …)
│       │   └── assistant/ → Assistant Claw mount (context, memory, logs, tools, …)
│       ├── milimo-blueprint/ → blueprint (orchestrator, policies, templates)
│       ├── mesh/ → heartbeats, PID files
│       └── templates/ → assistant system prompt
├── milimo-blueprint/ → symlink to .openclaw-data/milimo/milimo-blueprint
└── .local/lib/python3.11/site-packages/ → pip --target packages
```

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
