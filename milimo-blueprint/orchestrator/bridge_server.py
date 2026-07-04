# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Persistent JSON-RPC server for Milimo plugin.

Replaces per-call Python subprocess spawning with a single long-lived
HTTP server. Started by OpenClaw's service manager via api.registerService()
or by the install script.

Usage:
    python3 -m orchestrator.bridge_server [--port 19999]

Handlers receive (params: dict) and return a JSON-serializable value.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

logger = logging.getLogger("milimo.bridge_server")

RPC_PORT = int(os.environ.get("MILIMO_RPC_PORT", "19999"))


class RPCError(Exception):
    def __init__(self, message: str, code: int = -32603):
        self.message = message
        self.code = code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

HANDLERS: dict[str, callable] = {}


def rpc_method(fn: callable) -> callable:
    HANDLERS[fn.__name__] = fn
    return fn


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------


@rpc_method
def ping(params: dict[str, Any]) -> dict[str, Any]:
    return {"pong": True, "version": "0.1.0"}


@rpc_method
def python_eval(params: dict[str, Any]) -> dict[str, Any]:
    code = params.get("code", "")
    blueprint_dir = params.get("blueprintDir", "")
    try:
        import subprocess

        env = {**os.environ}
        if blueprint_dir:
            env["PYTHONPATH"] = os.pathsep.join(
                [blueprint_dir, str(Path(blueprint_dir) / "orchestrator")]
            )
        safe_code = (
            f"import sys; sys.path.insert(0, {json.dumps(blueprint_dir)}); {code}"
        )
        result = subprocess.run(
            [sys.executable, "-c", safe_code],
            cwd=blueprint_dir or None,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            raise RPCError(result.stderr.strip() or f"Exit code {result.returncode}")
        return {"stdout": result.stdout.strip()}
    except RPCError:
        raise
    except subprocess.TimeoutExpired:
        raise RPCError("Python eval timed out")
    except FileNotFoundError:
        raise RPCError(f"Python interpreter not found: {sys.executable}")
    except Exception as e:
        raise RPCError(str(e))


@rpc_method
def python_module(params: dict[str, Any]) -> dict[str, Any]:
    module_name = params.get("moduleName", "")
    args = params.get("args", [])
    blueprint_dir = params.get("blueprintDir", "")
    try:
        import subprocess

        env = {**os.environ}
        if blueprint_dir:
            env["PYTHONPATH"] = os.pathsep.join(
                [blueprint_dir, str(Path(blueprint_dir) / "orchestrator")]
            )
        result = subprocess.run(
            [sys.executable, "-m", module_name, *args],
            cwd=blueprint_dir or None,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            raise RPCError(result.stderr.strip() or f"Exit code {result.returncode}")
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except RPCError:
        raise
    except subprocess.TimeoutExpired:
        raise RPCError(f"Python module timed out: {module_name}")
    except Exception as e:
        raise RPCError(str(e))


@rpc_method
def python_file(params: dict[str, Any]) -> dict[str, Any]:
    script_path = params.get("scriptPath", "")
    args = params.get("args", [])
    blueprint_dir = params.get("blueprintDir", "")
    try:
        import subprocess

        env = {**os.environ}
        if blueprint_dir:
            env["PYTHONPATH"] = os.pathsep.join(
                [blueprint_dir, str(Path(blueprint_dir) / "orchestrator")]
            )
        result = subprocess.run(
            [sys.executable, script_path, *args],
            cwd=blueprint_dir or None,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            raise RPCError(result.stderr.strip() or f"Exit code {result.returncode}")
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except RPCError:
        raise
    except subprocess.TimeoutExpired:
        raise RPCError(f"Python file timed out: {script_path}")
    except Exception as e:
        raise RPCError(str(e))


@rpc_method
def bridge(params: dict[str, Any]) -> dict[str, Any]:
    command = params.get("command", "")
    args = params.get("args", {})
    blueprint_dir = params.get("blueprintDir", "")
    try:
        from orchestrator.bridge_cli import handle_command

        result = handle_command(command, args, blueprint_dir)
        return {"data": result}
    except Exception as e:
        raise RPCError(str(e))


@rpc_method
def solo_init(params: dict[str, Any]) -> dict[str, Any]:
    role = params.get("role", "solo")
    template = params.get("template", "solo-founder")
    blueprint_dir = params.get("blueprintDir", "")
    try:
        result = python_module(
            {
                "moduleName": "orchestrator.solo_init",
                "args": ["--role", role, "--template", template],
                "blueprintDir": blueprint_dir,
            }
        )
        return result
    except Exception as e:
        raise RPCError(str(e))


@rpc_method
def assistant_setup(params: dict[str, Any]) -> dict[str, Any]:
    blueprint_dir = params.get("blueprintDir", "")
    try:
        result = python_module(
            {
                "moduleName": "orchestrator.assistant_setup",
                "args": [],
                "blueprintDir": blueprint_dir,
            }
        )
        return result
    except Exception as e:
        raise RPCError(str(e))


@rpc_method
def assistant_verify(params: dict[str, Any]) -> dict[str, Any]:
    script_path = params.get("scriptPath", "")
    blueprint_dir = params.get("blueprintDir", "")
    try:
        result = python_file(
            {
                "scriptPath": script_path or "",
                "args": ["--verify"],
                "blueprintDir": blueprint_dir,
            }
        )
        return result
    except Exception as e:
        raise RPCError(str(e))


_launcher_process: Any = None


@rpc_method
def start_launcher(params: dict[str, Any]) -> dict[str, Any]:
    global _launcher_process
    blueprint_dir = params.get("blueprintDir", "")
    squad_id = params.get("squadId", "default")
    claw_role = params.get("clawRole", "solo")

    import subprocess

    from pathlib import Path

    launcher_script = str(Path(blueprint_dir) / "orchestrator" / "claw_launcher.py")

    if not os.path.exists(launcher_script):
        raise RPCError(f"claw_launcher.py not found at {launcher_script}")

    if _launcher_process and _launcher_process.poll() is None:
        return {"status": "already_running", "pid": _launcher_process.pid}

    env = {**os.environ}
    if blueprint_dir:
        env["PYTHONPATH"] = os.pathsep.join(
            [blueprint_dir, str(Path(blueprint_dir) / "orchestrator")]
        )
    env["MILIMO_SQUAD_ID"] = squad_id
    env["MILIMO_CLAW_ROLE"] = claw_role

    try:
        _launcher_process = subprocess.Popen(
            [sys.executable, launcher_script, "--all", "--daemon"],
            cwd=blueprint_dir or None,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"status": "started", "pid": _launcher_process.pid}
    except Exception as e:
        raise RPCError(f"Failed to start launcher: {e}")


@rpc_method
def stop_launcher(params: dict[str, Any]) -> dict[str, Any]:
    global _launcher_process
    if _launcher_process and _launcher_process.poll() is None:
        _launcher_process.terminate()
        try:
            _launcher_process.wait(timeout=10)
        except Exception:
            _launcher_process.kill()
            _launcher_process.wait()
        _launcher_process = None
        return {"status": "stopped"}
    return {"status": "not_running"}


@rpc_method
def collect_health(params: dict[str, Any]) -> dict[str, Any]:
    blueprint_dir = params.get("blueprintDir", "")
    squad_id = params.get("squadId", "default")
    try:
        result = python_module(
            {
                "moduleName": "orchestrator.bridge_cli",
                "args": [
                    "--command",
                    "collect_health",
                    "--args",
                    json.dumps({"squad_id": squad_id}),
                ],
                "blueprintDir": blueprint_dir,
            }
        )
        return {"result": result}
    except Exception as e:
        raise RPCError(str(e))


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------


class RPCHandler(BaseHTTPRequestHandler):
    server_version = "MilimoRPC/0.1"

    def do_POST(self):
        # Check if this is a War Room decision POST request
        # Path format: /v1/warroom/hold-queue/{action_id}/{decision}
        parts = self.path.strip("/").split("/")
        if len(parts) == 5 and parts[:3] == ["v1", "warroom", "hold-queue"]:
            action_id = parts[3]
            decision = parts[4]
            self._process_decision(action_id, decision)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id", 0)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error(-32700, "Parse error", 0)
            return

        if method == "ping":
            result = {"pong": True, "version": "0.1.0"}
            self._send_result(result, req_id)
            return

        handler = HANDLERS.get(method)
        if handler is None:
            self._send_error(-32601, f"Method not found: {method}", req_id)
            return

        try:
            result = handler(params)
            self._send_result(result, req_id)
        except RPCError as e:
            self._send_error(e.code, e.message, req_id)
        except Exception as e:
            logger.exception(f"Handler error: {method}")
            self._send_error(-32603, str(e), req_id)

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        elif self.path in ("/warroom.html", "/warroom"):
            self._serve_warroom_html()
        elif self.path == "/v1/warroom/claw-status":
            self._serve_claw_status()
        elif self.path == "/v1/warroom/hold-queue":
            self._serve_hold_queue()
        elif self.path == "/v1/warroom/cost-guard":
            self._serve_cost_guard()
        elif self.path == "/v1/warroom/last-updated":
            self._serve_last_updated()
        elif self.path == "/metrics":
            self._serve_metrics()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_warroom_html(self):
        # Look for warroom.html in orchestrator/
        html_path = Path(__file__).parent / "warroom.html"
        if not html_path.exists():
            html_path = Path(
                "/sandbox/.nemoclaw/blueprints/0.1.0/orchestrator/warroom.html"
            )
        if not html_path.exists():
            html_path = Path("/opt/hermes/warroom/warroom.html")

        if html_path.exists():
            html = html_path.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"warroom.html not found")

    def _serve_claw_status(self):
        try:
            from milimo_core.bridge_cli import handle_collect_health

            try:
                health = handle_collect_health({})
            except Exception as e:
                logger.warning(
                    "Could not collect health from bridge_cli, using stub: %s", e
                )
                health = {}

            html_parts = []
            for role in [
                "content",
                "ops",
                "analytics",
                "finance",
                "build",
                "assistant",
            ]:
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

    def _serve_hold_queue(self):
        try:
            from orchestrator.milimo_paths import mesh_dir as milimo_mesh_dir

            mesh_dir = milimo_mesh_dir()
            warroom_inbox = mesh_dir / "inbox" / "war_room"

            html_parts = []
            pending_files = []
            if warroom_inbox.exists():
                pending_files = sorted(
                    list(warroom_inbox.glob("*.json")), key=lambda f: f.stat().st_mtime
                )

            if not pending_files:
                html = '<div class="empty">No pending actions</div>'
            else:
                for msg_file in pending_files:
                    try:
                        msg_data = json.loads(msg_file.read_text(encoding="utf-8"))
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

                        is_hold = (
                            msg_type in ("spend_hold_decision", "hold_release")
                            or payload.get("mode") == "HOLD"
                        )
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
                        logger.warning(
                            "Failed to parse message file %s: %s", msg_file, fe
                        )

                html = (
                    "".join(html_parts)
                    if html_parts
                    else '<div class="empty">No pending actions</div>'
                )
            self._send_html(200, html)
        except Exception as e:
            logger.exception("Error serving hold queue")
            self._send_html(500, f"<div class='empty'>Error: {e}</div>")

    def _serve_cost_guard(self):
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

    def _serve_last_updated(self):
        from datetime import datetime

        self._send_html(200, datetime.now().strftime("%I:%M:%S %p"))

    def _process_decision(self, filename, decision):
        try:
            from orchestrator.milimo_paths import mesh_dir as milimo_mesh_dir

            mesh_dir = milimo_mesh_dir()
            warroom_inbox = mesh_dir / "inbox" / "war_room"
            filepath = warroom_inbox / filename

            if filepath.exists():
                msg_data = json.loads(filepath.read_text(encoding="utf-8"))

                if decision == "approve":
                    recipient = msg_data.get("recipient_role", "finance")
                    target_dir = mesh_dir / "inbox" / recipient
                    target_dir.mkdir(parents=True, exist_ok=True)
                    filepath.rename(target_dir / filename)
                    logger.info("Approved message %s: moved to %s", filename, recipient)
                elif decision == "veto":
                    rejected_dir = mesh_dir / "rejected"
                    rejected_dir.mkdir(parents=True, exist_ok=True)
                    filepath.rename(rejected_dir / filename)
                    logger.info("Vetoed message %s: moved to rejected", filename)

            self._serve_hold_queue()
        except Exception as e:
            logger.exception("Error processing decision")
            self._send_html(500, f"<div class='empty'>Error: {e}</div>")

    def _send_html(self, status: int, html: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_result(self, result: Any, req_id: int) -> None:
        response = json.dumps({"jsonrpc": "2.0", "result": result, "id": req_id})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode())

    def _send_error(self, code: int, message: str, req_id: int) -> None:
        response = json.dumps(
            {
                "jsonrpc": "2.0",
                "error": {"code": code, "message": message},
                "id": req_id,
            }
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode())

    def _serve_metrics(self) -> None:
        try:
            from orchestrator.metrics_collector import MetricsCollector

            lines = []

            # Add metric help and type headers
            lines.append(
                "# HELP milimo_messages_processed_total Total messages processed by the claw."
            )
            lines.append("# TYPE milimo_messages_processed_total counter")
            lines.append(
                "# HELP milimo_errors_total Total errors recorded by the claw."
            )
            lines.append("# TYPE milimo_errors_total counter")
            lines.append(
                "# HELP milimo_inference_calls_total Total inference API calls made by the claw."
            )
            lines.append("# TYPE milimo_inference_calls_total counter")
            lines.append(
                "# HELP milimo_inference_tokens_total Total tokens used by the claw in inference."
            )
            lines.append("# TYPE milimo_inference_tokens_total counter")
            lines.append(
                "# HELP milimo_sla_compliant_total Total SLA compliant messages."
            )
            lines.append("# TYPE milimo_sla_compliant_total counter")
            lines.append("# HELP milimo_sla_violation_total Total SLA violations.")
            lines.append("# TYPE milimo_sla_violation_total counter")

            for role in [
                "content",
                "ops",
                "analytics",
                "finance",
                "build",
                "assistant",
            ]:
                try:
                    collector = MetricsCollector(claw_role=role)
                    summary = collector.get_summary(lookback_hours=168)
                    counters = summary.get("counters", {})
                    timings = summary.get("timings", {})

                    # Global claw counters
                    lines.append(
                        f'milimo_messages_processed_total{{claw="{role}"}} {counters.get("messages_processed", 0)}'
                    )
                    lines.append(
                        f'milimo_errors_total{{claw="{role}"}} {counters.get("errors", 0)}'
                    )
                    lines.append(
                        f'milimo_inference_calls_total{{claw="{role}"}} {counters.get("inference_calls", 0)}'
                    )
                    lines.append(
                        f'milimo_inference_tokens_total{{claw="{role}"}} {counters.get("inference_tokens", 0)}'
                    )
                    lines.append(
                        f'milimo_sla_compliant_total{{claw="{role}"}} {counters.get("sla_compliant", 0)}'
                    )
                    lines.append(
                        f'milimo_sla_violation_total{{claw="{role}"}} {counters.get("sla_violation", 0)}'
                    )

                    # Breakdown by type/key
                    for key, val in counters.items():
                        if key.startswith("messages."):
                            msg_type = key[len("messages.") :]
                            lines.append(
                                f'milimo_messages_type_processed_total{{claw="{role}",message_type="{msg_type}"}} {val}'
                            )
                        elif key.startswith("errors."):
                            err_type = key[len("errors.") :]
                            lines.append(
                                f'milimo_errors_type_total{{claw="{role}",error_type="{err_type}"}} {val}'
                            )
                        elif key.startswith("inference."):
                            inf_type = key[len("inference.") :]
                            lines.append(
                                f'milimo_inference_type_calls_total{{claw="{role}",data_type="{inf_type}"}} {val}'
                            )

                    # Timing Gauges
                    for key, val in timings.items():
                        avg = val.get("avg_ms", 0.0)
                        p95 = val.get("p95_ms", 0.0)
                        if key.startswith("latency."):
                            msg_type = key[len("latency.") :]
                            lines.append(
                                f'milimo_latency_avg_ms{{claw="{role}",message_type="{msg_type}"}} {avg}'
                            )
                            lines.append(
                                f'milimo_latency_p95_ms{{claw="{role}",message_type="{msg_type}"}} {p95}'
                            )
                        elif key.startswith("inference_latency."):
                            inf_type = key[len("inference_latency.") :]
                            lines.append(
                                f'milimo_inference_latency_avg_ms{{claw="{role}",data_type="{inf_type}"}} {avg}'
                            )
                            lines.append(
                                f'milimo_inference_latency_p95_ms{{claw="{role}",data_type="{inf_type}"}} {p95}'
                            )

                except Exception as e:
                    logger.warning(
                        "Failed to collect metrics for claw role %s: %s", role, e
                    )

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(("\n".join(lines) + "\n").encode("utf-8"))
        except Exception as e:
            logger.exception("Error serving metrics")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(f"HTTP: {format % args}")


def run_server(port: int = RPC_PORT) -> None:
    server = HTTPServer(("127.0.0.1", port), RPCHandler)
    logger.info(f"Milimo RPC server listening on 127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    port = (
        int(sys.argv[sys.argv.index("--port") + 1])
        if "--port" in sys.argv
        else RPC_PORT
    )
    run_server(port)
