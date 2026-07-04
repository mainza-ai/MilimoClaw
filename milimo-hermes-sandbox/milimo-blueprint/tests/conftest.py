# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Shared test configuration and global fixtures.
"""

import os

os.environ.setdefault("MILIMO_ENV", "development")

import sys
import importlib
import pytest

# Pre-import orchestrator.build submodules and alias them as build.* in sys.modules
build_submodules = [
    "approval_handler",
    "build_claw",
    "build_init",
    "build_scheduler",
    "code_generator",
    "cost_monitor",
    "dependency_auditor",
    "deploy_manager",
    "doc_maintainer",
    "error_monitor",
    "issue_manager",
    "pr_manager",
    "sentry_client",
    "signal_dispatcher",
    "vercel_client",
]

# Alias build package itself
try:
    build_pkg = importlib.import_module("orchestrator.build")
    sys.modules["build"] = build_pkg
except ImportError:
    pass

for sub in build_submodules:
    try:
        mod = importlib.import_module(f"orchestrator.build.{sub}")
        sys.modules[f"build.{sub}"] = mod
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def mock_global_webhook_server(monkeypatch):
    """Globally mock OpsWebhookServer to prevent real socket binding in all unit/integration tests."""
    try:
        from orchestrator.ops.webhook_server import OpsWebhookServer

        monkeypatch.setattr(OpsWebhookServer, "start", lambda self: None)
        monkeypatch.setattr(OpsWebhookServer, "stop", lambda self: None)
    except ImportError:
        pass
