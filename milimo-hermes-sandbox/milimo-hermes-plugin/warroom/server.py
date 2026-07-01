import os
import sys
import json
import logging
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

# Ensure search paths include all Milimo components
sys.path.insert(0, "/sandbox/.nemoclaw/blueprints/0.1.0")
sys.path.insert(0, "/sandbox/.nemoclaw/blueprints/0.1.0/orchestrator")
sys.path.insert(0, "/opt/milimo-core")
sys.path.insert(0, "/opt/milimo-core/src")

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("milimo.warroom_server")

# Change directory to the folder containing this file to serve static assets
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def resolve_mesh_dir() -> Path:
    candidates = [
        "/sandbox/.hermes/mesh",
        "/sandbox/.openclaw/milimo/mesh",
        os.path.expanduser("~/.openclaw/milimo/mesh"),
        os.path.expanduser("~/.hermes/mesh"),
        "./mesh",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    p = Path(candidates[0])
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p

class WarRoomHTMXHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard logging to prevent console noise
        logger.debug(format % args)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/v1/warroom/claw-status":
            self._handle_claw_status()
        elif path == "/v1/warroom/hold-queue":
            self._handle_hold_queue()
        elif path == "/v1/warroom/cost-guard":
            self._handle_cost_guard()
        elif path == "/v1/warroom/last-updated":
            self._handle_last_updated()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Path format: /v1/warroom/hold-queue/{action_id}/{decision}
        parts = path.strip("/").split("/")
        if len(parts) == 5 and parts[:3] == ["v1", "warroom", "hold-queue"]:
            action_id = parts[3]
            decision = parts[4]
            self._process_decision(action_id, decision)
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad request")

    def _handle_claw_status(self):
        try:
            from milimo_core.bridge_cli import handle_collect_health
            try:
                health = handle_collect_health({})
            except Exception as e:
                logger.warning("Could not collect health from bridge_cli, using stub: %s", e)
                health = {}

            html_parts = []
            for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
                data = health.get(role, {})
                status = data.get("status", "idle")

                status_cls = "status-ready"
                if status in ("busy", "running", "active", "processing"):
                    status_cls = "status-busy"
                elif status in ("error", "crashed"):
                    status_cls = "status-error"

                html_parts.append(f"""
                <div class="claw">
                    <span class="claw-name">{role.upper()} CLAW</span>
                    <span class="claw-status {status_cls}">{status}</span>
                </div>
                """)
            self._send_html(200, "".join(html_parts))
        except Exception as e:
            logger.exception("Error serving claw status")
            self._send_html(500, f"<div class='empty'>Error: {e}</div>")

    def _handle_hold_queue(self):
        try:
            mesh_dir = resolve_mesh_dir()
            warroom_inbox = mesh_dir / "inbox" / "war_room"

            html_parts = []
            pending_files = []
            if warroom_inbox.exists():
                pending_files = sorted(
                    list(warroom_inbox.glob("*.json")),
                    key=lambda f: f.stat().st_mtime
                )

            if not pending_files:
                html = '<div class="empty">No pending actions</div>'
            else:
                for msg_file in pending_files:
                    try:
                        msg_data = json.loads(msg_file.read_text(encoding="utf-8"))
                        msg_id = msg_data.get("message_id", msg_file.stem)
                        sender = msg_data.get("sender_role", "unknown")
                        msg_type = msg_data.get("message_type", "unknown")
                        payload = msg_data.get("payload", {})

                        # Determine human-friendly details
                        description = f"Action Type: {msg_type}"
                        if msg_type == "spend_request":
                            merchant = payload.get("merchant_name", "unknown")
                            amount = payload.get("amount_cents", 0) / 100.0
                            description = f"Spend: ${amount:.2f} at {merchant}"
                        elif msg_type == "invoice_ready":
                            invoice_id = payload.get("invoice_id", "unknown")
                            amount = payload.get("amount", 0)
                            description = f"Invoice: ${amount:.2f} (#{invoice_id})"
                        elif msg_type == "draft_ready":
                            platform = payload.get("platform", "unknown")
                            description = f"Draft Ready for {platform}"
                        elif msg_type == "tool_proposal":
                            tool = payload.get("tool_name", "unknown")
                            description = f"Tool Proposal: {tool}"

                        # Determine if Stage 1 (REVIEW) or Stage 2 (HOLD)
                        is_hold = msg_type in ("spend_hold_decision", "hold_release") or payload.get("mode") == "HOLD"
                        approve_label = "Release" if is_hold else "Approve"
                        btn_cls = "btn-approve"

                        html_parts.append(f"""
                        <div class="hold-item">
                            <div class="hold-info">
                                <div class="hold-id">{description}</div>
                                <div class="hold-claw">{sender.upper()} CLAW</div>
                            </div>
                            <div class="hold-actions">
                                <button class="btn {btn_cls}" hx-post="/v1/warroom/hold-queue/{msg_file.name}/approve" hx-target="#hold-queue">{approve_label}</button>
                                <button class="btn btn-veto" hx-post="/v1/warroom/hold-queue/{msg_file.name}/veto" hx-target="#hold-queue">Veto</button>
                            </div>
                        </div>
                        """)
                    except Exception as fe:
                        logger.warning("Failed to parse message file %s: %s", msg_file, fe)

                html = "".join(html_parts) if html_parts else '<div class="empty">No pending actions</div>'
            self._send_html(200, html)
        except Exception as e:
            logger.exception("Error serving hold queue")
            self._send_html(500, f"<div class='empty'>Error: {e}</div>")

    def _handle_cost_guard(self):
        try:
            from milimo_core.cost_guard import get_cost_guard
            cg = get_cost_guard()
            usage = cg.get_usage()

            percent = min(100.0, usage.percent_used)
            html = f"""
            <div class="cost-guard">
                <div class="cost-text">
                    <span>{usage.total_tokens:,} / {usage.daily_limit:,} tokens</span>
                    <span>{percent:.1f}%</span>
                </div>
                <div class="cost-bar">
                    <div class="cost-fill" style="width: {percent}%"></div>
                </div>
            </div>
            """
            self._send_html(200, html)
        except Exception as e:
            logger.exception("Error serving cost guard")
            self._send_html(500, f"<div class='empty'>Error: {e}</div>")

    def _handle_last_updated(self):
        self._send_html(200, datetime.now().strftime("%I:%M:%S %p"))

    def _process_decision(self, filename, decision):
        try:
            mesh_dir = resolve_mesh_dir()
            warroom_inbox = mesh_dir / "inbox" / "war_room"
            filepath = warroom_inbox / filename

            if filepath.exists():
                msg_data = json.loads(filepath.read_text(encoding="utf-8"))

                if decision == "approve":
                    # Approved: Move from war_room to the original recipient inbox
                    recipient = msg_data.get("recipient_role", "finance")
                    target_dir = mesh_dir / "inbox" / recipient
                    target_dir.mkdir(parents=True, exist_ok=True)
                    filepath.rename(target_dir / filename)
                    logger.info("Approved message %s: moved to %s", filename, recipient)
                elif decision == "veto":
                    # Vetoed: Move to rejected queue
                    rejected_dir = mesh_dir / "rejected"
                    rejected_dir.mkdir(parents=True, exist_ok=True)
                    filepath.rename(rejected_dir / filename)
                    logger.info("Vetoed message %s: moved to rejected", filename)

            # Return updated hold queue HTML fragment
            self._handle_hold_queue()
        except Exception as e:
            logger.exception("Error processing decision")
            self._send_html(500, f"<div class='empty'>Error: {e}</div>")

    def _send_html(self, status, html):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

def run(port=8080):
    server = HTTPServer(("0.0.0.0", port), WarRoomHTMXHandler)
    logger.info("Milimo War Room Server running on http://localhost:%d/warroom.html", port)
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
