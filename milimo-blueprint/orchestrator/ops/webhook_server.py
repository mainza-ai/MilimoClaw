"""
Ops Claw Webhook Server for real-time incident ingestion.

Receives alerts from monitoring systems (Sentry, Vercel, uptime monitors)
and forwards them to the Ops Claw signal dispatcher for analysis and remediation.

Endpoints:
    POST /webhook/sentry    — Sentry error alerts
    POST /webhook/vercel    — Vercel deployment alerts
    POST /webhook/uptime    — Uptime monitor alerts
    POST /webhook/generic   — Generic JSON alert payload
    GET  /health            — Health check

Usage:
    server = OpsWebhookServer(port=8080, dispatcher=ops_signal_dispatcher)
    server.start()  # Runs in background thread
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

logger = logging.getLogger("milimo.ops_webhook")


class _WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook endpoints."""

    # Set by the server at startup
    ops_claw: Any = None
    dispatcher: Any = None
    alert_buffer: list[dict] = []
    buffer_lock = threading.Lock()

    def log_message(self, format: str, *args) -> None:
        """Suppress default stderr logging."""
        logger.debug("Webhook: %s", format % args)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if self.path == "/webhook/sentry":
            alert = self._parse_sentry_alert(payload)
        elif self.path == "/webhook/vercel":
            alert = self._parse_vercel_alert(payload)
        elif self.path == "/webhook/uptime":
            alert = self._parse_uptime_alert(payload)
        elif self.path == "/webhook/generic":
            alert = self._parse_generic_alert(payload)
        else:
            self._send_json(404, {"error": "Unknown webhook endpoint"})
            return

        # Buffer the alert
        with self.buffer_lock:
            self.alert_buffer.append(alert)

        # Forward to ops_claw for full analysis + remediation pipeline
        if self.ops_claw and hasattr(self.ops_claw, "handle_incident"):
            try:
                self.ops_claw.handle_incident(alert)
            except Exception as e:
                logger.error("Failed to dispatch alert to ops claw: %s", e)
        elif self.dispatcher and hasattr(self.dispatcher, "handle_incident"):
            # Fallback: just log via dispatcher
            try:
                self.dispatcher.handle_incident(alert)
            except Exception as e:
                logger.error("Failed to dispatch alert: %s", e)

        self._send_json(200, {"status": "received", "alert_id": alert.get("alert_id")})

    def _parse_sentry_alert(self, payload: dict) -> dict:
        """Parse Sentry webhook payload."""
        # Sentry v1 webhook format
        action = payload.get("action", "created")
        data = payload.get("data", {})
        issue = data.get("issue", {})

        return {
            "alert_id": f"sentry-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "source": "sentry",
            "severity": self._map_sentry_severity(data),
            "title": issue.get("title", "Unknown Sentry alert"),
            "description": data.get("description", ""),
            "url": issue.get("url", ""),
            "project": issue.get("project", {}).get("name", ""),
            "culprit": issue.get("culprit", ""),
            "level": data.get("level", "error"),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": payload,
        }

    def _parse_vercel_alert(self, payload: dict) -> dict:
        """Parse Vercel webhook payload."""
        return {
            "alert_id": f"vercel-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "source": "vercel",
            "severity": "warning" if payload.get("deployment", {}).get("state") == "ERROR" else "info",
            "title": f"Vercel deployment {payload.get('deployment', {}).get('state', 'unknown')}",
            "description": f"Deployment {payload.get('deployment', {}).get('uid', '')} for {payload.get('name', '')}",
            "url": payload.get("deployment", {}).get("url", ""),
            "project": payload.get("name", ""),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": payload,
        }

    def _parse_uptime_alert(self, payload: dict) -> dict:
        """Parse uptime monitor webhook payload."""
        return {
            "alert_id": f"uptime-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "source": "uptime",
            "severity": "critical" if payload.get("status") == "down" else "warning",
            "title": f"Service {payload.get('status', 'unknown')}: {payload.get('name', '')}",
            "description": payload.get("details", ""),
            "url": payload.get("url", ""),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": payload,
        }

    def _parse_generic_alert(self, payload: dict) -> dict:
        """Parse generic JSON alert payload."""
        return {
            "alert_id": f"generic-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "source": payload.get("source", "generic"),
            "severity": payload.get("severity", "warning"),
            "title": payload.get("title", "Generic alert"),
            "description": payload.get("description", ""),
            "url": payload.get("url", ""),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": payload,
        }

    @staticmethod
    def _map_sentry_severity(data: dict) -> str:
        """Map Sentry level to internal severity."""
        level = data.get("level", "error").lower()
        severity_map = {
            "fatal": "critical",
            "error": "critical",
            "warning": "warning",
            "info": "info",
            "debug": "info",
        }
        return severity_map.get(level, "warning")

    def _send_json(self, status: int, data: dict) -> None:
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


class OpsWebhookServer:
    """
    Webhook server for Ops Claw incident ingestion.

    Runs in a background thread. Start with server.start(), stop with server.stop().

    Usage:
        server = OpsWebhookServer(port=8080, dispatcher=ops_signal_dispatcher)
        server.start()
        # ... later ...
        server.stop()
    """

    def __init__(
        self,
        port: int = 8080,
        host: str = "0.0.0.0",
        dispatcher: Any | None = None,
        ops_claw: Any | None = None,
    ) -> None:
        self.port = port
        self.host = host
        self.dispatcher = dispatcher
        self.ops_claw = ops_claw
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the webhook server in a background thread."""
        if self._running:
            logger.warning("Webhook server already running")
            return

        # Clear stale alert buffer from previous session
        with _WebhookHandler.buffer_lock:
            _WebhookHandler.alert_buffer.clear()

        # Configure the handler class with our dispatcher and ops_claw
        _WebhookHandler.dispatcher = self.dispatcher
        _WebhookHandler.ops_claw = self.ops_claw

        self._server = HTTPServer((self.host, self.port), _WebhookHandler)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True, name="ops-webhook")
        self._thread.start()
        logger.info("Ops webhook server started on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Stop the webhook server."""
        self._running = False
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Ops webhook server stopped")

    def get_alerts(self) -> list[dict]:
        """Get all buffered alerts and clear the buffer."""
        with _WebhookHandler.buffer_lock:
            alerts = list(_WebhookHandler.alert_buffer)
            _WebhookHandler.alert_buffer.clear()
        return alerts

    def _serve(self) -> None:
        """Serve until stopped."""
        if self._server:
            self._server.serve_forever()
