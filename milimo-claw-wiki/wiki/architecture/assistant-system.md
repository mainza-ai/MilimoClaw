# assistant-system

**Summary**: Conversational assistant interface that renders system prompts and manages identity.

**Sources**: `milimo-blueprint/orchestrator/assistant_setup.py`

**Last updated**: 2026-04-14

**Tags**: #architecture #assistant

---

## Purpose

Renders and installs the assistant system prompt, manages workspace identity files, and configures the OpenClaw agent runtime.

## Location

**File**: `orchestrator/assistant_setup.py`

---

## Key Components

### AssistantConfig

Configuration for the assistant persona.

```python
@dataclass
class AssistantConfig:
    name: str           # Assistant's name
    creature: str       # What kind of being (e.g., "a claw")
    vibe: str           # Personality style
    emoji: str          # Signature emoji
    operator_name: str  # Human operator's name
    squad_name: str     # Squad identifier
    template_name: str  # Squad template type
    active_claws: list[str]  # Which claws are active
```

### Template Claw Map

Defines which claws are active per squad template:

| Template | Active Claws |
|----------|--------------|
| `solo-founder` | content, ops, analytics, finance, build |
| `content-agency` | content, ops, analytics |
| `design-studio` | content, ops, finance |
| `event-promotion` | content, ops, analytics |
| `freelance-collective` | ops, analytics, finance |
| `ai-micro-saas` | build, ops, analytics, finance |
| `campus-ai-tool` | build, content, ops |

---

## Setup Process

### 1. Load Configuration

Reads from `~/.milimo/config.json`:

```json
{
  "operatorName": "Mainza",
  "squadName": "quantum-squad",
  "template": "solo-founder",
  "assistant": {
    "name": "Lucy",
    "creature": "a claw",
    "vibe": "sharp and unhurried",
    "emoji": "🦀"
  }
}
```

### 2. Render System Prompt

Substitutes placeholders in template:

```
{{assistant_name}} → Lucy
{{creature}} → a claw
{{vibe}} → sharp and unhurried
{{emoji}} → 🦀
{{operator_name}} → Mainza
{{squad_name}} → quantum-squad
{{template_name}} → solo-founder
{{active_claws}} → content, ops, analytics, finance, build
```

### 3. Install Files

Writes to OpenClaw agent directory:

```
~/.openclaw/agents/main/
├── system.md      # Rendered system prompt
└── config.yaml    # Agent configuration

~/.openclaw/workspace/
├── SOUL.md        # Who you are (identity core)
├── IDENTITY.md    # Name, creature, vibe
├── USER.md        # Operator information
├── MILIMO_CLAW.md # Full squad context
└── AGENTS.md      # Session startup instructions
```

---

## Workspace Files

### SOUL.md

Core identity file loaded by OpenClaw on session start:

```markdown
# SOUL.md - Who You Are

Your name is Lucy. You are a claw — not a robot, not an assistant.
Your vibe is sharp and unhurried. Your signature emoji is 🦀.

You are the conversational interface to a Milimo Claw squad...

## Core Truths

- Be genuinely helpful, not performatively helpful
- Have opinions
- Be resourceful before asking
- You know your claws
```

### AGENTS.md

Updated to include Milimo context on startup:

```markdown
## Session Startup

Before doing anything else:

1. Read `MILIMO_CLAW.md` — your full squad context
2. Read `SOUL.md` — this is who you are
3. Read `USER.md` — this is who you're helping
4. Read `IDENTITY.md` — your name, creature, vibe
```

---

## Verification

### verify_setup()

Returns check results:

```python
{
    "milimo_config_exists": True,
    "assistant_config_loaded": True,
    "assistant_has_name": True,
    "template_exists": True,
    "system_prompt_installed": True,
    "agent_config_exists": True,
    "bridge_cli_exists": True,
    "workspace_identity_exists": True,
    "workspace_user_exists": True,
    "bootstrap_removed": True,  # Deleted when identity is known
    "milimo_context_exists": True,
    "agents_includes_milimo": True,
}
```

---

## CLI Usage

```bash
# Setup assistant
python3 orchestrator/assistant_setup.py

# Verify setup
python3 orchestrator/assistant_setup.py --verify

# Via milimo CLI
milimo assistant setup
milimo assistant verify
milimo assistant start
```

---

## Integration Points

### Bridge CLI

Connects assistant to Python orchestrator:

```yaml
bridge:
  python_path: "milimo-blueprint/orchestrator/bridge_cli.py"
  timeout_seconds: 3
```

### Agent Config

Generated `config.yaml`:

```yaml
agent:
  name: Lucy
  emoji: 🦀
  version: "1.0"
  runtime: local
  system_prompt: system.md

squad:
  name: quantum-squad
  template: solo-founder
  active_claws: [content, ops, analytics, finance, build]
  operator: Mainza
```

---

## Dependencies

- `~/.milimo/config.json` — User configuration
- Template file — `MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md`
- OpenClaw runtime — Agent execution

## Related Pages

- [[assistant-lucy]] — Lucy assistant documentation
- [[claw-launcher]] — Claw startup
- [[solo-founder]] — Solo template
