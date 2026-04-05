> ⚠️ **DEPRECATED** — Superseded by the setup steps in [README.md](../../README.md).
>
> Kept for historical reference only.

---

# MilimoClaw Complete Setup Guide

> Documented: 2026-04-04 — Verified end-to-end sandbox deployment with fresh NemoClaw install

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Docker Desktop | Running | `docker ps` |
| Node.js | 22.x | `node --version` |
| Python | 3.12+ | `python3 --version` |
| Git | Any | `git --version` |
| Disk space | ~5GB free | `df -h /` |
| NVIDIA API key | Valid | From build.nvidia.com |

---

## Phase 1: Install NemoClaw (User Step)

> **Important:** NemoClaw must be installed by the user. MilimoClaw runs inside the NemoClaw sandbox — it does not install NemoClaw itself.
>
> **Automated session clearing:** Both `install.sh` and `openclaw milimo onboard` automatically clear old agent sessions and memory before setting up the assistant. This ensures the AI loads fresh with full MilimoClaw context — no stale "I don't know about Milimo Claw" responses.

```bash
# 1. Install NemoClaw
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash

# 2. Go through the 7-step onboard wizard
#    - Select your inference provider (NVIDIA Endpoints recommended)
#    - Enter your NVIDIA API key
#    - Choose your model (z-ai/glm5, nvidia/nemotron-3-super-120b-a12b, etc.)
#    - Enable GPU if available
#    - Accept policy presets (pypi, npm, telegram)
#    - Confirm sandbox creation

# 3. Wait for sandbox to be ready (~5-10 minutes)
#    You should see:
#    ──────────────────────────────────────────────────
#      Sandbox      my-assistant (Landlock + seccomp + netns)
#      Model        <your-model>
#    ──────────────────────────────────────────────────
#      Run:         nemoclaw my-assistant connect
#    ──────────────────────────────────────────────────

# 4. Test the sandbox
nemoclaw my-assistant connect
# Inside sandbox:
openclaw tui
# You should be able to chat with the assistant
```

---

## Phase 2: Deploy MilimoClaw Plugin

### 2.1 Build the Plugin on Host

```bash
# From the MilimoClaw directory
cd /path/to/MilimoClaw/milimo

# Install dependencies and build
npm install
npx tsc

# Verify build output
ls dist/index.js  # Should exist
```

### 2.2 Transfer Source to Sandbox

```bash
# Create source archive (no node_modules, no tests)
cd /path/to/MilimoClaw
tar czf /tmp/milimo-source.tar.gz -C milimo \
  --exclude='node_modules' \
  --exclude='__tests__' \
  --exclude='*.test.ts' \
  --exclude='tsconfig.tsbuildinfo' \
  --exclude='dist' \
  .

# Transfer to sandbox
docker cp /tmp/milimo-source.tar.gz openshell-cluster-nemoclaw:/tmp/milimo-source.tar.gz
docker exec openshell-cluster-nemoclaw kubectl cp /tmp/milimo-source.tar.gz openshell/my-assistant:/tmp/milimo-source.tar.gz
```

### 2.3 Build and Install Inside Sandbox

