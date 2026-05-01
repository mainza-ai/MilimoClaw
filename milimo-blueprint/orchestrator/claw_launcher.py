# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Claw Launcher

Production-grade claw process supervisor with:
- Filesystem initialization
- Dependency injection (GitHub client, inference client, etc.)
- Message inbox polling loop
- Heartbeat emission on a timer
- Auto-restart of crashed/stale claws
- Daemon mode with PID file management
- Crash recovery with exponential backoff
- Real client integrations (Vercel, Sentry, Mesh)
- Startup validation and health checks
- HTTP health endpoint

Usage:
    python3 claw_launcher.py --all --daemon       # Start all claws in background
    python3 claw_launcher.py --role build         # Start build claw in foreground
    python3 claw_launcher.py --stop               # Stop running launcher
    python3 claw_launcher.py --status             # Check launcher status
    python3 claw_launcher.py --restart build      # Restart a specific claw
    python3 claw_launcher.py --validate-only      # Validate config and exit
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable

from milimo_paths import MILIMO_DIR, claw_base

logger = logging.getLogger("milimo.claw_launcher")

BLUEPRINT_PATH = MILIMO_DIR / "blueprints" / "0.1.0"
if BLUEPRINT_PATH.exists() and str(BLUEPRINT_PATH) not in sys.path:
    sys.path.insert(0, str(BLUEPRINT_PATH))

ALL_ROLES = ["content", "ops", "analytics", "finance", "build", "assistant"]
SQUAD_ID = os.environ.get("SQUAD_ID", "zulu")
MESH_DIR = MILIMO_DIR / "mesh"
HEARTBEAT_DIR = MESH_DIR / "heartbeats"
INBOX_DIR = MESH_DIR / "inbox"
OUTBOX_DIR = MESH_DIR / "outbox"
ALERTS_DIR = MESH_DIR / "alerts"
LAUNCHER_PID_FILE = MESH_DIR / "launcher.pid"
LAUNCHER_LOG_FILE = MESH_DIR / "logs" / "launcher.log"


class RealMeshGateway:
    """MeshGateway implementation using MeshCoordinator.

    Canonical 6-arg send interface matching FinanceClaw's MeshGateway Protocol.
    Shared across all claws — instantiated once in ClawLauncher.
    """

    def __init__(self) -> None:
        from orchestrator.mesh import MeshCoordinator

        mesh_dir = str(MESH_DIR)
        config_path = BLUEPRINT_PATH / "mesh_config.yaml"
        if config_path.exists():
            self._mesh = MeshCoordinator.from_config_file(
                str(config_path), squad_id=SQUAD_ID, mesh_dir=mesh_dir
            )
        else:
            self._mesh = MeshCoordinator.from_dict(
                {}, squad_id=SQUAD_ID, mesh_dir=mesh_dir
            )
        for claw_role in ALL_ROLES:
            self._mesh.register_claw(claw_role, address=f"local://{claw_role}")

    def send(
        self,
        message_type: str,
        recipient_role: str,
        sender_role: str,
        payload: dict,
        message_id: str,
        timestamp: str,
    ) -> bool:
        from orchestrator.contracts import ClawMessage

        msg = ClawMessage(
            sender_role=sender_role,
            recipient_role=recipient_role,
            message_type=message_type,
            payload=payload,
            squad_id=SQUAD_ID,
        )
        result = self._mesh.send_message(msg)
        if not result.delivered:
            logger.warning("RealMeshGateway: send failed: %s", result.reason)
        return result.delivered


class DictMeshGatewayAdapter:
    """Adapts RealMeshGateway to the 1-dict-arg send(message: dict) -> bool interface.

    Used by OpsClaw and BuildClaw's signal dispatchers which call
    gateway.send(message_dict) with a single dict argument.
    """

    def __init__(self, gateway: RealMeshGateway, sender_role: str) -> None:
        self._gateway = gateway
        self._sender_role = sender_role

    def send(self, message: dict[str, Any]) -> bool:
        return self._gateway.send(
            message_type=message.get("message_type", "unknown"),
            recipient_role=message.get("recipient_role", "unknown"),
            sender_role=message.get("sender_role", self._sender_role),
            payload=message.get("payload", {}),
            message_id=message.get("message_id", ""),
            timestamp=message.get("timestamp", ""),
        )


class CallableMeshSenderAdapter:
    """Adapts RealMeshGateway to the Callable[[dict], None] interface.

    Used by ContentClaw and AnalyticsClaw which accept
    mesh_sender: Callable[[dict], None].
    """

    def __init__(self, gateway: RealMeshGateway, sender_role: str) -> None:
        self._gateway = gateway
        self._sender_role = sender_role

    def __call__(self, message: dict[str, Any]) -> None:
        self._gateway.send(
            message_type=message.get("message_type", "unknown"),
            recipient_role=message.get("recipient_role", "unknown"),
            sender_role=message.get("sender_role", self._sender_role),
            payload=message.get("payload", {}),
            message_id=message.get("message_id", ""),
            timestamp=message.get("timestamp", ""),
        )


MAX_RESTART_THRESHOLD = 3
RESTART_WINDOW_SECONDS = 3600
UNHEALTHY_THRESHOLD = 90
RESTART_BACKOFF_MAX = 60
RESULT_TTL_SECONDS = 3600

# Health ports per claw (unique to avoid conflicts)
HEALTH_PORTS = {
    "content": 8081,
    "ops": 8082,
    "analytics": 8083,
    "finance": 8084,
    "build": 8085,
    "assistant": 8086,
}
DEFAULT_HEALTH_PORT = 8081

