# Installation Scripts

> **CRITICAL WARNING: All claws MUST run through NemoClaw's sandbox isolation layer. The ONLY supported deployment path is `nemoclaw onboard --from` which provides full isolation (Landlock + seccomp + network namespaces + policy engine + OpenShell gateway credential injection). Any deployment that bypasses NemoClaw's isolation — including standalone `docker compose up` or manual `docker run` — is UNSUPPORTED and defeats the entire purpose of MilimoClaw as a secured multi-agent system.**

**Summary**: One-command installer for deploying MilimoClaw into a NemoClaw sandbox.

**Sources**: `install.sh`, [Install OpenClaw Plugins (official)](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html)

**Last updated**: 2026-04-30

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

# Copy Milimo plugin source
COPY milimo/ /opt/milimo/
WORKDIR /opt/milimo
RUN npm ci --no-audit --no-fund && npm run build
RUN mkdir -p /sandbox/.openclaw/extensions \
    && cp -a /opt/milimo /sandbox/.openclaw/extensions/milimo \
    && openclaw plugins install /sandbox/.openclaw/extensions/milimo \
    && openclaw doctor --fix

# Copy Milimo blueprint
COPY milimo-blueprint/ /sandbox/.openclaw/milimo/milimo-blueprint/

# Create claw data directories
RUN BASE="/sandbox/.openclaw/milimo/claws" \
    && mkdir -p "$BASE/ops/clients/active" "$BASE/ops/clients/archived" ...

# Install Python dependencies
RUN pip3 install --target /sandbox/.local/lib/python3.11/site-packages ...

# Install GitHub CLI
RUN ARCH=$(uname -m) ...

WORKDIR /opt/nemoclaw
```

This follows the official pattern from the [plugin install docs](https://docs.nvidia.com/nemoclaw/latest/deployment/install-openclaw-plugins.html): `FROM` sandbox-base, `COPY` plugin, `npm ci && npm run build`, copy to `/sandbox/.openclaw/extensions/`, `openclaw plugins install`, `openclaw doctor --fix`, final `WORKDIR /opt/nemoclaw`. All claws share a single NemoClaw sandbox created via `nemoclaw onboard --from`.

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

For quick iteration without rebuilding the sandbox image. The sandbox MUST have been created via `nemoclaw onboard --from` first — runtime deploy injects into an existing NemoClaw sandbox (still within isolation boundaries: OpenShell gateway, policy engine, Landlock rules).

### How It Works

1. Build TypeScript plugin on host
2. Transfer plugin source to running sandbox via `docker cp` + `kubectl cp`
3. Build plugin inside sandbox
4. Deploy blueprint, assistant template, and support files
5. Initialize claw data directories under `/sandbox/.openclaw/milimo/claws/`
6. Install Python dependencies and GitHub CLI
7. Create milimo CLI wrapper and backward-compat symlinks
8. Inject environment variables
9. Register plugin via `openclaw plugins install`
10. Restart gateway

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
/sandbox/
├── .openclaw/ → unified agent config/state/plugins (root-owned, immutable at runtime)
│   ├── extensions/milimo/ → built plugin source (NemoClaw sandbox-base provides this)
│   ├── workspace/ → read-only at Landlock level (symlink target is writable)
│   ├── openclaw.json → read-only at runtime
│   └── .nemoclaw/ → root-owned NemoClaw plugin state (NOT milimo data)
└── .openclaw/milimo/ → MilimoClaw data subtree (symlink or explicit mount)
    ├── blueprints/0.1.0/ → symlink to milimo-blueprint/
    ├── bin/ → gh CLI, milimo wrapper
    ├── config.json → plugin + orchestrator config
    ├── claws/
    │   ├── ops/ → Ops Claw mount (clients, projects, calendar, queue, memory, …)
    │   ├── content/ → Content Claw mount (drafts, calendar, queue, memory, …)
    │   ├── analytics/ → Analytics Claw mount (reports, metrics, queue, memory, …)
    │   ├── finance/ → Finance Claw mount (invoices, expenses, revenue, queue, …)
    │   ├── build/ → Build Claw mount (prs, deployments, tasks, docs, …)
    │   └── assistant/ → Assistant Claw mount (context, memory, logs, tools, …)
    ├── milimo-blueprint/ → blueprint (orchestrator, policies, templates)
    ├── mesh/ → heartbeats, PID files
    └── templates/ → assistant system prompt
```

> **Note:** Per official NemoClaw docs, `.openclaw/` is the unified layout. MilimoClaw data lives under `.openclaw/milimo/`. The legacy `.openclaw-data/` layout was removed by NemoClaw's Dockerfile migration block.

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