```bash
# Connect to sandbox
nemoclaw my-assistant connect

# Inside sandbox, run all of these:

# 1. Extract source
mkdir -p /sandbox/extensions/milimo
tar xzf /tmp/milimo-source.tar.gz -C /sandbox/extensions/milimo
rm /tmp/milimo-source.tar.gz

# 2. Build plugin
cd /sandbox/extensions/milimo
npm install
npx tsc
ls dist/index.js  # Verify

# 3. Install via OpenClaw
openclaw plugins install /sandbox/extensions/milimo

# 4. Copy to sandbox user extensions directory
mkdir -p /sandbox/.openclaw-data/extensions
cp -r /sandbox/extensions/milimo /sandbox/.openclaw-data/extensions/milimo
chown -R sandbox:sandbox /sandbox/.openclaw-data/extensions/milimo

# 5. Register plugin in sandbox user's openclaw.json
python3 << 'PYEOF'
import json

config_path = "/sandbox/.openclaw/openclaw.json"
with open(config_path) as f:
    config = json.load(f)

config["plugins"] = {
    "entries": {
        "milimo": { "enabled": True }
    },
    "installs": {
        "milimo": {
            "source": "path",
            "sourcePath": "/sandbox/extensions/milimo",
            "installPath": "/sandbox/.openclaw-data/extensions/milimo",
            "version": "0.1.0",
            "installedAt": "2026-04-04T00:00:00.000Z"
        }
    }
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print("Plugin registered")
PYEOF

# 6. Fix all directory ownership
chown -R sandbox:sandbox /sandbox/.milimo 2>/dev/null || true
mkdir -p /sandbox/.milimo/blueprints
chown -R sandbox:sandbox /sandbox/.milimo
chown -R sandbox:sandbox /sandbox/.openclaw/agents/main
chmod -R 775 /sandbox/.openclaw/agents/main
chown -R sandbox:sandbox /sandbox/.openclaw/workspace
chown -R sandbox:sandbox /sandbox/.openclaw/credentials 2>/dev/null || true
mkdir -p /sandbox/.openclaw/credentials
chown 999:999 /sandbox/.openclaw/credentials
chmod 755 /sandbox/.openclaw/credentials
chown 999:999 /sandbox/.openclaw
chmod 755 /sandbox/.openclaw

# 7. Verify plugin loads
openclaw milimo --help
# Should show: "Milimo Claw registered" with Squad, Template, Commands
```

---

## Phase 3: Deploy Blueprint Economy

### 3.1 Transfer Blueprint to Sandbox

```bash
# From host machine
cd /path/to/MilimoClaw
tar czf /tmp/blueprint-full.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  milimo-blueprint/

docker cp /tmp/blueprint-full.tar.gz openshell-cluster-nemoclaw:/tmp/blueprint-full.tar.gz
docker exec openshell-cluster-nemoclaw kubectl cp /tmp/blueprint-full.tar.gz openshell/my-assistant:/tmp/blueprint-full.tar.gz
```

### 3.2 Extract Blueprint Inside Sandbox

```bash
# Inside sandbox (nemoclaw my-assistant connect)
cd /sandbox
tar xzf /tmp/blueprint-full.tar.gz
rm /tmp/blueprint-full.tar.gz
chown -R sandbox:sandbox /sandbox/milimo-blueprint
```

---

## Phase 4: Run MilimoClaw Onboarding

```bash
# Inside sandbox
openclaw milimo onboard

# The wizard will ask:
# - Assistant name (e.g., Lucy)
# - Creature (e.g., a claw)
# - Vibe (e.g., sharp and unhurried)
# - Signature emoji (e.g., 👽)
# - Squad name (e.g., zulu)
# - Template: solo (all 5 claws active — no role selection)
# - War Room mode: full

# Confirm with Y
```

### Non-Interactive Alternative

```bash
openclaw milimo onboard \
  --solo \
  --squad zulu \
  --operator Mainza \
  --template solo \
  --war-room-mode full
```

---

## Phase 5: Verify Everything Works

```bash
# Inside sandbox

# 1. Plugin loaded
openclaw milimo --help

# 2. Assistant has MilimoClaw context
openclaw agent --agent main --message "what do you know about Milimo Claw?"

# 3. All claws importable
cd /sandbox/milimo-blueprint
python3 -c "
import sys
sys.path.insert(0, '.')
from orchestrator.build.build_claw import BuildClaw
from orchestrator.content.content_claw import ContentClaw
from orchestrator.ops.ops_claw import OpsClaw
from orchestrator.analytics.analytics_claw import AnalyticsClaw
from orchestrator.finance.finance_claw import FinanceClaw
print('All 5 claws importable')
"

# 4. War Room
openclaw milimo warroom

# 5. TUI with Milimo slash commands
openclaw tui
# Inside TUI:
# /milimo health
# /milimo squad
```

---

## Phase 6: Telegram Setup (Host-Side)

> **Critical:** Telegram is managed by NemoClaw on the HOST, not inside the sandbox.

