> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — ASSISTANT SETUP + ONBOARDING WIZARD UPDATE PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md  (the parameterized template)
#   2. MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md             (solo template ground truth)
#   3. AGENTS.md                                         (system context)
#   4. The current onboarding wizard documentation       (attached — existing impl)
#   5. commands/onboard.ts                               (existing wizard — EXISTS)
#   6. commands/init.ts                                  (existing init — EXISTS)
#   7. onboard/config.ts                                 (config manager — EXISTS)
#   8. onboard/validate.ts                               (validators — EXISTS)
#   9. onboard/template.ts                               (template discovery — EXISTS)
#   10. onboard/prompt.ts                                (prompt utilities — EXISTS)
#   11. bridge_cli.py                                    (Python bridge — EXISTS)
#   12. lucy_setup.py or assistant_setup.py              (if it exists)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert TypeScript and Python engineer implementing two related
things in the Milimo Claw codebase:

1. Update the assistant setup system so the NemoClaw agent runtime prompt
   is generated from a parameterized template rather than a hardcoded file.
   The operator names their own assistant during onboarding — it is never
   hardcoded to "Lucy" or any other name.

2. Update the onboarding wizard to align with the full Milimo Claw spec —
   adding the assistant persona step, fixing the template list, adding
   squad assistant config to the config schema, and ensuring the wizard
   produces a complete config that enables Lucy (or any named assistant)
   to start immediately after onboarding completes.

Read this entire prompt before writing any code.

---

## CONTEXT

The current onboarding wizard (documented in the attached report) has the
right structure but several gaps relative to the spec:

**What currently works correctly:**
  - NemoClaw dependency check (Step 0)
  - Existing config detection and reconfiguration (Step 1)
  - Squad name input and validation (Step 4)
  - Operator name input (Step 6)
  - War Room mode selection (Step 7)
  - Mesh secret generation (Step 8)
  - Configuration save and directory structure (Step 11)
  - Migration from state.json to config.json (legacy)

**What needs to be added or fixed:**

  1. Template list is incomplete — spec defines 7 templates, wizard shows 5
  2. Assistant persona step is missing entirely — operator cannot name
     their assistant during onboarding
  3. Config schema missing `assistant` block
  4. After onboarding, assistant setup must run automatically so the operator
     can start their agent immediately with `milimo assistant start`
  5. The `init` quick-setup command does not set assistant config
  6. `commands/lucy.ts` is named for Lucy specifically — must be renamed
     to `commands/assistant.ts` and generalized

---

## DEVELOPMENT CONSTRAINTS

- TypeScript strict mode, full type annotations, no `any`
- Python 3.11+, full type hints, pathlib.Path only
- yaml.safe_load() only
- No hardcoded assistant names anywhere in the codebase
- The template renders `{{placeholder}}` syntax using Python's str.replace()
  — no third-party templating library required
- Tests: Jest for TypeScript, pytest for Python

---

## PART 1 — PARAMETERIZED ASSISTANT SETUP

### TASK 1.1 — Rename and rewrite assistant_setup.py

**Rename:** `lucy_setup.py` → `milimo-blueprint/orchestrator/assistant_setup.py`

The new version reads assistant config from `~/.milimo/config.json` and
renders the system prompt template before writing it. It is no longer a
static file copy.

