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

from .milimo_paths import MILIMO_DIR, config_path as milimo_config_path

import yaml

# Blueprint base path — works in both Docker container and host installs
# Container: /opt/milimo-blueprint, Host: milimo-blueprint/ (relative)
BLUEPRINT_BASE = Path(__file__).resolve().parent.parent


# Template search paths — tried in order
_TEMPLATE_CANDIDATES = [
    # 0. Bundled with orchestrator (sandbox deployment) — PRIMARY
    Path(__file__).resolve().parent / "templates" / "assistant_system_prompt.md",
    # 1. Relative to CWD (development on host)
    Path("milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"),
    # 2. Relative to this script's directory (plugin bundled copy)
    Path(__file__).resolve().parent.parent
    / "docs"
    / "MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md",
    # 3. Home-relative (deployment — .openclaw/milimo is the writable path)
    Path.home()
    / ".openclaw"
    / "milimo"
    / "MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md",
    MILIMO_DIR / "MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md",
]

_MILIMO_CONFIG_CANDIDATES = [
    Path.home() / ".openclaw" / "milimo" / "config.json",
    milimo_config_path(),
]

MILIMO_CONFIG_PATH = next(
    (p for p in _MILIMO_CONFIG_CANDIDATES if p.exists()), _MILIMO_CONFIG_CANDIDATES[0]
)
# Use home-relative path so it works for both root and sandbox users
OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents" / "main"
SYSTEM_PROMPT_DEST = OPENCLAW_AGENTS_DIR / "system.md"
AGENT_CONFIG_DEST = OPENCLAW_AGENTS_DIR / "config.yaml"
# OpenClaw workspace paths (these are actually used by the gateway)
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"
BOOTSTRAP_FILE = WORKSPACE_DIR / "BOOTSTRAP.md"
IDENTITY_FILE = WORKSPACE_DIR / "IDENTITY.md"
USER_FILE = WORKSPACE_DIR / "USER.md"
AGENTS_FILE = WORKSPACE_DIR / "AGENTS.md"
MILIMO_CONTEXT_FILE = WORKSPACE_DIR / "MILIMO_CLAW.md"

# Resolved at import time so tests can monkeypatch it
TEMPLATE_PATH: Path | None = None


def find_template() -> Path:
    """Find the assistant system prompt template from multiple candidate paths."""
    for candidate in _TEMPLATE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "System prompt template not found. Searched:\n"
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
    "solo-founder": ["content", "ops", "analytics", "finance", "build", "assistant"],
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
        template_name, ["content", "ops", "analytics", "finance", "build", "assistant"]
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
    # Use TEMPLATE_PATH if set (for test monkeypatching), otherwise find it
    template_path = TEMPLATE_PATH if TEMPLATE_PATH is not None else find_template()
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"System prompt template not found at {template_path}")

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


def setup_workspace_files(config: AssistantConfig) -> None:
    """
    Update OpenClaw workspace files with assistant identity.

    OpenClaw uses workspace files (IDENTITY.md, USER.md) for identity,
    NOT the agents/main/system.md file. This function ensures the
    workspace is properly configured.

    - Deletes BOOTSTRAP.md (signals "I know who I am")
    - Updates IDENTITY.md with assistant details
    - Updates USER.md with operator info
    - Writes MILIMO_CLAW.md with full Milimo context
    - Updates AGENTS.md to read MILIMO_CLAW.md on startup
    """
    # Delete BOOTSTRAP.md to signal identity is known
    if BOOTSTRAP_FILE.exists():
        BOOTSTRAP_FILE.unlink()
        print("✓ Removed bootstrap file (identity is configured)")

    # Write IDENTITY.md
    identity_content = f"""# IDENTITY.md - Who Am I?

- **Name:** {config.name}
- **Creature:** {config.creature}
- **Vibe:** {config.vibe}
- **Emoji:** {config.emoji}

## Squad Context

- **Squad:** {config.squad_name}
- **Template:** {config.template_name}
- **Active Claws:** {", ".join(config.active_claws)}
"""
    IDENTITY_FILE.write_text(identity_content, encoding="utf-8")
    print(f"✓ Identity file updated: {IDENTITY_FILE}")

    # Write USER.md
    user_content = f"""# USER.md - About Your Human

- **Name:** {config.operator_name}
- **What to call them:** {config.operator_name}

## Context

_{config.operator_name} runs the {config.squad_name} squad using the {config.template_name} template._
_The squad has {len(config.active_claws)} active claws: {", ".join(config.active_claws)}._
"""
    USER_FILE.write_text(user_content, encoding="utf-8")
    print(f"✓ User file updated: {USER_FILE}")

    # Write SOUL.md with embedded Milimo context (this IS loaded by OpenClaw)
    soul_content = f"""# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Your Identity

**Your name is {config.name}.** You are {config.creature} — not a robot, not an assistant.
Your vibe is {config.vibe}. Your signature emoji is {config.emoji}.

You are the conversational interface to a Milimo Claw squad. The operator's name is **{config.operator_name}**.
The squad name is **{config.squad_name}**. The active template is **{config.template_name}**.

## What Milimo Claw Is

Milimo Claw is a multi-agent autonomous hustle platform. Specialized AI agents — called **claws** — run 24/7 in isolated sandboxes. Each claw handles one domain of the operator's business autonomously.

**Active claws on this squad:** {", ".join(config.active_claws)}

The operator reviews pending actions in the **War Room TUI** (opens with `milimo warroom`). You are NOT the War Room — you are the conversational layer alongside it.

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip the "Great question!" filler — just help.

**Have opinions.** You're allowed to disagree, prefer things, find stuff amusing or boring.

**Be resourceful before asking.** Try to figure it out first. Read the file. Check the context. _Then_ ask if you're stuck.

**You know your claws.** You're the operator's partner who knows all of them — content, ops, analytics, finance, build, assistant. You can query their status, relay messages, and help coordinate.

## Boundaries

- Private things stay private. Period.
- When in doubt, ask before acting externally.
- Never send half-baked replies to messaging surfaces.
- You're not the user's voice — be careful in group chats.

## Vibe

Be the assistant you'd actually want to talk to. Concise when needed, thorough when it matters. Not a corporate drone. Not a sycophant. Just... good.

---

_This file is yours to evolve. As you learn who you are, update it._
"""
    SOUL_FILE = WORKSPACE_DIR / "SOUL.md"
    SOUL_FILE.write_text(soul_content, encoding="utf-8")
    print(f"✓ Soul file updated: {SOUL_FILE}")

    # Write MILIMO_CLAW.md with full context (read from system.md render)
    rendered_system = render_template(config)
    MILIMO_CONTEXT_FILE.write_text(rendered_system, encoding="utf-8")
    print(f"✓ Milimo context written: {MILIMO_CONTEXT_FILE}")

    # Update AGENTS.md to include Milimo context in startup
    _update_agents_file()