```bash
# 1. Set the bot token as an environment variable on your HOST
export TELEGRAM_BOT_TOKEN="your-bot-token-here"

# 2. (Optional) Restrict to your Telegram account only
export ALLOWED_CHAT_IDS="your_telegram_chat_id"

# 3. Start auxiliary services (launches Telegram bridge)
nemoclaw start

# 4. Verify the bridge is running
nemoclaw status

# 5. Open Telegram, find your bot, and send a message
# The bridge forwards messages between your bot and the agent

# 6. To stop the bridge
nemoclaw stop
```

**Getting your Telegram Chat ID:**
1. Send a message to your bot on Telegram
2. Check the NemoClaw logs: `nemoclaw my-assistant logs --follow`
3. Your chat ID will appear in the bridge logs

---

## Critical Fixes (If Things Break)

### Inference Not Working

```bash
# Inside sandbox - install CA cert
cp /etc/openshell-tls/openshell-ca.pem /usr/local/share/ca-certificates/openshell-ca.crt
update-ca-certificates 2>/dev/null || true

# Set TLS env vars
echo 'export CURL_CA_BUNDLE=/etc/openshell-tls/openshell-ca.pem' >> /sandbox/.bashrc
echo 'export NODE_EXTRA_CA_CERTS=/etc/openshell-tls/openshell-ca.pem' >> /sandbox/.bashrc
echo 'export REQUESTS_CA_BUNDLE=/etc/openshell-tls/openshell-ca.pem' >> /sandbox/.bashrc

# Test
curl -s --max-time 10 https://inference.local/v1/models
```

### Permission Denied Errors

```bash
# From host terminal
docker exec openshell-cluster-nemoclaw kubectl exec -n openshell my-assistant -- bash -c '
chown -R 999:999 /sandbox/.milimo
chown -R 999:999 /sandbox/.openclaw
chown -R 999:999 /sandbox/.openclaw/agents/main
chown -R 999:999 /sandbox/.openclaw/workspace
mkdir -p /sandbox/.openclaw/credentials
chown 999:999 /sandbox/.openclaw/credentials
chmod 755 /sandbox/.openclaw/credentials
echo "All permissions fixed"
'
```

### Assistant Has No MilimoClaw Context

```bash
# Inside sandbox - clear stale sessions and memory
rm -f /sandbox/.openclaw/agents/main/sessions/*.jsonl
rm -f /sandbox/.openclaw/workspace/MEMORY.md
rm -rf /sandbox/.openclaw/workspace/memory/daily/
rm -rf /sandbox/.openclaw/workspace/memory/channel/

# Re-run assistant setup
cd /sandbox/milimo-blueprint
python3 orchestrator/assistant_setup.py
```

### Template Not Found During Onboarding

```bash
# Inside sandbox - ensure template is at the right path
cp /sandbox/milimo-blueprint/orchestrator/templates/assistant_system_prompt.md \
   /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
chown sandbox:sandbox /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
```

### Assistant Setup Fails (FileNotFoundError)

If `openclaw milimo onboard` shows "System prompt template not found" during assistant setup:

```bash
# Inside sandbox - fix the find_template() search path
python3 << 'PYEOF'
path = "/sandbox/milimo-blueprint/orchestrator/assistant_setup.py"
with open(path) as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if "_TEMPLATE_CANDIDATES = [" in line:
        indent = "    "
        new_lines.append(indent + "# 0. Bundled with orchestrator (sandbox deployment)\n")
        new_lines.append(indent + "Path(__file__).resolve().parent / \"templates\" / \"assistant_system_prompt.md\",\n")

with open(path, "w") as f:
    f.writelines(new_lines)
print("Template search path added")
PYEOF

# Also copy template to expected locations
cp /sandbox/milimo-blueprint/orchestrator/templates/assistant_system_prompt.md \
   /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
chown sandbox:sandbox /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md

# Re-run assistant setup
cd /sandbox/milimo-blueprint
python3 orchestrator/assistant_setup.py
```

---

## Complete Sandbox Directory Structure

