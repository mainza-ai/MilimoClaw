# claw-launcher

**Summary**: Production-grade claw process supervisor with health monitoring, auto-restart, and daemon mode.

**Sources**: `milimo-blueprint/orchestrator/claw_launcher.py`

**Last updated**: 2026-04-14

**Tags**: #architecture #startup

---

## Purpose

Manages claw process lifecycle: startup, health monitoring, auto-restart, and graceful shutdown.

## Location

**File**: `orchestrator/claw_launcher.py`

---

## Key Components

### ClawLauncher

Main process supervisor for all claw roles.

```python
class ClawLauncher:
    def __init__(
        self,
        heartbeat_interval: int = 30,
        poll_interval: int = 5,
        check_interval: int = 60,
        unhealthy_threshold: int = 90,
    ): ...

    def start_all(self) -> None: ...
    def stop_all(self) -> None: ...
    def start_role(self, role: str) -> ClawComponents | None: ...
    def restart_role(self, role: str) -> ClawComponents | None: ...
    def status(self) -> dict: ...
```

---

## Startup Sequence

```
1. Validate environment (required env vars)
2. Create mesh directories (heartbeats, inbox, outbox)
3. Start HTTP health endpoint
4. For each claw role:
   a. Initialize claw instance
   b. Start heartbeat emitter (30s interval)
   c. Start inbox poller (5s interval)
   d. Connect external clients (Vercel, Sentry, Stripe)
5. Start heartbeat monitor (60s check)
6. Start outbox cleaner (300s interval)
```

---

## Health Monitoring

### HeartbeatEmitter

Emits heartbeat every 30 seconds:

```python
heartbeat = {
    "role": "content",
    "squad_id": "zulu",
    "timestamp": "2026-04-14T12:00:00Z",
    "pid": 12345,
    "status": "running",
    "uptime_seconds": 3600
}
```

Written to: `~/.milimo/mesh/heartbeats/{role}.json`

### HeartbeatMonitor

Checks all heartbeats every 60 seconds:
- If heartbeat > 90 seconds old → trigger auto-restart
- Uses `ProcessSupervisor` to prevent flapping

---

## Auto-Restart Behavior

### ProcessSupervisor

Tracks restarts per claw:
- Max 3 restarts per hour
- Exponential backoff (1s → 2s → 4s → ... → 60s max)
- If flapping: logs error, doesn't restart

```python
class ProcessSupervisor:
    def record_restart(self, role: str) -> bool: ...
    def is_flapping(self, role: str) -> bool: ...
```

---

## Required Environment Variables

| Role | Required Vars |
|------|--------------|
| All | `NVIDIA_API_KEY` |
| Finance | `STRIPE_SECRET_KEY` |
| Build | `GITHUB_REPO` |

### Optional Integration Vars

| Service | Variables |
|---------|-----------|
| Vercel | `VERCEL_TOKEN`, `VERCEL_TEAM_ID`, `VERCEL_PROJECT_ID` |
| Sentry | `SENTRY_AUTH_TOKEN`, `SENTRY_ORG_SLUG`, `SENTRY_PROJECT_SLUG` |
| GitHub | `GITHUB_TOKEN` or `GH_TOKEN` |

---

## HTTP Health Endpoint

Default port: 8081

### Endpoints

| Path | Description |
|------|-------------|
| `/health` | Full status of all claws |
| `/ready` | Returns `{ready: true}` if all claws running |

### Response Example

```json
{
  "running": true,
  "launcher_pid": 12345,
  "timestamp": "2026-04-14T12:00:00Z",
  "claws": {
    "content": {"status": "running", "uptime_seconds": 3600, "restarts": 0},
    "ops": {"status": "running", "uptime_seconds": 3600, "restarts": 0},
    "analytics": {"status": "running", "uptime_seconds": 3600, "restarts": 0},
    "finance": {"status": "running", "uptime_seconds": 3600, "restarts": 0},
    "build": {"status": "running", "uptime_seconds": 3600, "restarts": 0}
  }
}
```

---

## File Storage

```
~/.milimo/mesh/
├── heartbeats/{role}.json    # Claw heartbeats
├── inbox/{role}/             # Incoming messages
├── outbox/{role}/            # Processed results
├── alerts/                   # Startup/error alerts
├── logs/launcher.log         # Daemon log
└── launcher.pid              # PID file
```

---

## CLI Usage

```bash
# Start all claws
python3 claw_launcher.py --all

# Start specific claw
python3 claw_launcher.py --role build

# Run as daemon
python3 claw_launcher.py --all --daemon

# Check status
python3 claw_launcher.py --status

# Stop all
python3 claw_launcher.py --stop

# Restart specific claw
python3 claw_launcher.py --restart finance

# Validate configuration
python3 claw_launcher.py --validate-only
```

---

## Message Flow

### InboxPoller

Polls `~/.milimo/mesh/inbox/{role}/` every 5 seconds:
1. Read message JSON
2. Call `claw.handle_inbound(message)`
3. Write result to outbox
4. Archive message to `inbox/processed/`

### OutboxCleaner

Removes expired results every 5 minutes (TTL: 1 hour)

---

## Dependencies

- [[content-claw]], [[ops-claw]], [[analytics-claw]], [[finance-claw]], [[build-claw]] — Claw instances
- [[mesh-coordinator]] — Message routing
- [[privacy-router]] — Inference client

## Related Pages

- [[system-overview]] — Full architecture
- [[mesh-coordinator]] — Inter-claw messaging
- [[assistant-system]] — User interface
