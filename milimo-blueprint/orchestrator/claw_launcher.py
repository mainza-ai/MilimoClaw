#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Claw Launcher

Starts all claw autonomous agents with:
- Filesystem initialization
- Dependency injection (GitHub client, inference client, etc.)
- Message inbox polling loop
- Heartbeat emission on a timer

Usage:
    python3 claw_launcher.py [--role build] [--heartbeat-interval 30]

    Or start all claws:
    python3 claw_launcher.py --all
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
from datetime import datetime, timezone
from pathlib import Path

# Add blueprint to path
BLUEPRINT_PATH = Path("/sandbox/.milimo/blueprints/0.1.0")
if BLUEPRINT_PATH.exists():
    sys.path.insert(0, str(BLUEPRINT_PATH))

logger = logging.getLogger("milimo.claw_launcher")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SQUAD_ID = os.environ.get("SQUAD_ID", "zulu")
MESH_DIR = Path.home() / ".milimo" / "mesh"
HEARTBEAT_DIR = MESH_DIR / "heartbeats"
INBOX_DIR = MESH_DIR / "inbox"

ALL_ROLES = ["content", "ops", "analytics", "finance", "build"]

# ---------------------------------------------------------------------------
# Heartbeat Emitter
# ---------------------------------------------------------------------------


class HeartbeatEmitter:
    """Emits periodic heartbeats for a claw process."""

    def __init__(self, role: str, interval: int = 30):
        self.role = role
        self.interval = interval
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start emitting heartbeats in a background thread."""
        HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._emit_loop, daemon=True)
        self._thread.start()
        logger.info("Heartbeat emitter started for %s (interval=%ds)", self.role, self.interval)

    def stop(self):
        """Stop emitting heartbeats."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Heartbeat emitter stopped for %s", self.role)

    def _emit_loop(self):
        while self._running:
            try:
                self._emit()
            except Exception as e:
                logger.error("Heartbeat emit failed for %s: %s", self.role, e)
            time.sleep(self.interval)

    def _emit(self):
        heartbeat = {
            "role": self.role,
            "squad_id": SQUAD_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "status": "running",
            "uptime_seconds": time.monotonic(),
        }
        heartbeat_file = HEARTBEAT_DIR / f"{self.role}.json"
        heartbeat_file.write_text(json.dumps(heartbeat, indent=2))


# ---------------------------------------------------------------------------
# Inbox Poller
# ---------------------------------------------------------------------------