```python
"""
assistant_setup.py — Renders and installs the Milimo Claw assistant
system prompt into the NemoClaw agent runtime.

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
import json
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass

import yaml  # yaml.safe_load only


TEMPLATE_PATH = Path(
    "milimo-claw-docs/reference/"
    "MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"
)
MILIMO_CONFIG_PATH = Path.home() / ".milimo" / "config.json"
OPENCLAW_AGENTS_DIR = Path(".openclaw") / "agents" / "main"
SYSTEM_PROMPT_DEST = OPENCLAW_AGENTS_DIR / "system.md"
AGENT_CONFIG_DEST = OPENCLAW_AGENTS_DIR / "config.yaml"


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


# Template names and their active claw sets — must match solo-founder.yaml
TEMPLATE_CLAW_MAP: dict[str, list[str]] = {
"solo-founder": ["content", "ops", "analytics", "finance", "build", "assistant"],
    "content-agency":      ["content", "ops", "analytics"],
    "design-studio":       ["content", "ops", "finance"],
    "event-promotion":     ["content", "ops", "analytics"],
    "freelance-collective": ["ops", "analytics", "finance"],
    "ai-micro-saas":       ["build", "ops", "analytics", "finance"],
    "campus-ai-tool":      ["build", "content", "ops"],
}


def load_assistant_config() -> AssistantConfig:
    """
    Load assistant configuration from ~/.milimo/config.json.
    Raises FileNotFoundError if config doesn't exist.
    Raises ValueError if required fields are missing.
    """
    if not MILIMO_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Milimo config not found at {MILIMO_CONFIG_PATH}
"
            "Run onboarding first: milimo onboard"
        )

    config = json.loads(MILIMO_CONFIG_PATH.read_text(encoding="utf-8"))

    assistant = config.get("assistant", {})
    if not assistant.get("name"):
        raise ValueError(
            "Assistant name not configured.
"
            "Run onboarding to set your assistant's name: milimo onboard"
        )

    template_name = config.get("template", "solo-founder")
    active_claws = TEMPLATE_CLAW_MAP.get(
        template_name,
        ["content", "ops", "analytics", "finance", "build", "assistant"]
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
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"System prompt template not found at {TEMPLATE_PATH}
"
            "Ensure MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md is "
            "in milimo-claw-docs/reference/"
        )

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    substitutions = {
        "{{assistant_name}}": config.name,
        "{{creature}}":       config.creature,
        "{{vibe}}":           config.vibe,
        "{{emoji}}":          config.emoji,
        "{{operator_name}}":  config.operator_name,
        "{{squad_name}}":     config.squad_name,
        "{{template_name}}":  config.template_name,
        "{{active_claws}}":   ", ".join(config.active_claws),
    }

    rendered = template
    for placeholder, value in substitutions.items():
        rendered = rendered.replace(placeholder, value)

    # Verify all placeholders were substituted
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
        }
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

    return {
        "milimo_config_exists":    MILIMO_CONFIG_PATH.exists(),
        "assistant_config_loaded": config_loaded,
        "assistant_has_name":      config_has_name,
        "template_exists":         TEMPLATE_PATH.exists(),
        "system_prompt_installed": SYSTEM_PROMPT_DEST.exists(),
        "agent_config_exists":     AGENT_CONFIG_DEST.exists(),
        "bridge_cli_exists":       Path(
            "milimo-blueprint/orchestrator/bridge_cli.py"
        ).exists(),
    }


if __name__ == "__main__":
    if "--verify" in sys.argv:
        results = verify_setup()
        all_passed = all(results.values())
        for check, passed in results.items():
            print(f"  {'✓' if passed else '✗'} {check}")
        sys.exit(0 if all_passed else 1)
    else:
        setup_assistant()
```

**Write pytest tests:**
- `load_assistant_config()` reads name/creature/vibe/emoji from config correctly
- `load_assistant_config()` raises FileNotFoundError when config missing
- `load_assistant_config()` raises ValueError when assistant.name is empty
- `render_template()` substitutes all 8 placeholders correctly
- `render_template()` raises ValueError if any placeholder remains unsubstituted
- `render_template()` raises FileNotFoundError if template missing
- `setup_assistant()` writes system.md with correct content
- `setup_assistant()` writes config.yaml with correct agent name
- `setup_assistant()` is idempotent — safe to run twice
- `verify_setup()` returns all True after successful setup
- active_claws correct for each of the 7 template names

---

### TASK 1.2 — Rename commands/lucy.ts → commands/assistant.ts

**Delete:** `milimo/src/commands/lucy.ts`
**Create:** `milimo/src/commands/assistant.ts`

Same functionality as before but generalized — no reference to "Lucy":

