#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Wrapper for claw_launcher.py that bootstraps env vars from gateway config.
No hardcoded model/provider names.
"""

import os
import sys
import subprocess

# Bootstrap env from gateway config before launching
CONFIG_PATH = "/sandbox/.openclaw/openclaw.json"
if os.path.exists(CONFIG_PATH):
    import json

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    # Read model from models.providers.<provider>.models[0]
    models_providers = cfg.get("models", {}).get("providers", {})
    for prov in models_providers.values():
        for m in prov.get("models", []):
            name = m.get("name") or m.get("id")
            if name:
                os.environ.setdefault("NEMOCLAW_MODEL", name)
                break
        if os.environ.get("NEMOCLAW_MODEL"):
            break

    # Also check agents.defaults.model.primary
    if not os.environ.get("NEMOCLAW_MODEL"):
        primary = (
            cfg.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")
        )
        if primary:
            os.environ["NEMOCLAW_MODEL"] = primary

    # Read base URL
    for prov in models_providers.values():
        base = prov.get("baseUrl")
        if base:
            base = base.rstrip("/")
            os.environ.setdefault("NEMOCLAW_INFERENCE_BASE_URL", base)
            os.environ.setdefault("NVIDIA_API_BASE", base)
            break

    if os.environ.get("NEMOCLAW_MODEL"):
        print(
            f"[bootstrap] NEMOCLAW_MODEL={os.environ['NEMOCLAW_MODEL']}",
            file=sys.stderr,
        )
    if os.environ.get("NEMOCLAW_INFERENCE_BASE_URL"):
        print(
            f"[bootstrap] base={os.environ['NEMOCLAW_INFERENCE_BASE_URL']}",
            file=sys.stderr,
        )

# Launch the real claw_launcher with all args
launcher = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claw_launcher.py")
sys.exit(subprocess.call([sys.executable, launcher] + sys.argv[1:]))