```
/sandbox/
├── .milimo/
│   ├── config.json              # Flat schema: squadName, operatorName, template, solo, activeClaws
│   ├── blueprints/              # Installed blueprint packages
│   ├── templates/               # Assistant prompt templates
│   └── MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md  # Copy for find_template()
├── .openclaw/
│   ├── openclaw.json            # Main config (plugins, models, channels)
│   ├── credentials/             # Pairing codes (telegram-pairing.json)
│   ├── gateway-token            # Auth token for gateway connection
│   ├── agents/main/
│   │   ├── system.md            # Rendered assistant prompt with MilimoClaw context
│   │   ├── config.yaml          # Agent config (model, session)
│   │   └── sessions/            # Session history
│   └── workspace/
│       ├── MILIMO_CLAW.md       # Full MilimoClaw architecture reference
│       ├── SOUL.md              # Assistant personality + Milimo awareness
│       ├── IDENTITY.md          # Assistant identity
│       ├── USER.md              # Operator info
│       └── AGENTS.md            # Startup instructions
├── extensions/milimo/           # Plugin source + dist/ + node_modules/
├── .openclaw-data/extensions/milimo/  # Sandbox user's installed plugin
└── milimo-blueprint/
    ├── orchestrator/
    │   ├── build/               # 13 Build Claw modules
    │   ├── content/             # 11 Content Claw modules
    │   ├── ops/                 # 11 Ops Claw modules
    │   ├── analytics/           # 12 Analytics Claw modules
    │   ├── finance/             # 12 Finance Claw modules
    │   ├── templates/
    │   │   └── assistant_system_prompt.md  # Source template
    │   └── assistant_setup.py   # Renders and installs system prompt
    ├── roles/                   # 5 role YAML blueprints
    └── policies/                # 5 sandbox policy YAMLs
```

---

## Command Reference

### Host Machine

| Command | Purpose |
|---|---|
| `curl -fsSL https://www.nvidia.com/nemoclaw.sh \| bash` | Install NemoClaw |
| `nemoclaw my-assistant connect` | Connect to sandbox |
| `nemoclaw my-assistant status` | Check sandbox status |
| `nemoclaw my-assistant logs --follow` | Follow sandbox logs |
| `nemoclaw start` | Start auxiliary services (Telegram bridge) |
| `nemoclaw stop` | Stop auxiliary services |
| `export TELEGRAM_BOT_TOKEN="..."` | Set Telegram bot token |

### Inside Sandbox

| Command | Purpose |
|---|---|
| `openclaw milimo --help` | List Milimo commands |
| `openclaw milimo health` | Check squad health |
| `openclaw milimo squad` | View squad configuration |
| `openclaw milimo warroom` | Launch War Room TUI |
| `openclaw milimo onboard` | Run onboarding wizard |
| `openclaw milimo assistant start` | Talk to assistant |
| `openclaw agent --agent main` | Direct agent access |
| `openclaw tui` | Interactive TUI |
| `openclaw plugins list` | List loaded plugins |
| `openclaw pairing list telegram` | List Telegram pairing requests |
| `openclaw pairing approve telegram <CODE>` | Approve Telegram pairing |

### In TUI (Slash Commands)

| Command | Purpose |
|---|---|
| `/milimo health` | Check squad health |
| `/milimo squad` | View squad configuration |
| `/milimo action list` | View War Room queue |

---

## Key Architecture Notes

1. **NemoClaw is the host** — MilimoClaw runs inside the NemoClaw sandbox, never on the host directly
2. **API key stays on host** — The sandbox uses `inference.local` which is proxied by OpenShell; credentials never enter the sandbox
3. **Telegram is host-side** — The Telegram bridge runs via `nemoclaw start` on the host, not inside the sandbox
4. **Two OpenClaw users** — The sandbox has both `root` and `sandbox` (uid 999) users. Plugins must be installed for the sandbox user at `/sandbox/.openclaw-data/extensions/`
5. **Solo template = all 5 claws** — No role selection. All claws (Content, Ops, Analytics, Finance, Build) are active simultaneously
6. **Assistant is NOT a claw** — It's the conversational bridge between the operator and the autonomous claws