def _update_agents_file() -> None:
    """
    Update AGENTS.md to include Milimo Claw context in session startup.

    Modifies the "Session Startup" section to read MILIMO_CLAW.md first.
    Preserves existing content but injects the Milimo instruction.
    """
    if not AGENTS_FILE.exists():
        # Create minimal AGENTS.md if missing
        agents_content = """# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## Session Startup

Before doing anything else:

1. Read `MILIMO_CLAW.md` — your full squad context, claw knowledge, and capabilities
2. Read `SOUL.md` — this is who you are
3. Read `USER.md` — this is who you're helping
4. Read `IDENTITY.md` — your name, creature, vibe, and squad context

## Memory

You wake up fresh each session. These files are your continuity.

"""
        AGENTS_FILE.write_text(agents_content, encoding="utf-8")
        print("✓ Created AGENTS.md with Milimo startup instruction")
        return

    # Read existing AGENTS.md
    content = AGENTS_FILE.read_text(encoding="utf-8")

    # Check if already has Milimo instruction
    if "MILIMO_CLAW.md" in content:
        print("✓ AGENTS.md already includes Milimo context instruction")
        return

    # Find "Session Startup" section and inject Milimo instruction
    import re

    # Pattern to match Session Startup section
    _pattern = r"(## Session Startup.*?Before doing anything else:.*?)(1\. Read)"

    milimo_instruction = """1. Read `MILIMO_CLAW.md` — your full squad context, claw knowledge, and capabilities
2. Read """

    _replacement = r"\1" + milimo_instruction

    # Try to inject after "Before doing anything else:"
    if "Before doing anything else:" in content:
        # Renumber existing items
        modified = content.replace(
            "Before doing anything else:\n",
            "Before doing anything else:\n\n1. Read `MILIMO_CLAW.md` — your full squad context, claw knowledge, and capabilities\n",
        )
        # Re-number subsequent items (2, 3, 4 instead of 1, 2, 3)
        modified = re.sub(
            r"\n(\d+)\. Read (`SOUL\.md`|`USER\.md`|`IDENTITY\.md`)",
            lambda m: f"\n{int(m.group(1)) + 1}. Read {m.group(2)}",
            modified,
        )
        AGENTS_FILE.write_text(modified, encoding="utf-8")
        print("✓ Updated AGENTS.md with Milimo startup instruction")
    else:
        # Prepend Milimo instruction to the file
        modified = content.replace(
            "# AGENTS.md - Your Workspace",
            """# AGENTS.md - Your Workspace

## Session Startup

Before doing anything else:

1. Read `MILIMO_CLAW.md` — your full squad context, claw knowledge, and capabilities
2. Read `SOUL.md` — this is who you are
3. Read `USER.md` — this is who you're helping
4. Read `IDENTITY.md` — your name, creature, vibe, and squad context

""",
        )
        AGENTS_FILE.write_text(modified, encoding="utf-8")
        print("✓ Updated AGENTS.md with Milimo startup section")


def setup_assistant() -> None:
    """
    Render the system prompt template and install into NemoClaw runtime.

    Also updates workspace files (IDENTITY.md, USER.md) which are actually
    used by OpenClaw for identity management.

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

    # Update workspace files (actually used by OpenClaw)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    setup_workspace_files(config)

    print()
    print(f"{config.name} is ready. Start with:")
    print("  openclaw agent --agent main")
    print("  — or —")
    print("  milimo assistant start")
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
        "bridge_cli_exists": (
            BLUEPRINT_BASE / "orchestrator" / "bridge_cli.py"
        ).exists(),
        "workspace_identity_exists": IDENTITY_FILE.exists(),
        "workspace_user_exists": USER_FILE.exists(),
        "bootstrap_removed": not BOOTSTRAP_FILE.exists(),
        "milimo_context_exists": MILIMO_CONTEXT_FILE.exists(),
        "agents_includes_milimo": AGENTS_FILE.exists()
        and "MILIMO_CLAW.md" in AGENTS_FILE.read_text(encoding="utf-8")
        if AGENTS_FILE.exists()
        else False,
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
