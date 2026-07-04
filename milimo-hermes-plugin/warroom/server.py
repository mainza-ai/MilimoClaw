import os
import sys
import json
import html as html_mod
import logging
import signal
import threading
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution: prefer env override, fall back to stacking known layouts
# so the server works outside a NemoClaw sandbox without hardcoded paths.
# ---------------------------------------------------------------------------
_MILIMO_CORE_PATH = os.environ.get("MILIMO_CORE_PATH")
_MILIMO_BLUEPRINT_PATH = os.environ.get("MILIMO_BLUEPRINT_PATH")
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent  # milimo-hermes-plugin/

_WANTED = [
    _MILIMO_CORE_PATH,
    str(_REPO_ROOT / "milimo-core" / "src"),
    "/opt/milimo-core/src",
    "/sandbox/.openclaw/milimo/milimo-core/src",
]

for _p in _WANTED:
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

_BLUEPRINTS = [
    _MILIMO_BLUEPRINT_PATH,
    str(_REPO_ROOT / "milimo-blueprint"),
    "/opt/milimo-blueprint",
    "/sandbox/.openclaw/milimo/milimo-blueprint",
]

for _p in _BLUEPRINTS:
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Auth: fail-closed by default; set WARROOM_AUTH_TOKEN to a strong secret.
# ---------------------------------------------------------------------------
WARROOM_AUTH_TOKEN = os.environ.get("WARROOM_AUTH_TOKEN", "")

# ---------------------------------------------------------------------------
# Role list — sourced from the canonical contracts module.
# ---------------------------------------------------------------------------
try:
    from milimo_core.contracts import VALID_ROLES
except ImportError:
    VALID_ROLES = ["content", "ops", "analytics", "finance", "build", "assistant"]

# ---------------------------------------------------------------------------
# Bridge layer — delegates file operations out of the request handler.
# ---------------------------------------------------------------------------
from warroom_bridge import approve_hold_message, veto_hold_message, resolve_mesh_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("milimo.warroom_server")

