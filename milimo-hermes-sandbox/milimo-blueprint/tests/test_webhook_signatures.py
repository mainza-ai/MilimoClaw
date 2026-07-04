# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unit and integration tests for OpsWebhookServer signature verification and error bubbling."""

import hmac
import hashlib
import json
import os
import socket
import urllib.request
import urllib.error
import pytest
from unittest.mock import patch, MagicMock
from orchestrator.ops.webhook_server import OpsWebhookServer


def get_free_port() -> int:
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def webhook_server():
    """Start OpsWebhookServer on a random port in a background thread."""
    port = get_free_port()
    dispatcher = MagicMock()
    server = OpsWebhookServer(port=port, dispatcher=dispatcher, host="127.0.0.1")

    from http.server import HTTPServer
    import threading
    from milimo_core.ops.webhook_server import _WebhookHandler

    def real_start():
        if server._running:
            return
        with _WebhookHandler.buffer_lock:
            _WebhookHandler.alert_buffer.clear()
        _WebhookHandler.dispatcher = server.dispatcher
        _WebhookHandler.ops_claw = server.ops_claw

        server._server = HTTPServer((server.host, server.port), _WebhookHandler)
        server._running = True
        server._thread = threading.Thread(
            target=server._serve, daemon=True, name="ops-webhook"
        )
        server._thread.start()

    def real_stop():
        server._running = False
        if server._server:
            server._server.shutdown()
            server._server.server_close()
        if server._thread:
            server._thread.join(timeout=5)

    server.start = real_start
    server.stop = real_stop

    server.start()
    yield server
    server.stop()


def test_sentry_signature_verification(webhook_server):
    """Verify Sentry HMAC signature validation."""
    port = webhook_server.port
    url = f"http://127.0.0.1:{port}/webhook/sentry"
    payload = {"action": "created", "data": {"issue": {"title": "Test Error"}}}
    body = json.dumps(payload).encode("utf-8")

    # Set Sentry webhook secret
    with patch.dict(os.environ, {"SENTRY_WEBHOOK_SECRET": "sentry_secret_key"}):
        # 1. Invalid signature
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("sentry-hook-signature", "wrong_signature")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.status == 401

        # 2. Valid signature
        sig = hmac.new(b"sentry_secret_key", body, hashlib.sha256).hexdigest()
        req2 = urllib.request.Request(url, data=body, method="POST")
        req2.add_header("Content-Type", "application/json")
        req2.add_header("sentry-hook-signature", sig)
        resp = urllib.request.urlopen(req2)
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "received"


def test_webhook_error_bubbling(webhook_server):
    """Verify that exceptions during incident dispatch return HTTP 500."""
    port = webhook_server.port
    url = f"http://127.0.0.1:{port}/webhook/generic"
    payload = {"title": "Generic Test"}
    body = json.dumps(payload).encode("utf-8")

    # Force dispatcher to raise an error
    webhook_server.dispatcher.handle_incident.side_effect = Exception("Database is down")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.status == 500
    resp_body = json.loads(exc.value.read().decode())
    assert "Database is down" in resp_body["error"]