# Required environment variables for each claw
REQUIRED_ENV_VARS = {
    "content": ["NVIDIA_API_KEY"],
    "ops": ["NVIDIA_API_KEY"],
    "analytics": ["NVIDIA_API_KEY"],
    "finance": ["NVIDIA_API_KEY", "STRIPE_SECRET_KEY"],
    "build": ["NVIDIA_API_KEY", "GITHUB_REPO"],
    "assistant": ["NVIDIA_API_KEY"],
}

# Optional environment variables for enhanced functionality
OPTIONAL_ENV_VARS = {
    "vercel": ["VERCEL_TOKEN", "VERCEL_TEAM_ID", "VERCEL_PROJECT_ID"],
    "sentry": ["SENTRY_AUTH_TOKEN", "SENTRY_ORG_SLUG", "SENTRY_PROJECT_SLUG"],
    "github": ["GITHUB_TOKEN", "GH_TOKEN"],
}


# ---------------------------------------------------------------------------
# Validation Functions
# ---------------------------------------------------------------------------


def validate_environment(role: str | None = None) -> dict[str, Any]:
    """Validate required environment variables.

    Args:
        role: Specific role to validate, or None for all roles

    Returns:
        Dict with validation results including missing vars and warnings
    """
    results = {
        "valid": True,
        "missing_required": [],
        "missing_optional": [],
        "warnings": [],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    roles_to_check = [role] if role else ALL_ROLES

    for r in roles_to_check:
        required = REQUIRED_ENV_VARS.get(r, [])
        for var in required:
            if not os.environ.get(var):
                results["missing_required"].append({"role": r, "var": var})
                results["valid"] = False

    for category, vars_list in OPTIONAL_ENV_VARS.items():
        for var in vars_list:
            if not os.environ.get(var):
                results["missing_optional"].append({"category": category, "var": var})

    if not os.environ.get("NVIDIA_API_KEY") and not os.environ.get(
        "BUILD_CLAW_NVIDIA_API_KEY"
    ):
        sandbox_mode = bool(os.environ.get("NEMOCLAW_MODEL"))
        if sandbox_mode:
            results["warnings"].append(
                "NVIDIA_API_KEY not set — using sandbox proxy (inference routed through gateway)"
            )
        else:
            results["warnings"].append("No NVIDIA API key - inference will fail")

    return results


def validate_clients() -> dict[str, Any]:
    """Validate external client connections.

    Returns:
        Dict with client health check results
    """
    results = {
        "vercel": {"available": False, "healthy": False, "error": None},
        "sentry": {"available": False, "healthy": False, "error": None},
        "github": {"available": False, "healthy": False, "error": None},
    }

    vercel_token = os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN")
    if vercel_token:
        results["vercel"]["available"] = True
        try:
            from orchestrator.build.vercel_client import VercelClient

            client = VercelClient(api_token=vercel_token)
            results["vercel"]["healthy"] = client.health_check()
        except Exception as e:
            results["vercel"]["error"] = str(e)

    sentry_token = os.environ.get("SENTRY_AUTH_TOKEN")
    if sentry_token:
        results["sentry"]["available"] = True
        try:
            from orchestrator.build.sentry_client import SentryClient

            client = SentryClient(auth_token=sentry_token)
            results["sentry"]["healthy"] = client.health_check()
        except Exception as e:
            results["sentry"]["error"] = str(e)

    github_repo = os.environ.get("GITHUB_REPO")
    if github_repo:
        results["github"]["available"] = True
        try:
            import subprocess

            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            results["github"]["healthy"] = result.returncode == 0
            if result.returncode != 0:
                results["github"]["error"] = result.stderr.strip()
        except Exception as e:
            results["github"]["error"] = str(e)

    return results


def write_alert(alert_type: str, message: str, details: dict | None = None) -> None:
    """Write an alert to the alerts directory.

    Args:
        alert_type: Type of alert (e.g., "env_missing", "client_unhealthy")
        message: Human-readable alert message
        details: Additional details to include
    """
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)

    alert_id = f"{alert_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    alert_file = ALERTS_DIR / f"{alert_id}.json"

    alert = {
        "alert_id": alert_id,
        "alert_type": alert_type,
        "message": message,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    alert_file.write_text(json.dumps(alert, indent=2))
    logger.warning("Alert written: %s - %s", alert_type, message)


def print_startup_summary(launcher: "ClawLauncher") -> None:
    """Print a startup summary to stdout."""
    status = launcher.status()

    print("\n" + "=" * 60)
    print("  MILIMO CLAW LAUNCHER - STARTUP SUMMARY")
    print("=" * 60)
    print(f"\n  Launcher PID: {os.getpid()}")
    print(f"  Squad ID: {SQUAD_ID}")
    print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
    print("\n  Claws Status:")
    print("-" * 60)

    for role, claw_status in status.get("claws", {}).items():
        icon = "✓" if claw_status.get("status") == "running" else "✗"
        uptime = claw_status.get("uptime_seconds", 0)
        restarts = claw_status.get("restarts", 0)
        print(
            f"    [{icon}] {role:12} - {claw_status.get('status', 'unknown'):8} (uptime: {uptime:.0f}s, restarts: {restarts})"
        )

    print("-" * 60)
    print(f"\n Health Endpoint: http://localhost:{DEFAULT_HEALTH_PORT}/health")
    print(f" Log File: {LAUNCHER_LOG_FILE}")
    print(f" PID File: {LAUNCHER_PID_FILE}")
    print("\n" + "=" * 60 + "\n")


# ---------------------------------------------------------------------------
# HTTP Health Endpoint
# ---------------------------------------------------------------------------


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""

    launcher: "ClawLauncher | None" = None

    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            if self.launcher:
                status = self.launcher.status()
                status["health_endpoint"] = "ok"
                status["timestamp"] = datetime.now(timezone.utc).isoformat()
            else:
                status = {"error": "launcher not initialized"}

            self.wfile.write(json.dumps(status, indent=2).encode())
        elif self.path == "/ready":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            ready = True
            reasons = []

            if self.launcher:
                for role, claw_status in (
                    self.launcher.status().get("claws", {}).items()
                ):
                    if claw_status.get("status") != "running":
                        ready = False
                        reasons.append(f"{role} not running")

            response = {
                "ready": ready,
                "reasons": reasons,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server(
    launcher: "ClawLauncher", port: int = DEFAULT_HEALTH_PORT
) -> threading.Thread:
    """Start the HTTP health endpoint in a background thread."""

    def run_server():
        HealthHandler.launcher = launcher
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info("Health endpoint started on port %d", port)
        server.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


def write_outbox(
    message_id: str,
    role: str,
    original_message: dict,
    result: Any,
) -> None:
    """
    Write a result to the outbox directory.
    Creates a JSON file at OUTBOX_DIR/{role}/{message_id}.json containing
    the original message and the handler result, along with timestamps.
    """
    outbox_dir = OUTBOX_DIR / role
    outbox_dir.mkdir(parents=True, exist_ok=True)

    outbox_entry = {
        "message_id": message_id,
        "role": role,
        "squad_id": SQUAD_ID,
        "original_message": original_message,
        "result": result,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.fromtimestamp(
            time.time() + RESULT_TTL_SECONDS, tz=timezone.utc
        ).isoformat(),
    }

    outbox_file = outbox_dir / f"{message_id}.json"
    outbox_file.write_text(json.dumps(outbox_entry, indent=2))
    logger.debug("write_outbox: wrote result for %s to %s", message_id, outbox_file)


class ProcessSupervisor:
    """Tracks claw restarts and enforces the max-restart threshold."""

    def __init__(
        self,
        max_restarts: int = MAX_RESTART_THRESHOLD,
        window_seconds: int = RESTART_WINDOW_SECONDS,
    ):
        self.max_restarts = max_restarts
        self.window_seconds = window_seconds
        self._restarts: dict[str, list[float]] = defaultdict(list)

    def record_restart(self, role: str) -> bool:
        """Record a restart attempt. Returns True if restart is allowed."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._restarts[role] = [t for t in self._restarts[role] if t > cutoff]
        self._restarts[role].append(now)
        return len(self._restarts[role]) <= self.max_restarts

    def restart_count(self, role: str) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        return len([t for t in self._restarts.get(role, []) if t > cutoff])

    def is_flapping(self, role: str) -> bool:
        return self.restart_count(role) > self.max_restarts

    def clear(self, role: str) -> None:
        self._restarts[role] = []


class HeartbeatEmitter:
    """Emits periodic heartbeats for a claw process."""

    def __init__(self, role: str, interval: int = 30):
        self.role = role
        self.interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._start_time = time.time()

    @property
    def is_alive(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._emit_loop, daemon=True)
        self._thread.start()
        logger.info(
            "HeartbeatEmitter: started for %s (interval=%ds)", self.role, self.interval
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._clear_heartbeat()
        logger.info("HeartbeatEmitter: stopped for %s", self.role)

    def _clear_heartbeat(self) -> None:
        hb_file = HEARTBEAT_DIR / f"{self.role}.json"
        if hb_file.exists():
            try:
                hb_file.unlink()
            except OSError:
                pass

    def _emit_loop(self) -> None:
        while self._running:
            try:
                self._emit()
            except Exception as e:
                logger.error("HeartbeatEmitter: emit failed for %s: %s", self.role, e)
            time.sleep(self.interval)

    def _emit(self) -> None:
        heartbeat = {
            "role": self.role,
            "squad_id": SQUAD_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "status": "running",
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }
        hb_file = HEARTBEAT_DIR / f"{self.role}.json"
        hb_file.write_text(json.dumps(heartbeat, indent=2))


class InboxPoller:
    """Polls a claw's inbox for new messages, processes them, and writes results to the outbox."""

    def __init__(
        self,
        role: str,
        interval: int = 5,
        message_handler: Callable[[dict], Any] | None = None,
        outbox_writer: Callable[[str, str, dict, Any], None] | None = None,
    ):
        self.role = role
        self.interval = interval
        self.inbox = INBOX_DIR / role
        self.outbox = OUTBOX_DIR / role
        self._running = False
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._message_handler = message_handler
        self._outbox_writer = outbox_writer

    @property
    def is_alive(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(
            "InboxPoller: started for %s (interval=%ds)", self.role, self.interval
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("InboxPoller: stopped for %s", self.role)

    def _poll_loop(self) -> None:
        while self._running:
            try:
                self._check_inbox()
            except Exception as e:
                logger.error("InboxPoller: poll failed for %s: %s", self.role, e)
            time.sleep(self.interval)

    def _check_inbox(self) -> None:
        if not self.inbox.exists():
            return

        for msg_file in sorted(self.inbox.glob("*.json")):
            msg_id = msg_file.stem
            if msg_id in self._processed:
                continue

            try:
                content = json.loads(msg_file.read_text())
                logger.info(
                    "InboxPoller: processing message %s for %s: %s",
                    msg_id,
                    self.role,
                    content.get("message_type"),
                )

                result: Any = None
                if self._message_handler:
                    try:
                        result = self._message_handler(content)
                    except Exception as e:
                        logger.error("InboxPoller: handler error for %s: %s", msg_id, e)
                        result = {"error": str(e)}

                self._processed.add(msg_id)

                if self._outbox_writer:
                    try:
                        self._outbox_writer(msg_id, self.role, content, result)
                    except Exception as e:
                        logger.error(
                            "InboxPoller: outbox write failed for %s: %s", msg_id, e
                        )

                archive_dir = self.inbox / "processed"
                archive_dir.mkdir(exist_ok=True)
                msg_file.rename(archive_dir / msg_file.name)

            except Exception as e:
                logger.error("InboxPoller: failed to process message %s: %s", msg_id, e)


class HeartbeatMonitor:
    """Monitors claw heartbeats and triggers auto-restart when stale."""

    def __init__(
        self,
        heartbeat_dir: Path,
        check_interval: int = 60,
        unhealthy_threshold: int = UNHEALTHY_THRESHOLD,
    ) -> None:
        self.heartbeat_dir = heartbeat_dir
        self.check_interval = check_interval
        self.unhealthy_threshold = unhealthy_threshold
        self._running = False
        self._thread: threading.Thread | None = None
        self._restart_callback: Callable[[str], None] | None = None
        self._active_roles: list[str] = []

    def set_restart_callback(self, callback: Callable[[str], None]) -> None:
        self._restart_callback = callback

    def set_active_roles(self, roles: list[str]) -> None:
        self._active_roles = list(roles)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(
            "HeartbeatMonitor: started (interval=%ds, threshold=%ds)",
            self.check_interval,
            self.unhealthy_threshold,
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("HeartbeatMonitor: stopped")

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                self._check_heartbeats()
            except Exception as e:
                logger.error("HeartbeatMonitor: error: %s", e)
            time.sleep(self.check_interval)

    def _check_heartbeats(self) -> None:
        if not self.heartbeat_dir.exists():
            return

        _now = time.time()
        for hb_file in sorted(self.heartbeat_dir.glob("*.json")):
            role = hb_file.stem
            if role not in self._active_roles:
                continue

            try:
                hb = json.loads(hb_file.read_text())
                timestamp = hb.get("timestamp", "")
                if not timestamp:
                    continue

                hb_time = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - hb_time).total_seconds()

                if age_seconds > self.unhealthy_threshold:
                    logger.warning(
                        "HeartbeatMonitor: claw '%s' stale (%.0fs old, threshold=%ds)",
                        role,
                        age_seconds,
                        self.unhealthy_threshold,
                    )
                    if self._restart_callback:
                        self._restart_callback(role)
                else:
                    logger.debug(
                        "HeartbeatMonitor: claw '%s' healthy (%.0fs old)",
                        role,
                        age_seconds,
                    )

            except Exception as e:
                logger.warning("HeartbeatMonitor: failed to read %s: %s", hb_file, e)


class OutboxCleaner:
    """Periodically removes expired result files from the outbox."""

    def __init__(
        self,
        check_interval: int = 300,
        ttl_seconds: int = RESULT_TTL_SECONDS,
    ):
        self.check_interval = check_interval
        self.ttl_seconds = ttl_seconds
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._clean_loop, daemon=True)
        self._thread.start()
        logger.info(
            "OutboxCleaner: started (interval=%ds, ttl=%ds)",
            self.check_interval,
            self.ttl_seconds,
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("OutboxCleaner: stopped")

    def _clean_loop(self) -> None:
        while self._running:
            try:
                self._clean_expired()
            except Exception as e:
                logger.error("OutboxCleaner: error: %s", e)
            time.sleep(self.check_interval)

    def _clean_expired(self) -> None:
        if not OUTBOX_DIR.exists():
            return

        now = datetime.now(timezone.utc)
        cleaned = 0

        for role_dir in OUTBOX_DIR.iterdir():
            if not role_dir.is_dir():
                continue

            for result_file in role_dir.glob("*.json"):
                try:
                    data = json.loads(result_file.read_text())
                    expires_at = data.get("expires_at")
                    if not expires_at:
                        continue

                    expiry_dt = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )
                    if now > expiry_dt:
                        result_file.unlink()
                        cleaned += 1
                        logger.debug(
                            "OutboxCleaner: removed expired result %s", result_file
                        )
                except (json.JSONDecodeError, OSError, ValueError):
                    pass

        if cleaned > 0:
            logger.info("OutboxCleaner: cleaned %d expired results", cleaned)


class ClawComponents:
    """Bundles all components for a single running claw."""

    def __init__(
        self, role: str, claw: Any, heartbeat: HeartbeatEmitter, poller: InboxPoller
    ):
        self.role = role
        self.claw = claw
        self.heartbeat = heartbeat
        self.poller = poller
        self._alive = True

    def is_alive(self) -> bool:
        return (
            self.claw is not None
            and self._alive
            and self.heartbeat.is_alive
            and self.poller.is_alive
        )

    def stop(self) -> None:
        self._alive = False
        self.poller.stop()
        self.heartbeat.stop()
        if self.claw and hasattr(self.claw, "shutdown"):
            try:
                self.claw.shutdown()
            except Exception as e:
                logger.error("ClawComponents: error shutting down %s: %s", self.role, e)

    def restart(self) -> None:
        self.stop()


class ClawLauncher:
    """Production claw process supervisor."""

    def __init__(
        self,
        heartbeat_interval: int = 30,
        poll_interval: int = 5,
        check_interval: int = 60,
        unhealthy_threshold: int = UNHEALTHY_THRESHOLD,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.poll_interval = poll_interval
        self.check_interval = check_interval
        self.unhealthy_threshold = unhealthy_threshold

        self._components: dict[str, ClawComponents] = {}
        self._supervisor = ProcessSupervisor()
        self._backoff: dict[str, float] = defaultdict(lambda: 1.0)
        self._running = False
        self._lock = threading.Lock()
        self._monitor = HeartbeatMonitor(
            heartbeat_dir=HEARTBEAT_DIR,
            check_interval=check_interval,
            unhealthy_threshold=unhealthy_threshold,
        )
        self._outbox_cleaner = OutboxCleaner()

        MESH_DIR.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

        self._mesh_gateway = RealMeshGateway()
        logger.info("ClawLauncher: shared RealMeshGateway initialized")

    def start_role(self, role: str) -> ClawComponents | None:
        """Start a single claw role."""
        self._running = True
        with self._lock:
            if role in self._components and self._components[role].is_alive():
                logger.warning("ClawLauncher: %s already running", role)
                return self._components[role]

            logger.info("ClawLauncher: starting %s", role)
            try:
                if role == "build":
                    claw, heartbeat, poller = self._start_build_claw()
                else:
                    claw, heartbeat, poller = self._start_generic_claw(role)

                if claw is not None and heartbeat is not None:
                    components = ClawComponents(role, claw, heartbeat, poller)
                    self._components[role] = components
                    self._supervisor.clear(role)
                    self._backoff[role] = 1.0
                    logger.info("ClawLauncher: %s started successfully", role)
                    return components
                else:
                    logger.error("ClawLauncher: failed to start %s", role)
                    return None
            except Exception as e:
                logger.error("ClawLauncher: exception starting %s: %s", role, e)
                return None

    def stop_role(self, role: str) -> None:
        """Stop a single claw role."""
        with self._lock:
            if role not in self._components:
                logger.warning("ClawLauncher: %s not running", role)
                return
            logger.info("ClawLauncher: stopping %s", role)
            self._components[role].stop()
            del self._components[role]

    def restart_role(self, role: str) -> ClawComponents | None:
        """Stop then start a claw role."""
        logger.info("ClawLauncher: restarting %s", role)
        self.stop_role(role)
        time.sleep(2)
        return self.start_role(role)

    def _monitor_restart_callback(self, role: str) -> None:
        """Wraps restart_stale_claw for use as a monitor callback."""
        self.restart_stale_claw(role)

    def restart_stale_claw(self, role: str) -> None:
        """Called by HeartbeatMonitor when a claw's heartbeat goes stale."""
        if role not in self._components:
            return

        if self._supervisor.is_flapping(role):
            logger.error(
                "ClawLauncher: %s is flapping (%d restarts in %ds). Not restarting automatically.",
                role,
                self._supervisor.restart_count(role),
                RESTART_WINDOW_SECONDS,
            )
            return

        if not self._supervisor.record_restart(role):
            logger.error(
                "ClawLauncher: %s exceeded restart threshold (%d in %ds)",
                role,
                self._supervisor.restart_count(role),
                RESTART_WINDOW_SECONDS,
            )
            return

        backoff = self._backoff[role]
        logger.warning(
            "ClawLauncher: restarting stale claw %s (backoff=%.1fs)",
            role,
            backoff,
        )

        def delayed_restart():
            time.sleep(backoff)
            self.restart_role(role)

        self._backoff[role] = min(backoff * 2, RESTART_BACKOFF_MAX)
        threading.Thread(target=delayed_restart, daemon=True).start()

    def start_all(self) -> None:
        """Start all 6 claw roles."""
        self._running = True
        self._monitor.set_active_roles(ALL_ROLES)
        self._monitor.set_restart_callback(self._monitor_restart_callback)
        self._monitor.start()
        self._outbox_cleaner.start()

        for role in ALL_ROLES:
            self.start_role(role)

    def stop_all(self) -> None:
        """Stop all running claws."""
        self._running = False
        self._monitor.stop()
        self._outbox_cleaner.stop()
        with self._lock:
            for role in list(self._components.keys()):
                self._components[role].stop()
            self._components.clear()

    def status(self) -> dict:
        """Return status of all claws."""
        status = {
            "running": self._running,
            "launcher_pid": os.getpid(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "claws": {},
        }
        for role in ALL_ROLES:
            components = self._components.get(role)
            hb_file = HEARTBEAT_DIR / f"{role}.json"
            if components and components.is_alive():
                status["claws"][role] = {
                    "status": "running",
                    "uptime_seconds": getattr(components.heartbeat, "_start_time", 0),
                    "restarts": self._supervisor.restart_count(role),
                    "flapping": self._supervisor.is_flapping(role),
                }
            elif hb_file.exists():
                try:
                    hb = json.loads(hb_file.read_text())
                    age = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(hb.get("timestamp", "")).replace(
                            tzinfo=timezone.utc
                        )
                    ).total_seconds()
                    status["claws"][role] = {
                        "status": "stale",
                        "age_seconds": round(age, 1),
                        "restarts": self._supervisor.restart_count(role),
                    }
                except Exception:
                    status["claws"][role] = {"status": "unknown"}
            else:
                status["claws"][role] = {
                    "status": "stopped",
                    "restarts": self._supervisor.restart_count(role),
                }
        return status

    def _start_build_claw(self) -> tuple:
        """Start the Build claw with real clients when available."""
        from orchestrator.build.build_claw import BuildClaw
        from orchestrator.build.build_init import BASE
        from orchestrator.inference_client import NvidiaInferenceClient
        from orchestrator.github_client import GitHubClient

        inference_client = NvidiaInferenceClient(
            api_key=os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("BUILD_CLAW_NVIDIA_API_KEY"),
            api_base=os.environ.get("NVIDIA_API_BASE"),
        )

        try:
            github_client = GitHubClient(repo=os.environ.get("GITHUB_REPO"))
        except RuntimeError as exc:
            logger.warning(
                "ClawLauncher: GitHubClient unavailable (%s) — build running without GitHub",
                exc,
            )
            github_client = None

        # Initialize real Vercel client if token available
        vercel_client = None
        vercel_token = os.environ.get("VERCEL_TOKEN") or os.environ.get(
            "VERCEL_API_TOKEN"
        )
        if vercel_token:
            try:
                from orchestrator.build.vercel_client import VercelClient

                vercel_client = VercelClient(
                    api_token=vercel_token,
                    team_id=os.environ.get("VERCEL_TEAM_ID"),
                    project_id=os.environ.get("VERCEL_PROJECT_ID"),
                )
                if vercel_client.health_check():
                    logger.info("ClawLauncher: VercelClient connected successfully")
                else:
                    logger.warning(
                        "ClawLauncher: VercelClient health check failed, using stub"
                    )
                    vercel_client = None
            except ImportError as e:
                logger.warning("ClawLauncher: VercelClient import failed: %s", e)
            except Exception as e:
                logger.warning("ClawLauncher: VercelClient init failed: %s", e)

        # Initialize real Sentry client if token available
        sentry_client = None
        sentry_token = os.environ.get("SENTRY_AUTH_TOKEN")
        if sentry_token:
            try:
                from orchestrator.build.sentry_client import SentryClient

                sentry_client = SentryClient(
                    auth_token=sentry_token,
                    org_slug=os.environ.get("SENTRY_ORG_SLUG"),
                    project_slug=os.environ.get("SENTRY_PROJECT_SLUG"),
                )
                if sentry_client.health_check():
                    logger.info("ClawLauncher: SentryClient connected successfully")
                else:
                    logger.warning(
                        "ClawLauncher: SentryClient health check failed, using stub"
                    )
                    sentry_client = None
            except ImportError as e:
                logger.warning("ClawLauncher: SentryClient import failed: %s", e)
            except Exception as e:
                logger.warning("ClawLauncher: SentryClient init failed: %s", e)

        # Use stub clients if real ones not available
        if vercel_client is None:

            class _StubVercelClient:
                def health_check(self):
                    return False

                def trigger_deployment(self, *a, **kw):
                    return {"id": None, "status": "skipped", "url": None}

                def get_deployment_status(self, *a, **kw):
                    return "skipped"

                def get_deployment_url(self, *a, **kw):
                    return ""

                def wait_for_deployment(self, *a, **kw):
                    return "skipped"

                def rollback(self, *a, **kw):
                    return {}

                def list_deployments(self, *a, **kw):
                    return []

            vercel_client = _StubVercelClient()
            logger.debug("ClawLauncher: using stub VercelClient")

        if github_client is None:

            class _StubGitHubClient:
                def get_open_issues(self, limit=50):
                    return []

                def create_issue(self, *a, **kw):
                    return None

                def create_branch(self, *a, **kw):
                    return False

                def commit_file(self, *a, **kw):
                    return False

                def create_pull_request(self, *a, **kw):
                    return (None, None)

                def merge_pull_request(self, *a, **kw):
                    return False

                def list_prs(self, *a, **kw):
                    return []

            github_client = _StubGitHubClient()
            logger.debug("ClawLauncher: using stub GitHubClient")

        if sentry_client is None:

            class _StubSentryClient:
                def health_check(self):
                    return False

                def get_recent_errors(self, *a, **kw):
                    return []

                def list_events(self, *a, **kw):
                    return []

                def get_event(self, *a, **kw):
                    return {}

                def create_release(self, *a, **kw):
                    return {}

                def upload_sourcemap(self, *a, **kw):
                    return {}

                def deploy_release(self, *a, **kw):
                    return {}

                def list_projects(self, *a, **kw):
                    return []

                def get_release_stats(self, *a, **kw):
                    return {}

            sentry_client = _StubSentryClient()
            logger.debug("ClawLauncher: using stub SentryClient")

        claw = BuildClaw(
            squad_id=SQUAD_ID,
            inference_client=inference_client,
            github_client=github_client,
            vercel_client=vercel_client,
            sentry_client=sentry_client,
            mesh_gateway=DictMeshGatewayAdapter(self._mesh_gateway, "build"),
            base_path=BASE,
        )
        claw.startup()
        logger.info(
            "ClawLauncher: BuildClaw using RealMeshGateway via DictMeshGatewayAdapter"
        )

        heartbeat = HeartbeatEmitter("build", self.heartbeat_interval)
        heartbeat.start()

        def handle_message(msg):
            try:
                claw.handle_inbound(msg)
            except Exception as e:
                logger.error("BuildClaw: handle_inbound error: %s", e)

        poller = InboxPoller("build", self.poll_interval, handle_message, write_outbox)
        poller.start()

        return claw, heartbeat, poller

    def _start_generic_claw(self, role: str) -> tuple:
        """Start a generic claw with real clients when available."""
        claw = None
        heartbeat = HeartbeatEmitter(role, self.heartbeat_interval)
        heartbeat.start()

        poller = InboxPoller(role, self.poll_interval, outbox_writer=write_outbox)
        poller.start()

        try:
            if role == "content":
                from orchestrator.content.content_claw import ContentClaw
                from orchestrator.inference_client import NvidiaInferenceClient

                inference = NvidiaInferenceClient(
                    api_key=os.environ.get("NVIDIA_API_KEY"),
                    api_base=os.environ.get("NVIDIA_API_BASE"),
                )
                mesh_sender = CallableMeshSenderAdapter(self._mesh_gateway, "content")
                claw = ContentClaw(
                    squad_id=SQUAD_ID,
                    inference_client=inference,
                    mesh_sender=mesh_sender,
                    base_path=claw_base("content"),
                )
                claw.startup()
                poller._message_handler = claw.handle_inbound
                logger.info(
                    "ClawLauncher: ContentClaw using RealMeshGateway via CallableMeshSenderAdapter"
                )

            elif role == "ops":
                from orchestrator.ops.ops_claw import OpsClaw
                from orchestrator.inference_client import NvidiaInferenceClient

                inference = NvidiaInferenceClient(
                    api_key=os.environ.get("NVIDIA_API_KEY"),
                    api_base=os.environ.get("NVIDIA_API_BASE"),
                )
                mesh_gateway = DictMeshGatewayAdapter(self._mesh_gateway, "ops")
                claw = OpsClaw(
                    squad_id=SQUAD_ID,
                    inference_client=inference,
                    mesh_gateway=mesh_gateway,
                    base_path=claw_base("ops"),
                )
                claw.startup()
                poller._message_handler = claw.handle_inbound
                logger.info(
                    "ClawLauncher: OpsClaw using RealMeshGateway via DictMeshGatewayAdapter"
                )

            elif role == "analytics":
                from orchestrator.analytics.analytics_claw import AnalyticsClaw
                from orchestrator.inference_client import NvidiaInferenceClient

                inference = NvidiaInferenceClient(
                    api_key=os.environ.get("NVIDIA_API_KEY"),
                    api_base=os.environ.get("NVIDIA_API_BASE"),
                )
                mesh_sender = CallableMeshSenderAdapter(self._mesh_gateway, "analytics")
                claw = AnalyticsClaw(
                    squad_id=SQUAD_ID,
                    inference_client=inference,
                    mesh_sender=mesh_sender,
                    base_path=claw_base("analytics"),
                )
                claw.startup()
                poller._message_handler = claw.handle_inbound
                logger.info(
                    "ClawLauncher: AnalyticsClaw using RealMeshGateway via CallableMeshSenderAdapter"
                )

            elif role == "finance":
                from orchestrator.finance.finance_claw import FinanceClaw
                from orchestrator.finance.stripe_client import StripeClient
                from orchestrator.inference_client import NvidiaInferenceClient

                inference = NvidiaInferenceClient(
                    api_key=os.environ.get("NVIDIA_API_KEY"),
                    api_base=os.environ.get("NVIDIA_API_BASE"),
                )
                stripe = StripeClient(
                    api_key=os.environ.get("STRIPE_SECRET_KEY"),
                    webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET"),
                    currency=os.environ.get("STRIPE_CURRENCY", "usd"),
                )

                claw = FinanceClaw(
                    squad_id=SQUAD_ID,
                    inference_client=inference,
                    stripe_client=stripe,
                    gateway=self._mesh_gateway,
                    base_path=claw_base("finance"),
                )
                claw.startup()
                poller._message_handler = claw.handle_inbound
                logger.info("ClawLauncher: FinanceClaw using shared RealMeshGateway")

            elif role == "assistant":
                from orchestrator.assistant.lucy import LucyAssistant

                claw = LucyAssistant(
                    squad_id=SQUAD_ID,
                    mesh_gateway=self._mesh_gateway,
                    base_path=claw_base("assistant"),
                )
                claw.startup()
                poller._message_handler = claw.handle_inbound
                logger.info(
                    "ClawLauncher: LucyAssistant using shared RealMeshGateway"
                    " (Telegram handled by OpenShell channel messaging)"
                )

        except ImportError as e:
            logger.warning(
                "ClawLauncher: could not import %s claw: %s (running in stub mode)",
                role,
                e,
            )
        except Exception as e:
            logger.error("ClawLauncher: error starting %s claw: %s", role, e)

        return claw, heartbeat, poller


def _daemonize() -> None:
    """Fork into background and write PID file."""
    try:
        pid = os.fork()
        if pid > 0:
            print(f"Launcher started in background (PID {pid})")
            print(f"PID file: {LAUNCHER_PID_FILE}")
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork failed: {e}\n")
        sys.exit(1)

    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork failed: {e}\n")
        sys.exit(1)

    LAUNCHER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()

    with open(LAUNCHER_LOG_FILE, "a") as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
    with open(LAUNCHER_LOG_FILE, "a") as log:
        os.dup2(log.fileno(), sys.stderr.fileno())

    LAUNCHER_PID_FILE.write_text(str(os.getpid()))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Milimo Claw Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--role", choices=ALL_ROLES, help="Start a specific claw")
    parser.add_argument("--all", action="store_true", help="Start all claws")
    parser.add_argument("--daemon", action="store_true", help="Run in background")
    parser.add_argument("--stop", action="store_true", help="Stop running launcher")
    parser.add_argument("--status", action="store_true", help="Show launcher status")
    parser.add_argument("--restart", choices=ALL_ROLES, help="Restart a specific claw")
    parser.add_argument(
        "--validate-only", action="store_true", help="Validate configuration and exit"
    )
    parser.add_argument("--heartbeat-interval", type=int, default=30)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--health-port",
        type=int,
        default=DEFAULT_HEALTH_PORT,
        help="Port for HTTP health endpoint",
    )
    args = parser.parse_args()
    health_port = args.health_port

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Handle --validate-only
    if args.validate_only:
        print("\n=== Environment Validation ===\n")
        env_result = validate_environment()
        print(json.dumps(env_result, indent=2))

        print("\n=== Client Validation ===\n")
        client_result = validate_clients()
        print(json.dumps(client_result, indent=2))

        if not env_result["valid"]:
            print("\n❌ Validation FAILED - missing required environment variables")
            sys.exit(1)
        else:
            print("\n✓ Validation PASSED")
            sys.exit(0)

    # Handle --stop
    if args.stop:
        if LAUNCHER_PID_FILE.exists():
            try:
                pid = int(LAUNCHER_PID_FILE.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                print(f"Stopped launcher (PID {pid})")
                LAUNCHER_PID_FILE.unlink()
            except ProcessLookupError:
                print("Launcher not running")
                LAUNCHER_PID_FILE.unlink(missing_ok=True)
            except Exception as e:
                print(f"Error stopping launcher: {e}")
        else:
            print("No launcher PID file found")
        return

    # Handle --status
    if args.status:
        if LAUNCHER_PID_FILE.exists():
            try:
                pid = int(LAUNCHER_PID_FILE.read_text().strip())
                os.kill(pid, 0)
                print(f"Launcher running (PID {pid})")
            except ProcessLookupError:
                print("Launcher not running (stale PID file)")
                LAUNCHER_PID_FILE.unlink()
            except Exception as e:
                print(f"Error checking launcher: {e}")
        else:
            print("Launcher not running")
        return

    # Handle --restart
    if args.restart:
        launcher = ClawLauncher()
        launcher.restart_role(args.restart)
        return

    # Validate environment before starting (only check current role's vars)
    env_result = validate_environment(role=args.role)
    if not env_result["valid"]:
        missing = env_result["missing_required"]
        # In sandbox mode, some vars are optional (proxy-injected or mocked)
        sandbox_mode = os.environ.get("NEMOCLAW_MODEL") is not None
        _SKIP_VARS = {"NVIDIA_API_KEY", "GITHUB_REPO", "STRIPE_SECRET_KEY"}
        if sandbox_mode:
            missing = [m for m in missing if m["var"] not in _SKIP_VARS]
        if missing:
            print("\n❌ Missing required environment variables:")
            for item in missing:
                print(f" - {item['role']}: {item['var']}")
            print("\nSet missing variables or use --validate-only for full report.")
            write_alert(
                "env_missing", "Missing required environment variables", env_result
            )
            sys.exit(1)
        if sandbox_mode:
            logger.warning(
                "Some env vars not set (running in sandbox mode with defaults)"
            )

    # Warn about missing optional vars
    if env_result["missing_optional"]:
        logger.warning("Optional integrations not configured:")
        for item in env_result["missing_optional"]:
            logger.warning("  - %s: %s", item["category"], item["var"])

    # Daemonize if requested
    if args.daemon:
        if LAUNCHER_PID_FILE.exists():
            try:
                pid = int(LAUNCHER_PID_FILE.read_text().strip())
                os.kill(pid, 0)
                print("Launcher already running. Use --stop first.")
                sys.exit(1)
            except (ProcessLookupError, ValueError, OSError):
                logger.warning(
                    "Stale PID file found (PID %s), cleaning up",
                    LAUNCHER_PID_FILE.read_text().strip(),
                )
                LAUNCHER_PID_FILE.unlink(missing_ok=True)
        _daemonize()

    # Create launcher
    launcher = ClawLauncher(
        heartbeat_interval=args.heartbeat_interval,
        poll_interval=args.poll_interval,
    )

    # Start health endpoint
    start_health_server(launcher, health_port)

    # Handle shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down...")
        launcher.stop_all()
        if LAUNCHER_PID_FILE.exists():
            LAUNCHER_PID_FILE.unlink()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start claws
    if args.all:
        launcher.start_all()
    elif args.role:
        launcher.start_role(args.role)
    else:
        launcher.start_all()

    # Write PID file
    if args.daemon:
        LAUNCHER_PID_FILE.write_text(str(os.getpid()))

    # Print startup summary
    print_startup_summary(launcher)

    # Start health verification thread
    def verify_health():
        time.sleep(10)
        status = launcher.status()
        unhealthy = []
        for role, claw_status in status.get("claws", {}).items():
            if claw_status.get("status") != "running":
                unhealthy.append(role)

        if unhealthy:
            write_alert(
                "startup_health_failed",
                f"Claws failed to start: {', '.join(unhealthy)}",
                {"unhealthy_claws": unhealthy},
            )
        else:
            logger.info("All claws healthy after startup verification")

    health_thread = threading.Thread(target=verify_health, daemon=True)
    health_thread.start()

    # Keep running
    try:
        while launcher._running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    launcher.stop_all()


if __name__ == "__main__":
    main()