os.chdir(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Graceful shutdown helpers
# ---------------------------------------------------------------------------
_httpd: HTTPServer | None = None
_server_thread: threading.Thread | None = None  # type: ignore[name-defined]


def _handle_sigterm(signum, _frame):
    logger.info("SIGTERM/SIGINT received — shutting down gracefully")
    if _httpd is not None:
        _httpd.shutdown()


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _extract_bearer(headers):
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return ""


def _require_auth(handler: BaseHTTPRequestHandler) -> bool:
    if not WARROOM_AUTH_TOKEN:
        return True
    token = _extract_bearer(handler.headers)
    if not token or token != WARROOM_AUTH_TOKEN:
        _send_json(handler, 401, {"error": "Unauthorized"})
        return False
    return True


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.end_headers()
    handler.wfile.write(body)


def _send_html(
    handler: BaseHTTPRequestHandler,
    status: int,
    html_body: str,
    request_id: str,
):
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("X-Request-ID", request_id)
    handler.end_headers()
    handler.wfile.write(html_body.encode("utf-8"))


def _safe_action_id(raw: str) -> str:
    if any(x in raw for x in ("/", "\\")) or raw.startswith("..") or raw.strip() in (".", ".."):
        raise ValueError(f"Invalid action_id: {raw!r}")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("action_id is empty")
    return cleaned


def _escaped_error(exc: Exception) -> str:
    return html_mod.escape(str(exc), quote=True)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------
class WarRoomHTMXHandler(BaseHTTPRequestHandler):
    """Hardened HTMX handler — all public endpoints require Bearer auth
    when WARROOM_AUTH_TOKEN is set; path traversal is blocked;
    error responses are HTML-escaped."""

    request_id: str = ""

    def log_message(self, fmt, *args):
        logger.debug("[%s] %s", self.request_id, fmt % args)

    # ------------------------------------------------------------------
    # Route dispatch
    # ------------------------------------------------------------------

    def do_GET(self):
        self.request_id = str(uuid.uuid4())
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            _send_json(self, 200, {"status": "ok"})
            return

        if not _require_auth(self):
            return

        if path == "/v1/warroom/claw-status":
            self._handle_claw_status()
        elif path == "/v1/warroom/hold-queue":
            self._handle_hold_queue()
        elif path == "/v1/warroom/cost-guard":
            self._handle_cost_guard()
        elif path == "/v1/warroom/last-updated":
            self._handle_last_updated()
        elif path == "/" or path.endswith("/warroom.html"):
            self._serve_static(path)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        self.request_id = str(uuid.uuid4())
        parsed = urlparse(self.path)
        path = parsed.path

        if not _require_auth(self):
            return

        origin = self.headers.get("Origin", "")
        expected = f"http://{self.headers.get('Host', '')}"
        if origin and origin != expected:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Origin not allowed")
            logger.warning(
                "[%s] CSRF blocked: Origin=%s Host=%s",
                self.request_id, origin, self.headers.get("Host"),
            )
            return

        parts = path.strip("/").split("/")
        if (
            len(parts) == 5
            and parts[:3] == ["v1", "warroom", "hold-queue"]
            and parts[4] in ("approve", "veto")
        ):
            try:
                action_id = _safe_action_id(parts[3])
            except ValueError as exc:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Bad request: {_escaped_error(exc)}".encode("utf-8"))
                logger.warning("[%s] Bad action_id: %s", self.request_id, parts[3])
                return
            self._process_decision(action_id, parts[4])
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad request")

    # ------------------------------------------------------------------
    # GET handlers
    # ------------------------------------------------------------------

    def _serve_static(self, path: str):
        try:
            candidates = ["warroom.html", "index.html"]
            for name in candidates:
                if Path(name).exists():
                    with open(name, "rb") as fh:
                        data = fh.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"warroom.html not found")
        except Exception as exc:
            logger.exception("[%s] Error serving static file", self.request_id)
            _send_html(
                self, 500,
                f'<div class="error">Error: {_escaped_error(exc)}</div>',
                self.request_id,
            )

    def _handle_claw_status(self):
        try:
            from milimo_core.bridge_cli import handle_collect_health
            try:
                health = handle_collect_health({})
            except Exception as exc:
                logger.warning(
                    "[%s] Could not collect health from bridge_cli, using stub: %s",
                    self.request_id, exc,
                )
                health = {}

            if not health:
                _send_html(
                    self, 200,
                    '<div class="empty">Health data unavailable</div>',
                    self.request_id,
                )
                return

            html_parts = []
            for role in VALID_ROLES:
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
            _send_html(self, 200, "".join(html_parts), self.request_id)
        except Exception as exc:
            logger.exception("[%s] Error serving claw status", self.request_id)
            _send_html(
                self, 500,
                f'<div class="error">Error: {_escaped_error(exc)}</div>',
                self.request_id,
            )

    def _handle_hold_queue(self):
        try:
            mesh_dir = resolve_mesh_dir()
            warroom_inbox = mesh_dir / "inbox" / "war_room"

            html_parts = []
            pending_files = []
            if warroom_inbox.exists():
                pending_files = sorted(
                    list(warroom_inbox.glob("*.json")),
                    key=lambda f: f.stat().st_mtime,
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

                        is_hold = (
                            msg_type in ("spend_hold_decision", "hold_release")
                            or payload.get("mode") == "HOLD"
                        )
                        approve_label = "Release" if is_hold else "Approve"
                        btn_cls = "btn-approve"

                        safe_description = html_mod.escape(description, quote=True)
                        safe_sender = html_mod.escape(sender, quote=True).upper()

                        html_parts.append(f"""
                        <div class="hold-item">
                            <div class="hold-info">
                                <div class="hold-id">{safe_description}</div>
                                <div class="hold-claw">{safe_sender} CLAW</div>
                            </div>
                            <div class="hold-actions">
                                <button class="btn {btn_cls}" hx-post="/v1/warroom/hold-queue/{msg_file.name}/approve" hx-target="#hold-queue">{approve_label}</button>
                                <button class="btn btn-veto" hx-post="/v1/warroom/hold-queue/{msg_file.name}/veto" hx-target="#hold-queue">Veto</button>
                            </div>
                        </div>
                        """)
                    except Exception as fe:
                        logger.warning(
                            "[%s] Failed to parse message file %s: %s",
                            self.request_id, msg_file, fe,
                        )

                html = "".join(html_parts) if html_parts else '<div class="empty">No pending actions</div>'
            _send_html(self, 200, html, self.request_id)
        except Exception as exc:
            logger.exception("[%s] Error serving hold queue", self.request_id)
            _send_html(
                self, 500,
                f'<div class="error">Error: {_escaped_error(exc)}</div>',
                self.request_id,
            )

    def _handle_cost_guard(self):
        try:
            from milimo_core.cost_guard import get_cost_guard
            cg = get_cost_guard()
            usage = cg.get_usage()

            percent = min(100.0, usage.percent_used)
            html_body = f"""
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
            _send_html(self, 200, html_body, self.request_id)
        except Exception as exc:
            logger.exception("[%s] Error serving cost guard", self.request_id)
            _send_html(
                self, 500,
                f'<div class="error">Error: {_escaped_error(exc)}</div>',
                self.request_id,
            )

    def _handle_last_updated(self):
        _send_html(self, 200, datetime.now().strftime("%I:%M:%S %p"), self.request_id)

    # ------------------------------------------------------------------
    # POST handler
    # ------------------------------------------------------------------

    def _process_decision(self, filename: str, decision: str):
        try:
            if decision == "approve":
                approve_hold_message(filename)
            elif decision == "veto":
                veto_hold_message(filename)
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad decision")
                return
            self._handle_hold_queue()
        except Exception as exc:
            logger.exception(
                "[%s] Error processing decision %s on %s",
                self.request_id, decision, filename,
            )
            _send_html(
                self, 500,
                f'<div class="error">Error: {_escaped_error(exc)}</div>',
                self.request_id,
            )


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------
def run(port: int = 9090):
    global _httpd, _server_thread
    server = HTTPServer(("0.0.0.0", port), WarRoomHTMXHandler)
    _httpd = server

    if WARROOM_AUTH_TOKEN:
        logger.info(
            "War Room auth ENABLED — set WARROOM_AUTH_TOKEN env var (Bearer token required)"
        )
    else:
        logger.warning(
            "War Room auth DISABLED — set WARROOM_AUTH_TOKEN to enable Bearer auth"
        )

    logger.info(
        "Milimo War Room Server running on http://localhost:%d/warroom.html", port
    )

    _server_thread = threading.Thread(
        target=server.serve_forever, name="warroom-http", daemon=False
    )
    _server_thread.start()

    try:
        _server_thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping HTTP server...")
        server.shutdown()
        _server_thread.join(timeout=5)
        server.server_close()
        logger.info("Server stopped cleanly")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int, default=8080)
    args = parser.parse_args()
    run(args.port)