```typescript
/**
 * milimo assistant setup  — renders and installs the assistant system prompt
 * milimo assistant verify — checks assistant is correctly configured
 * milimo assistant start  — starts the assistant in NemoClaw terminal
 */
import { spawn } from "child_process";
import { existsSync } from "fs";
import { readFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";

interface AssistantConfig {
  name: string;
  emoji: string;
}

function getAssistantConfig(): AssistantConfig | null {
  const configPath = join(homedir(), ".milimo", "config.json");
  try {
    const config = JSON.parse(readFileSync(configPath, "utf-8"));
    const assistant = config?.assistant;
    if (assistant?.name) {
      return { name: assistant.name, emoji: assistant.emoji || "🦀" };
    }
    return null;
  } catch {
    return null;
  }
}

export async function assistantSetup(): Promise<void> {
  console.log("Setting up squad assistant...
");

  const result = spawn("python3", [
    "milimo-blueprint/orchestrator/assistant_setup.py"
  ], { stdio: "inherit" });

  return new Promise((resolve, reject) => {
    result.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Assistant setup failed with exit code ${code}`));
    });
  });
}

export async function assistantVerify(): Promise<void> {
  const result = spawn("python3", [
    "milimo-blueprint/orchestrator/assistant_setup.py",
    "--verify"
  ], { stdio: "inherit" });

  return new Promise((resolve, reject) => {
    result.on("close", (code) => {
      const assistant = getAssistantConfig();
      if (code === 0) {
        const name = assistant?.name ?? "your assistant";
        console.log(`
${name} setup is complete.`);
        console.log("Start with: milimo assistant start");
        resolve();
      } else {
        console.error("
Assistant setup incomplete. Run: milimo assistant setup");
        reject(new Error("Assistant setup verification failed"));
      }
    });
  });
}

export async function assistantStart(): Promise<void> {
  const agentConfig = ".openclaw/agents/main/config.yaml";

  if (!existsSync(agentConfig)) {
    console.error("Assistant not set up. Run: milimo assistant setup");
    process.exit(1);
  }

  const assistant = getAssistantConfig();
  const name = assistant?.name ?? "your assistant";
  const emoji = assistant?.emoji ?? "🦀";

  console.log(`Starting ${name}... ${emoji}
`);

  const result = spawn("openclaw", ["agent", "--agent", "main"], {
    stdio: "inherit"
  });

  return new Promise((resolve, reject) => {
    result.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${name} exited with code ${code}`));
    });
  });
}
```

Update `milimo/src/cli.ts` to register `assistant` commands and remove
any reference to the old `lucy` command.

---

## PART 2 — ONBOARDING WIZARD UPDATES

The existing wizard has 12 steps. The following tasks add, fix, or
replace specific steps. Do not rewrite the entire wizard — surgical
changes only to the identified steps.

---

### TASK 2.1 — Fix the template list (Step 2)

**File:** `milimo/src/commands/onboard.ts` and `onboard/template.ts`

The spec defines 7 templates. The wizard currently shows 5. Update the
built-in template list in `getBuiltInTemplates()` to match the full spec:

```typescript
const SPEC_TEMPLATES = [
  {
    id: "solo-founder",
    displayName: "Solo Founder",
    category: "solo",
description: "All 6 claws on one machine. One operator. The full product.",
squadSize: 1,
clawsActive: ["content", "ops", "analytics", "finance", "build", "assistant"],
    isDefault: true,
  },
  {
    id: "content-agency",
    displayName: "Content Agency",
    category: "creative",
    description: "Creative output, client management, and performance intelligence.",
    squadSize: 3,
    clawsActive: ["content", "ops", "analytics"],
  },
  {
    id: "design-studio",
    displayName: "Design Studio",
    category: "creative",
    description: "Creative output, client lifecycle, and financial tracking.",
    squadSize: 3,
    clawsActive: ["content", "ops", "finance"],
  },
  {
    id: "event-promotion",
    displayName: "Event Promotion",
    category: "creative",
    description: "Content, operations, and audience intelligence for events.",
    squadSize: 3,
    clawsActive: ["content", "ops", "analytics"],
  },
  {
    id: "freelance-collective",
    displayName: "Freelance Collective",
    category: "commerce",
    description: "Client management, analytics, and financial operations.",
    squadSize: 3,
    clawsActive: ["ops", "analytics", "finance"],
  },
  {
    id: "ai-micro-saas",
    displayName: "AI Micro-SaaS",
    category: "tech",
    description: "Full engineering, operations, analytics, and financial stack.",
    squadSize: 4,
    clawsActive: ["build", "ops", "analytics", "finance"],
  },
  {
    id: "campus-ai-tool",
    displayName: "Campus AI Tool",
    category: "tech",
    description: "Engineering, content, and operations for campus products.",
    squadSize: 3,
    clawsActive: ["build", "content", "ops"],
  },
];
```

Update the wizard display prompt to show all 7 with their descriptions
and claw composition.

---

### TASK 2.2 — Add the assistant persona step (new Step 6a)

Insert a new step between the current Step 6 (Operator Name) and Step 7
(War Room Mode). This is the assistant persona configuration step.

**Position in wizard:** After operator name is collected, before War Room mode.

**Implement in `milimo/src/commands/onboard.ts`:**

```typescript
// Step 6a: Assistant Persona
// Displayed after operator name is collected

async function promptAssistantPersona(): Promise<{
  name: string;
  creature: string;
  vibe: string;
  emoji: string;
}> {
  console.log("
── Assistant Persona ─────────────────────────────────");
  console.log("Your squad assistant is your conversational interface to");
  console.log("all your claws. Give it a name, a creature, and a vibe.
");
  console.log("Examples:");
  console.log('  Name: Nova  · Creature: a hawk   · Vibe: fast and precise  · 🦅');
  console.log('  Name: Rex   · Creature: a wolf   · Vibe: direct and loyal  · 🐺');
  console.log('  Name: Sage  · Creature: an owl   · Vibe: measured and wise · 🦉');
  console.log('  Name: Lucy  · Creature: a claw   · Vibe: sharp and unhurried · 🦀');
  console.log();

  const name = await promptInput("Assistant name", {
    default: "Nova",
    validate: (v: string) => {
      if (!v.trim()) return "Name cannot be empty";
      if (v.length > 30) return "Name must be 30 characters or fewer";
      return null;
    }
  });

  const creature = await promptInput("Creature (e.g. a claw, a hawk, an owl)", {
    default: "a claw",
    validate: (v: string) => {
      if (!v.trim()) return "Creature cannot be empty";
      return null;
    }
  });

  const vibe = await promptInput("Vibe (e.g. sharp and unhurried, warm and direct)", {
    default: "sharp and unhurried",
    validate: (v: string) => {
      if (!v.trim()) return "Vibe cannot be empty";
      return null;
    }
  });

  const emoji = await promptInput("Signature emoji", {
    default: "🦀",
    validate: (v: string) => {
      if (!v.trim()) return "Emoji cannot be empty";
      return null;
    }
  });

  return { name, creature, vibe, emoji };
}
```

The collected values are stored in the wizard state and written to
`config.json` under the `assistant` key.

---

### TASK 2.3 — Update the config schema

**File:** `milimo/src/onboard/config.ts`

Add the `assistant` block to `MilimoConfig`:

```typescript
interface MilimoConfig {
  squadName: string;
  clawRole: ClawRole;
  template: string;
  solo: boolean;
  meshMembers: string[];
  meshSecret: string | null;
  operatorName: string;
  warRoomMode: "full" | "minimal" | "disabled";
  onboardedAt: string | null;
  initializedAt: string;
  blueprintVersion: string;
  serverUrl?: string;
  deep_work?: {
    active: boolean;
    activated_at: string;
    resume_date: string;
  };

  // NEW — assistant persona
  assistant: {
    name: string;         // e.g. "Nova", "Rex", "Lucy"
    creature: string;     // e.g. "a claw", "a hawk"
    vibe: string;         // e.g. "sharp and unhurried"
    emoji: string;        // e.g. "🦀", "🦅"
  };

  // NEW — active claws derived from template
  activeClaws: string[];  // e.g. ["content", "ops", "analytics", "finance", "build"]
}
```

Add default values for the `assistant` block in `ConfigManager.getDefaults()`:

```typescript
assistant: {
  name: "Nova",
  creature: "a claw",
  vibe: "sharp and unhurried",
  emoji: "🦀",
},
activeClaws: ["content", "ops", "analytics", "finance", "build", "assistant"],
```

Add a migration step in `ConfigManager.migrate()` for existing configs
that lack the `assistant` field — add defaults without overwriting if
already set.

---

### TASK 2.4 — Update Step 10 confirmation summary

**File:** `milimo/src/commands/onboard.ts`

The confirmation summary (Step 10) must include the new assistant config:

```
Configuration summary:
  Squad:     my-squad
  Template:  solo-founder (content, ops, analytics, finance, build)
  Mode:      Solo
  Operator:  Mainza Kangombe
  Assistant: Nova (a hawk · fast and precise · 🦅)
  War Room:  full

Apply this configuration? (Y/n):
```

---

### TASK 2.5 — Run assistant setup automatically after onboarding

**File:** `milimo/src/commands/onboard.ts`

At the end of the `applyConfiguration()` function (Step 11), after the
config is saved and directories created, automatically run assistant setup:

```typescript
// After saving config.json...

console.log("
Configuring squad assistant...");
try {
  await assistantSetup();  // from commands/assistant.ts
} catch (err) {
  // Non-fatal — assistant can be configured manually later
  console.warn("Assistant setup skipped — run 'milimo assistant setup' manually.");
  console.warn(err instanceof Error ? err.message : String(err));
}
```

---

### TASK 2.6 — Update the success screen (Step 12)

**File:** `milimo/src/commands/onboard.ts`

Replace the hardcoded success message with one that uses the assistant's
configured name and emoji:

```typescript
function showSuccessScreen(config: MilimoConfig): void {
  const { name, emoji } = config.assistant;
  const assistantLine = `${name} is ready — start with: milimo assistant start`;

  console.log(`
╔═══════════════════════════════════════════════════════╗
║ ${emoji}  Onboarding Complete!  ${emoji}                         ║
╚═══════════════════════════════════════════════════════╝

  Squad:     ${config.squadName}
  Template:  ${config.template}
  Assistant: ${name} ${emoji}

Next steps:
  milimo assistant start          # Talk to ${name}
  milimo warroom                  # Open the War Room
  milimo squad status             # View squad configuration

The milimo never stops. Work. Without working.
`);
}
```

---

### TASK 2.7 — Update init command to include assistant config

**File:** `milimo/src/commands/init.ts`

The quick init command currently skips assistant configuration. Add
non-interactive flags and defaults:

```typescript
// Add to init command flags:
// --assistant-name <name>     default: "Nova"
// --assistant-creature <c>    default: "a claw"
// --assistant-vibe <vibe>     default: "sharp and unhurried"
// --assistant-emoji <emoji>   default: "🦀"

// After config is saved, run assistant setup automatically
await assistantSetup();
```

---

### TASK 2.8 — Update onboard --squad status to show assistant

**File:** `milimo/src/commands/init.ts` or `commands/squad.ts`

The `openclaw milimo squad status` output should include assistant info:

```
Squad: my-squad
Template: solo-founder
Active claws: content, ops, analytics, finance, build
Mode: Solo
Operator: Mainza Kangombe
Assistant: Nova 🦀  (a claw · sharp and unhurried)
War Room: full
Onboarded: 2026-03-22
```

---

## PART 2B — CRITICAL UX FIX: SOLO MODE ROLE SELECTION

This is a standalone fix that must be applied regardless of everything else
in this prompt. It can be merged and deployed independently.

### The Bug

When the operator selects solo mode during onboarding, the wizard
immediately asks them to pick one of six claw roles. In solo mode,
all six claws run simultaneously on the same machine. Asking the
operator to pick one is incorrect, confusing, and implies only one
claw will run — which contradicts the entire purpose of the solo template.

Current broken flow:
```
Operating solo (no mesh coordination)? (Y/n): Y
Squad name [my-squad]: MQ

Your claw role:
 * 1. content — Creative output...
   2. ops — Client lifecycle...
   ...

Select [1-6] (default: 1): ← THIS QUESTION MUST NOT APPEAR IN SOLO MODE
```

### TASK 2B.1 — Fix role prompt conditional in onboard.ts

**File:** `milimo/src/commands/onboard.ts`

The role selection step (Step 5) must be gated on the operating mode
selected in Step 3. Apply this logic:

```typescript
// Step 3: Solo vs Mesh (existing — do not change)
const isSolo = await promptConfirm(
  "Operating solo (no mesh coordination)?",
  { default: true }
);

// Step 4: Squad name (existing — do not change)
const squadName = await promptInput("Squad name", { default: "my-squad" });

// Step 5: Role — CONDITIONAL on mode
let clawRole: string;

if (isSolo) {
  // Solo mode: all claws run on this machine — no role selection
  clawRole = "solo";

  // Show confirmation of what will run instead of asking
  const template = selectedTemplate; // from Step 2
  const activeClaws = template.clawsActive.join(" · ");

  console.log(`
✓ Solo mode — all claws will run on this machine:
  ${activeClaws}
`);

} else {
  // Mesh mode: operator runs exactly one claw — role selection makes sense
  console.log("
Mesh mode — which claw are you running on this machine?
");

const roleChoices = [
  { value: "content", label: "content — Creative output — posts, copy, campaigns, brand voice" },
  { value: "ops", label: "ops — Client lifecycle — intake, scoping, delivery, follow-up" },
  { value: "analytics", label: "analytics — Intelligence layer — performance, trends, opportunities" },
  { value: "finance", label: "finance — Financial ops — invoicing, pricing, margin tracking" },
  { value: "build", label: "build — Engineering — code, PRs, deploys, monitoring" },
  { value: "assistant", label: "assistant — Conversational interface — routing, status, operator proxy" },
];

  // Filter to only claws active in the selected template
  const availableRoles = roleChoices.filter(
    r => template.clawsActive.includes(r.value)
  );

  clawRole = await promptSelect("Your claw role", availableRoles, {
    default: availableRoles[0].value
  });

  console.log(`
✓ You are running the ${clawRole} claw on this machine.`);
  console.log(
    `  Other squad members will run: ` +
    template.clawsActive.filter(c => c !== clawRole).join(", ")
  );
}
```

### TASK 2B.2 — Update MilimoConfig clawRole type

**File:** `milimo/src/onboard/config.ts`

The `clawRole` field type must include `"solo"` as a valid value:

```typescript
// Before:
type ClawRole = "content" | "ops" | "analytics" | "finance" | "build";

// After:
type ClawRole = "content" | "ops" | "analytics" | "finance" | "build" | "assistant" | "solo";
```

All downstream code that reads `clawRole` and expects exactly one of the
six claw names must handle `"solo"` gracefully — typically by treating it
as "all claws" or by reading `activeClaws` from the config instead.

### TASK 2B.3 — Update squad status display

**File:** `milimo/src/commands/onboard.ts` (existing config display, Step 1)

The existing config display shows `Role: build` for a solo-founder
setup — which is actively misleading. Update it to show the actual
running claws when role is `"solo"`:

```typescript
function formatRoleDisplay(config: MilimoConfig): string {
  if (config.clawRole === "solo") {
    return `Solo (${config.activeClaws?.join(", ") ?? "all claws"})`;
  }
  return config.clawRole;
}

// Usage in Step 1 existing config display:
console.log(`  Role:     ${formatRoleDisplay(config)}`);
```

This fixes the display seen in the screenshot:
```
// Before (misleading):
Role: build

// After (accurate):
Role: Solo (content, ops, analytics, finance, build, assistant)
```

### TASK 2B.4 — Update solo_init.py to initialize all claws when role is solo

**File:** `milimo-blueprint/orchestrator/solo_init.py`

Currently `solo_init.py` may check `clawRole` to determine which sandboxes
to initialize. When `clawRole === "solo"`, it must initialize ALL sandboxes
in the active claws list — not just one:

```python
def get_claws_to_initialize(config: dict) -> list[str]:
    """
    Returns the list of claw roles to initialize sandboxes for.

    In solo mode: all active claws from the template.
    In mesh mode: only the single claw role this operator runs.
    """
    claw_role = config.get("clawRole", "solo")
    active_claws = config.get("activeClaws",
        ["content", "ops", "analytics", "finance", "build", "assistant"])

    if claw_role == "solo":
        return active_claws   # Initialize everything
    else:
        return [claw_role]    # Mesh mode — one claw only
```

### TASK 2B.5 — Fix the screenshot scenario specifically

The screenshot shows the wizard running with:
  - Template: solo-founder ✓
  - Mode: Solo ✓
  - Squad name: MQ ✓
  - Then immediately: "Your claw role: 1. content..." ← BUG

After this fix, the same flow should look like:

```
🦀 MILIMO CLAW — Onboarding Wizard 🦀

Inference: ${NEMOCLAW_MODEL} @ https://inference.local/v1

Existing Milimo configuration found:
  Squad:    milimoquantum
  Role:     Solo (content, ops, analytics, finance, build)
  Template: solo-founder
  Mode:     Solo
  War Room: full
  Onboarded: 2026-03-20T18:47:16.080Z

Reconfigure? (y/N): y

Template:
 * 1. Solo Founder — solo (all 6 claws)
   2. Content Agency — squad of 3
   ...

Select [1-7] (default: 1): 1

Operating solo (no mesh coordination)? (Y/n): Y

Squad name [milimoquantum]: MQ

✓ Solo mode — all claws will run on this machine:
  content · ops · analytics · finance · build

Operator name [mainza]:
```

The role selection screen is completely absent from the solo flow.

### Tests for 2B

Write tests covering:
- Solo mode: `clawRole` set to `"solo"` in output config
- Solo mode: role prompt never shown (assert it is not called)
- Mesh mode: role prompt shown, only claws in active template offered
- Mesh mode: `clawRole` set to selected role in output config
- `formatRoleDisplay("solo")` returns readable multi-claw string
- `formatRoleDisplay("content")` returns "content" unchanged
- `get_claws_to_initialize()` returns all active claws when role is "solo"
- `get_claws_to_initialize()` returns one claw when role is "content"
- Template with 3 active claws only shows 3 role options in mesh mode

---

## PART 3 — UPDATE AGENTS.md AND bridge_cli.py REFERENCES

### TASK 3.1 — Update bridge_cli.py squad_config response

**File:** `milimo-blueprint/orchestrator/bridge_cli.py`

The `squad_config` query handler must include the assistant config
in its response (credentials still stripped):

```python
@register("squad_config")
def squad_config(args: dict, start: float) -> None:
    config = _safe_read_json(MILIMO_CONFIG_PATH)
    if not config:
        _respond("squad_config", _empty_state("config not found"), start)
        return

    # Strip credential fields
    STRIP_KEYS = {"stripe_key", "github_token", "api_key",
                  "secret", "credentials", "meshSecret"}
    safe_config = {k: v for k, v in config.items() if k not in STRIP_KEYS}

    _respond("squad_config", {
        "config": safe_config,
        "assistant_name": config.get("assistant", {}).get("name", "unknown"),
        "assistant_emoji": config.get("assistant", {}).get("emoji", "🦀"),
        "active_claws": config.get("activeClaws", []),
        "data_quality": "complete"
    }, start)
```

### TASK 3.2 — Update AGENTS.md file structure reference

Update the file structure reference in `AGENTS.md` to reflect the renames:

```
# Replace:
├── commands/
│   └── lucy.ts              Deep Work Mode CLI  ← REMOVE THIS LINE

# Add:
├── commands/
│   └── assistant.ts         Assistant setup, verify, start

# Replace in milimo-claw-docs/reference/:
LUCY_SYSTEM_PROMPT.md  ← REMOVE

# Add:
MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md   (parameterized template)
```

Also update the orchestrator file list:

```
# Replace:
solo_init.py           ← keep
# lucy_setup.py        ← REMOVE

# Add:
assistant_setup.py     Template renderer + NemoClaw runtime installer
```

---

## FINAL VERIFICATION CHECKLIST

### Assistant Setup
□ `assistant_setup.py` reads name/creature/vibe/emoji from config.json
□ `render_template()` substitutes all 8 placeholders correctly
□ `render_template()` raises ValueError if any placeholder remains
□ Rendered system.md references the correct assistant name throughout
□ Rendered system.md shows only active claws for this template
□ `assistant_setup.py --verify` exits 0 when complete, 1 when incomplete
□ `milimo assistant setup` triggers Python setup script
□ `milimo assistant verify` prints per-check results
□ `milimo assistant start` reads name from config (not hardcoded)
□ `commands/lucy.ts` deleted — no reference to it in cli.ts

### Onboarding Wizard
□ Template list shows all 7 templates with claw composition
□ solo-founder is the default template (option 1)
□ Assistant persona step appears between operator name and War Room mode
□ Assistant name, creature, vibe, emoji all prompted with sensible defaults
□ Confirmation summary includes assistant persona line
□ `config.json` written with `assistant` block populated
□ `config.json` written with `activeClaws` array matching selected template
□ Assistant setup runs automatically at end of onboarding
□ Success screen shows the operator's assistant name (not "Lucy")
□ `milimo init` accepts `--assistant-name` flag
□ `milimo init` runs assistant setup automatically
□ `milimo squad status` output includes assistant name and emoji

### Config Schema
□ `MilimoConfig` interface has `assistant` block with all 4 fields
□ `MilimoConfig` interface has `activeClaws` string array
□ `ConfigManager.getDefaults()` includes assistant defaults
□ `ConfigManager.migrate()` adds assistant defaults to legacy configs
□ No hardcoded assistant names anywhere in TypeScript or Python source

### Bridge
□ `squad_config` query returns `assistant_name` and `assistant_emoji`
□ `squad_config` strips meshSecret and credential fields

### Solo/Mesh Role Selection Fix (2B)
□ Solo mode: role selection screen never appears
□ Solo mode: confirmation shows all active claws from the template
□ Solo mode: `clawRole` written as `"solo"` in config.json
□ Solo mode: `activeClaws` array written correctly in config.json
□ Mesh mode: role selection shows only claws active in selected template
□ Mesh mode: `clawRole` written as the selected single role
□ `formatRoleDisplay("solo")` returns multi-claw readable string
□ Existing config display shows `Role: Solo (content, ops, ...)` not `Role: build`
□ `get_claws_to_initialize()` returns all claws when role is "solo"
□ `get_claws_to_initialize()` returns one claw in mesh mode
□ `ClawRole` type includes `"solo"` as valid value

### No "Lucy" hardcoding
□ grep codebase for "Lucy" — only appears in example interactions in
  the system prompt TEMPLATE (as an example) — never in source code
□ grep codebase for "lucy" — no TypeScript or Python files reference
  "lucy" as a fixed name

### Tests
□ All pytest tests pass: `pytest milimo-blueprint/tests/`
□ All Jest tests pass: `npx jest milimo/src/`

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  File: [exact path — NEW | UPDATE | DELETE]
  Summary: [one sentence]

  [complete implementation]

  Tests: [complete test additions or new test file]
  -----------------------------------------

Begin with Task 1.1. Complete Part 1 before Part 2.
No hardcoded assistant names anywhere.
The template renders at setup time — not at session start.
