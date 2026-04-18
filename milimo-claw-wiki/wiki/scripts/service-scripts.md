# Service Scripts

**Summary**: Scripts for starting, stopping, and managing NemoClaw auxiliary services including Telegram bridge and cloudflared tunnel.

**Sources**: `scripts/start-services.sh`, `scripts/milimo-start.sh`, `scripts/run-milimo-docker.sh`

**Last updated**: 2026-04-15

**Tags**: #scripts #services #operations

---

## Overview

Service scripts manage auxiliary services that run alongside the sandbox: Telegram bridge for mobile access and cloudflared tunnel for public URLs.

**Files**:
- `scripts/start-services.sh` — Start/stop services
- `scripts/milimo-start.sh` — Milimo startup wrapper
- `scripts/run-milimo-docker.sh` — Docker deployment

---

## start-services.sh

### Usage

```bash
# Start all services
TELEGRAM_BOT_TOKEN=... ./scripts/start-services.sh

# Check status
./scripts/start-services.sh --status

# Stop all services
./scripts/start-services.sh --stop

# Start for specific sandbox
./scripts/start-services.sh --sandbox mybox
```

### Options

| Option | Description |
|--------|-------------|
| `--sandbox <name>` | Target sandbox name |
| `--stop` | Stop all services |
| `--status` | Show service status |

### Services Managed

| Service | Description |
|---------|-------------|
| telegram-bridge | Telegram bot for mobile access |
| cloudflared | Public tunnel for dashboard |

### Requirements

- `NVIDIA_API_KEY` — Required for inference
- `TELEGRAM_BOT_TOKEN` — Required for Telegram bridge (optional)

### PID Files

Services store PIDs at: `/tmp/nemoclaw-services-{sandbox}/`

---

## Telegram Bridge

The Telegram bridge forwards messages between Telegram and the sandboxed OpenClaw agent.

### Setup

1. Create bot via @BotFather on Telegram
2. Set `TELEGRAM_BOT_TOKEN` environment variable
3. Run `./scripts/start-services.sh`

### Output

```
┌─────────────────────────────────────────────────────┐
│ NemoClaw Services                                   │
│                                                     │
│ Public URL: https://xxx.trycloudflare.com          │
│ Telegram: bridge running                            │
│                                                     │
│ Run 'openshell term' to monitor egress approvals   │
└─────────────────────────────────────────────────────┘
```

---

## Cloudflared Tunnel

Provides public HTTPS URL for the dashboard.

### Default Port

Dashboard runs on port 18789 (configurable via `DASHBOARD_PORT`).

### Installation

```bash
# Via Brev
./brev-setup.sh

# Manual
brew install cloudflared
```

---

## milimo-start.sh

Wrapper script for starting MilimoClaw in various configurations.

```bash
./scripts/milimo-start.sh --solo
```

---

## run-milimo-docker.sh

Docker-based deployment for containerized environments.

```bash
./scripts/run-milimo-docker.sh
```

---

## Related Pages

- [[installation-scripts]] — Installation process
- [[cli-reference]] — CLI commands
- [[mesh-coordinator]] — Mesh coordination
- [[war-room]] — Action queue

---

## See Also

- `scripts/debug.sh` — Debugging helper
- `scripts/backup-workspace.sh` — Workspace backup