class InboxPoller:
    """Polls a claw's inbox for new messages and processes them."""

    def __init__(self, role: str, interval: int = 5, message_handler=None):
        self.role = role
        self.interval = interval
        self.inbox = INBOX_DIR / role
        self._running = False
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._message_handler = message_handler

    def start(self):
        """Start polling the inbox in a background thread."""
        self.inbox.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Inbox poller started for %s (interval=%ds)", self.role, self.interval)

    def stop(self):
        """Stop polling the inbox."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Inbox poller stopped for %s", self.role)

    def _poll_loop(self):
        while self._running:
            try:
                self._check_inbox()
            except Exception as e:
                logger.error("Inbox poll failed for %s: %s", self.role, e)
            time.sleep(self.interval)

    def _check_inbox(self):
        if not self.inbox.exists():
            return

        for msg_file in sorted(self.inbox.glob("*.json")):
            msg_id = msg_file.stem
            if msg_id in self._processed:
                continue

            try:
                content = json.loads(msg_file.read_text())
                logger.info("Processing message %s for %s: %s", msg_id, self.role, content.get("message_type"))

                if self._message_handler:
                    self._message_handler(content)

                # Mark as processed
                self._processed.add(msg_id)

                # Archive processed message
                archive_dir = self.inbox / "processed"
                archive_dir.mkdir(exist_ok=True)
                msg_file.rename(archive_dir / msg_file.name)

            except Exception as e:
                logger.error("Failed to process message %s: %s", msg_id, e)


# ---------------------------------------------------------------------------
# Claw Starter
# ---------------------------------------------------------------------------


def start_build_claw(heartbeat_interval: int = 30, poll_interval: int = 5):
    """Start the Build Claw autonomous agent."""
    try:
        from orchestrator.build.build_claw import BuildClaw
        from orchestrator.build.build_init import BASE
        from orchestrator.inference_client import NvidiaInferenceClient
        from orchestrator.github_client import GitHubClient

        # Create real clients with environment-based configuration
        inference_client = NvidiaInferenceClient(
            api_key=os.environ.get("NVIDIA_API_KEY") or os.environ.get("BUILD_CLAW_NVIDIA_API_KEY"),
            api_base=os.environ.get("NVIDIA_API_BASE"),
        )

        github_client = GitHubClient(
            repo=os.environ.get("GITHUB_REPO"),
        )

        class MockVercelClient:
            pass

        class MockSentryClient:
            pass

        claw = BuildClaw(
            squad_id=SQUAD_ID,
            inference_client=inference_client,
            github_client=github_client,
            vercel_client=MockVercelClient(),
            sentry_client=MockSentryClient(),
            base_path=BASE,
        )

        # Start the claw (this initializes filesystem, managers, etc.)
        claw.startup()
        logger.info("Build Claw started successfully")

        # Start heartbeat
        heartbeat = HeartbeatEmitter("build", heartbeat_interval)
        heartbeat.start()

        # Start inbox poller
        def handle_message(msg):
            try:
                claw.handle_inbound(msg)
            except Exception as e:
                logger.error("Error handling message: %s", e)

        poller = InboxPoller("build", poll_interval, handle_message)
        poller.start()

        return claw, heartbeat, poller

    except ImportError as e:
        logger.error("Failed to import BuildClaw: %s", e)
        return None, None, None
    except Exception as e:
        logger.error("Failed to start BuildClaw: %s", e)
        return None, None, None


def start_generic_claw(role: str, heartbeat_interval: int = 30, poll_interval: int = 5):
    """Start a generic claw (content, ops, analytics, finance) with heartbeat, inbox polling, and message handlers."""
    try:
        # Import the appropriate claw class based on role
        if role == "content":
            from orchestrator.content.content_claw import ContentClaw
            from orchestrator.inference_client import NvidiaInferenceClient
            inference = NvidiaInferenceClient(
                api_key=os.environ.get("NVIDIA_API_KEY"),
                api_base=os.environ.get("NVIDIA_API_BASE"),
            )
            claw = ContentClaw(
                squad_id=SQUAD_ID,
                inference_client=inference,
                base_path=Path("/sandbox/content"),
            )
            claw.startup()
            message_handler = claw.handle_inbound
        elif role == "ops":
            from orchestrator.ops.ops_claw import OpsClaw
            from orchestrator.inference_client import NvidiaInferenceClient
            inference = NvidiaInferenceClient(
                api_key=os.environ.get("NVIDIA_API_KEY"),
                api_base=os.environ.get("NVIDIA_API_BASE"),
            )
            claw = OpsClaw(
                squad_id=SQUAD_ID,
                inference_client=inference,
                base_path=Path("/sandbox/ops"),
            )
            claw.startup()
            message_handler = claw.handle_inbound
        elif role == "analytics":
            from orchestrator.analytics.analytics_claw import AnalyticsClaw
            claw = AnalyticsClaw(
                squad_id=SQUAD_ID,
                base_path=Path("/sandbox/analytics"),
            )
            claw.startup()
            message_handler = claw.handle_inbound
        elif role == "finance":
            from orchestrator.finance.finance_claw import FinanceClaw
            claw = FinanceClaw(
                squad_id=SQUAD_ID,
                base_path=Path("/sandbox/finance"),
            )
            claw.startup()
            message_handler = claw.handle_inbound
        else:
            logger.warning("Unknown claw role: %s", role)
            heartbeat = HeartbeatEmitter(role, heartbeat_interval)
            heartbeat.start()
            poller = InboxPoller(role, poll_interval)
            poller.start()
            return heartbeat, poller

        # Start heartbeat
        heartbeat = HeartbeatEmitter(role, heartbeat_interval)
        heartbeat.start()

        # Start inbox poller with the claw's message handler
        poller = InboxPoller(role, poll_interval, message_handler)
        poller.start()

        logger.info("Claw %s started with heartbeat, inbox polling, and message handler", role)
        return heartbeat, poller

    except ImportError as e:
        logger.error("Failed to import %s claw: %s", role, e)
        # Fall back to basic heartbeat + poller
        heartbeat = HeartbeatEmitter(role, heartbeat_interval)
        heartbeat.start()
        poller = InboxPoller(role, poll_interval)
        poller.start()
        return heartbeat, poller
    except Exception as e:
        logger.error("Failed to start %s claw: %s", role, e)
        heartbeat = HeartbeatEmitter(role, heartbeat_interval)
        heartbeat.start()
        poller = InboxPoller(role, poll_interval)
        poller.start()
        return heartbeat, poller


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Milimo Claw Launcher")
    parser.add_argument("--role", choices=ALL_ROLES, default="build", help="Which claw to start")
    parser.add_argument("--all", action="store_true", help="Start all claws")
    parser.add_argument("--heartbeat-interval", type=int, default=30, help="Heartbeat interval in seconds")
    parser.add_argument("--poll-interval", type=int, default=5, help="Inbox poll interval in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Ensure mesh directories exist
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Track all components for graceful shutdown
    components: list = []

    # Handle shutdown gracefully
    def shutdown(signum, frame):
        logger.info("Shutting down claw launcher...")
        for component in components:
            try:
                if hasattr(component, "stop"):
                    component.stop()
                    logger.info("Stopped component: %s", type(component).__name__)
            except Exception as e:
                logger.error("Error stopping component %s: %s", type(component).__name__, e)
        logger.info("All components stopped. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start FailoverManager for process supervision
    failover_manager = None
    try:
        from orchestrator.mesh_failover import FailoverManager
        failover_manager = FailoverManager(
            heartbeat_dir=str(HEARTBEAT_DIR),
            check_interval=60,
            unhealthy_threshold=90,
        )
        failover_manager.start()
        components.append(failover_manager)
        logger.info("FailoverManager started — monitoring claw heartbeats")
    except Exception as e:
        logger.warning("Failed to start FailoverManager: %s", e)

    if args.all:
        logger.info("Starting all claws...")
        started = []
        for role in ALL_ROLES:
            if role == "build":
                claw, heartbeat, poller = start_build_claw(args.heartbeat_interval, args.poll_interval)
                if claw:
                    started.append(role)
                    if heartbeat:
                        components.append(heartbeat)
                    if poller:
                        components.append(poller)
            else:
                heartbeat, poller = start_generic_claw(role, args.heartbeat_interval, args.poll_interval)
                started.append(role)
                if heartbeat:
                    components.append(heartbeat)
                if poller:
                    components.append(poller)

        logger.info("Started %d/%d claws: %s", len(started), len(ALL_ROLES), ", ".join(started))
    else:
        logger.info("Starting %s claw...", args.role)
        if args.role == "build":
            claw, heartbeat, poller = start_build_claw(args.heartbeat_interval, args.poll_interval)
            if claw:
                started = ["build"]
                if heartbeat:
                    components.append(heartbeat)
                if poller:
                    components.append(poller)
                logger.info("Build Claw started successfully")
            else:
                logger.error("Failed to start Build Claw")
                sys.exit(1)
        else:
            heartbeat, poller = start_generic_claw(args.role, args.heartbeat_interval, args.poll_interval)
            if heartbeat:
                components.append(heartbeat)
            if poller:
                components.append(poller)
            logger.info("%s claw started", args.role)

    # Keep main thread alive
    logger.info("Claw launcher running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Claw launcher stopped.")


if __name__ == "__main__":
    main()
