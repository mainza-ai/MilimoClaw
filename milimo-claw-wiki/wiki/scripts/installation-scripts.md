# Installation Scripts

**Summary**: One-command installer for deploying MilimoClaw into an existing NemoClaw sandbox.

**Sources**: `install.sh`, `scripts/uninstall-nemoclaw.sh`

**Last updated**: 2026-04-15

**Tags**: #scripts #installation #deployment

---

## Overview

The MilimoClaw installer deploys the plugin and blueprint into an existing NemoClaw sandbox. NemoClaw must be installed and the sandbox running before installation.

**File**: `install.sh`

---

## Usage

```bash
cd /path/to/MilimoClaw
./install.sh --solo --operator-name "YourName" --squad-name "my-squad"
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
| `--uninstall` | Remove MilimoClaw, keep NemoClaw |
| `--sandbox-name <name>` | Target sandbox name |
| `--version, -v` | Print version and exit |
| `--help, -h` | Show help message |

---

## Installation Phases

### Phase 1: Prerequisites

Checks:
- Docker installed and running
- Node.js >= 22
- npm installed
- Python 3 installed
- NemoClaw sandbox running

### Phase 2: Build & Deploy

1. Build TypeScript plugin on host
2. Transfer plugin source to sandbox
3. Build plugin inside sandbox
4. Install plugin for sandbox user
5. Deploy blueprint to `/sandbox/milimo-blueprint`
6. Deploy assistant template
7. Initialize sandbox directories for all claws
8. Install Python dependencies
9. Install GitHub CLI (gh)
10. Create milimo CLI wrapper
11. Fix Python virtual environment
12. Inject environment variables
13. Clean stale PID files

### Phase 3: Onboarding

- Write plugin config
- Write orchestrator config
- Run assistant setup

### Phase 4: Verification

- Check plugin loaded
- Verify Build Claw modules
- Validate config

---

## Environment Variables

Injected from `.env`:

| Variable | Purpose |
|----------|---------|
| `NVIDIA_API_KEY` | Inference API |
| `GITHUB_TOKEN` | GitHub operations |
| `STRIPE_SECRET_KEY` | Payment processing |
| `VERCEL_TOKEN` | Deployments |
| `SENTRY_AUTH_TOKEN` | Error monitoring |

---

## Directory Structure After Install

```
/sandbox/
├── .milimo/
│   ├── blueprints/0.1.0/
│   ├── config.json
│   └── templates/
├── .openclaw/
│   ├── extensions/milimo/
│   └── openclaw.json
├── milimo-blueprint/
│   └── orchestrator/
├── clients/      # Ops Claw mount
├── content/      # Content Claw mount
├── analytics/    # Analytics Claw mount
├── finance/      # Finance Claw mount
└── build/        # Build Claw mount
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

- `scripts/start-services.sh` — Service startup
- `scripts/uninstall-nemoclaw.sh` — Full uninstall
