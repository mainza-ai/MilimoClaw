#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
assistant_setup.py — Renders and installs the Milimo Claw assistant system prompt.

Reads assistant config from ~/.milimo/config.json.
Renders MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md with squad values.
Writes rendered prompt to .openclaw/agents/main/system.md.

Run after onboarding:
    python milimo-blueprint/orchestrator/assistant_setup.py

Or via CLI:
    milimo assistant setup
    milimo assistant verify
    milimo assistant start
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


# Template search paths — tried in order
_TEMPLATE_CANDIDATES = [
    # 1. Relative to CWD (development on host)
    Path("milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"),
    # 2. Relative to this script's directory (plugin bundled copy)
    Path(__file__).resolve().parent.parent / "docs" / "MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md",
    # 3. Home-relative (sandbox deployment)
    Path.home() / ".milimo" / "MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md",
]
MILIMO_CONFIG_PATH = Path.home() / ".milimo" / "config.json"
# Use home-relative path so it works for both root and sandbox users
OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents" / "main"
SYSTEM_PROMPT_DEST = OPENCLAW_AGENTS_DIR / "system.md"
AGENT_CONFIG_DEST = OPENCLAW_AGENTS_DIR / "config.yaml"


def find_template() -> Path:
    """Find the assistant system prompt template from multiple candidate paths."""
    for candidate in _TEMPLATE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"System prompt template not found. Searched:\n"
        + "\n".join(f"  - {p}" for p in _TEMPLATE_CANDIDATES)
        + "\nCopy MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md to ~/.milimo/"
    )


@dataclass
class AssistantConfig:
    name: str
    creature: str
    vibe: str
    emoji: str
    operator_name: str
    squad_name: str
    template_name: str
    active_claws: list[str]


TEMPLATE_CLAW_MAP: dict[str, list[str]] = {
    "solo-founder": ["content", "ops", "analytics", "finance", "build"],
    "content-agency": ["content", "ops", "analytics"],
    "design-studio": ["content", "ops", "finance"],
    "event-promotion": ["content", "ops", "analytics"],
    "freelance-collective": ["ops", "analytics", "finance"],
    "ai-micro-saas": ["build", "ops", "analytics", "finance"],
    "campus-ai-tool": ["build", "content", "ops"],
}


def load_assistant_config() -> AssistantConfig:
    """
    Load assistant configuration from ~/.milimo/config.json.

    Raises FileNotFoundError if config doesn't exist.
    Raises ValueError if required fields are missing.
    """
    if not MILIMO_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Milimo config not found at {MILIMO_CONFIG_PATH}\n"
            "Run onboarding first: milimo onboard"
        )

    config = json.loads(MILIMO_CONFIG_PATH.read_text(encoding="utf-8"))
    assistant = config.get("assistant", {})

    if not assistant.get("name"):
        raise ValueError(
            "Assistant name not configured.\n"
            "Run onboarding to set your assistant's name: milimo onboard"
        )

    template_name = config.get("template", "solo-founder")
    active_claws = TEMPLATE_CLAW_MAP.get(
        template_name, ["content", "ops", "analytics", "finance", "build"]
    )

    return AssistantConfig(
        name=assistant.get("name", "Assistant"),
        creature=assistant.get("creature", "a claw"),
        vibe=assistant.get("vibe", "sharp and unhurried"),
        emoji=assistant.get("emoji", "🦀"),
        operator_name=config.get("operatorName", "Operator"),
        squad_name=config.get("squadName", "my-squad"),
        template_name=template_name,
        active_claws=active_claws,
    )


def render_template(config: AssistantConfig) -> str:
    """
    Render the system prompt template by substituting all placeholders.

    Uses simple str.replace() — no third-party templating required.
    """
    template_path = find_template()
    template = template_path.read_text(encoding="utf-8")

    substitutions = {
        "{{assistant_name}}": config.name,
        "{{creature}}": config.creature,
        "{{vibe}}": config.vibe,
        "{{emoji}}": config.emoji,
        "{{operator_name}}": config.operator_name,
        "{{squad_name}}": config.squad_name,
        "{{template_name}}": config.template_name,
        "{{active_claws}}": ", ".join(config.active_claws),
    }

    rendered = template
    for placeholder, value in substitutions.items():
        rendered = rendered.replace(placeholder, value)

    remaining = [p for p in substitutions if p in rendered]
    if remaining:
        raise ValueError(
            f"Template render incomplete. Unsubstituted placeholders: {remaining}"
        )

    return rendered


def build_agent_config(config: AssistantConfig) -> dict:
    """Build the .openclaw/agents/main/config.yaml content."""
    return {
        "agent": {
            "name": config.name,
            "emoji": config.emoji,
            "version": "1.0",
            "runtime": "local",
            "system_prompt": "system.md",
            "description": f"Milimo Claw conversational squad interface for {config.squad_name}",
        },
        "identity": {
            "creature": config.creature,
            "vibe": config.vibe,
            "signature_emoji": config.emoji,
        },
        "bridge": {
            "python_path": "milimo-blueprint/orchestrator/bridge_cli.py",
            "timeout_seconds": 3,
            "spawn_args": ["python3", "milimo-blueprint/orchestrator/bridge_cli.py"],
        },
        "session": {
            "auto_load_squad_status": True,
            "status_on_start": True,
        },
        "squad": {
            "name": config.squad_name,
            "template": config.template_name,
            "active_claws": config.active_claws,
            "operator": config.operator_name,
        },
    }


def setup_assistant() -> None:
    """
    Render the system prompt template and install into NemoClaw runtime.

    Safe to run multiple times — overwrites cleanly.
    """
    print("Loading assistant config...")
    config = load_assistant_config()

    print(f"Rendering system prompt for {config.name}...")
    rendered = render_template(config)

    OPENCLAW_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEM_PROMPT_DEST.write_text(rendered, encoding="utf-8")
    print(f"✓ System prompt installed: {SYSTEM_PROMPT_DEST}")

    agent_config = build_agent_config(config)
    with open(AGENT_CONFIG_DEST, "w", encoding="utf-8") as f:
        yaml.dump(agent_config, f, default_flow_style=False, allow_unicode=True)
    print(f"✓ Agent config written: {AGENT_CONFIG_DEST}")

    print()
    print(f"{config.name} is ready. Start with:")
    print("    openclaw agent --agent main")
    print("    — or —")
    print("    milimo assistant start")
    print()
    print(f"The milimo never stops. {config.emoji}")


def verify_setup() -> dict[str, bool]:
    """Verify assistant setup is complete. Returns check_name → passed."""
    try:
        config = load_assistant_config()
        config_loaded = True
        config_has_name = bool(config.name)
    except Exception:
        config_loaded = False
        config_has_name = False

    try:
        template_found = find_template().exists()
    except FileNotFoundError:
        template_found = False

    return {
        "milimo_config_exists": MILIMO_CONFIG_PATH.exists(),
        "assistant_config_loaded": config_loaded,
        "assistant_has_name": config_has_name,
        "template_exists": template_found,
        "system_prompt_installed": SYSTEM_PROMPT_DEST.exists(),
        "agent_config_exists": AGENT_CONFIG_DEST.exists(),
        "bridge_cli_exists": Path("milimo-blueprint/orchestrator/bridge_cli.py").exists(),
    }


if __name__ == "__main__":
    if "--verify" in sys.argv:
        results = verify_setup()
        all_passed = all(results.values())
        for check, passed in results.items():
            print(f"    {'✓' if passed else '✗'} {check}")
        sys.exit(0 if all_passed else 1)
    else:
        setup_assistant()
