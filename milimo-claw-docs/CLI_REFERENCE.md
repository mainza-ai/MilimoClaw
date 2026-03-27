# Milimo Claw — CLI Reference

> Complete command documentation for the Milimo Claw CLI.

---

## Overview

Milimo Claw registers as an OpenClaw plugin, adding the `milimo` command group to the `openclaw` CLI. All commands follow this pattern:

```bash
openclaw milimo <command> [subcommand] [options]
```

The `/milimo` slash command is also available from in-chat interfaces (Telegram, TUI).

---

## `milimo onboard`

Interactive setup wizard for squad configuration, template selection, and role assignment.

```bash
openclaw milimo onboard [options]
```

| Option | Description | Default |
|---|---|---|
| `--squad <name>` | Squad name | Interactive prompt |
| `--role <role>` | Claw role: `content`, `ops`, `analytics`, `finance`, `build` | Interactive prompt |
| `--template <template>` | Squad template (e.g., `solo-founder`, `content-agency`) | Interactive prompt |
| `--solo` | Initialize as solo operator (no mesh) | `false` |
| `--operator <name>` | Operator name | `$USER` |
| `--war-room-mode <mode>` | War Room mode: `full`, `minimal`, `disabled` | `full` |

**Examples:**

```bash
# Interactive wizard
openclaw milimo onboard

# Non-interactive setup
openclaw milimo onboard \
  --squad my-squad \
  --role content \
  --template solo-founder \
  --solo

# With custom operator and minimal War Room
openclaw milimo onboard \
  --squad agency-team \
  --role ops \
  --template content-agency \
  --operator "John Doe" \
  --war-room-mode minimal
```

**Onboarding Steps:**

1. **NemoClaw Check** — Verifies inference is configured
2. **Template Selection** — Choose from built-in or discovered templates
3. **Solo/Mesh Mode** — Single operator vs. team mesh
4. **Squad Name** — Unique identifier for your squad
5. **Role Assignment** — Your primary claw role
6. **Operator Name** — Human operator identifier
7. **War Room Mode** — Dashboard complexity level
8. **Mesh Secret** — Generated for mesh authentication (if applicable)
9. **Template Validation** — Python validation of template config
10. **Confirmation** — Review before applying
11. **Apply** — Create directories, save config
12. **Success** — Next steps displayed

**Built-in Templates:**

| Template | Category | Squad Size | Description |
|----------|----------|------------|-------------|
| `solo-founder` | solo | 1 | One-person operation with all claws |
| `content-agency` | agency | 3 | Content-first squad for agencies |
| `design-studio` | studio | 4 | Visual creative squad for designers |
| `tech-consultancy` | consultancy | 5 | Full-stack tech squad with build focus |
| `custom` | custom | — | Manual configuration from scratch |

---

## `milimo init`

Initialize a new squad or join an existing mesh (legacy command, use `onboard` for full setup).

```bash
openclaw milimo init [options]
```

| Option | Description | Default |
|---|---|---|
| `--squad <name>` | Squad name | Interactive prompt |
| `--role <role>` | Claw role: `content`, `ops`, `analytics`, `finance`, `build` | Interactive prompt |
| `--template <template>` | Squad template (e.g., `content-agency`, `design-studio`) | Interactive prompt |
| `--solo` | Initialize as solo operator (no mesh) | `false` |

**Examples:**

```bash
# Interactive setup
openclaw milimo init

# Non-interactive with template
openclaw milimo init --squad hustle-squad --role content --template content-agency

# Solo mode (no mesh networking)
openclaw milimo init --squad solo-ops --role ops --solo
```

**What it does:**
1. Creates squad state at `~/.milimo/state.json`
2. Deploys the selected template's claw configuration
3. Sets up the mesh directory structure at `~/.milimo/mesh/`
4. Registers this claw with the squad mesh (unless `--solo`)

---

## `milimo squad`

Squad lifecycle management commands.

### `milimo squad status`

Show squad topology, claw health, and mesh state.

```bash
openclaw milimo squad status [--json]
```

| Option | Description |
|---|---|
| `--json` | Output as machine-readable JSON |

**Output includes:**
- Squad name and role
- Mesh topology (which claws are online)
- Current mode (normal / finals-mode)
- Blueprint version
- Pending War Room actions count

### `milimo squad finals-mode`

Activate Finals Mode — all claws enter maintenance configuration simultaneously.

```bash
openclaw milimo squad finals-mode [options]
```

| Option | Description | Default |
|---|---|---|
| `--duration <duration>` | Duration (e.g., `2weeks`, `10days`, `3weeks`) | `2weeks` |
| `--resume-date <date>` | Scheduled resume date (ISO format) | Calculated from duration |

**What Finals Mode does:**
1. Hot-reloads all squad sandbox egress policies to outgoing-only
2. Enables auto-responses for active clients from approved templates
3. Pauses all new client intake routes
4. Flags all pending deadlines in War Room with urgency scoring
5. Sets Analytics claw to passive monitoring only

### `milimo squad onboard-status`

Show current onboarding configuration.

```bash
openclaw milimo squad onboard-status
```

**Output includes:**
- Squad name and role
- Template selection
- Solo/Mesh mode
- Operator name
- War Room mode
- Onboarding timestamp

### `milimo squad resume`

Resume from Finals Mode — restore all claw policies to their pre-finals state.

```bash
openclaw milimo squad resume
```

---

## `milimo blueprint`

Blueprint operations for versioning, forking, and marketplace publishing.

### `milimo blueprint list`

List available role blueprints and templates.

```bash
openclaw milimo blueprint list [--json]
```

### `milimo blueprint fork`

Fork a public blueprint as your starting point.

```bash
openclaw milimo blueprint fork <source> [--into <name>]
```

| Argument | Description |
|---|---|
| `<source>` | Blueprint identifier (e.g., `@seniorSquad2025/content-agency-v8.3`) |
| `--into <name>` | Name for the forked blueprint |

### `milimo blueprint diff`

Compare two blueprint versions.

```bash
openclaw milimo blueprint diff <versionA> <versionB>
```

### `milimo blueprint publish`

Export your evolved blueprint to the marketplace.

```bash
openclaw milimo blueprint publish [--name <name>] [--price <price>]
```

| Option | Description | Default |
|---|---|---|
| `--name <name>` | Display name for the listing | Derived from squad name |
| `--price <price>` | Price (e.g., `0.05eth`, `$25`, `free`) | `free` |

### `milimo blueprint rollback`

Roll back to a previous blueprint version.

```bash
openclaw milimo blueprint rollback [--to <version>] [--reason <reason>]
```

---

## `milimo health`

Display health status of squad claws.

```bash
openclaw milimo health [--json]
```

| Option | Description |
|---|---|
| `--json` | Output as machine-readable JSON |

**Output includes:**
- Per-claw status (active/idle/error)
- Tool count per claw
- Last evolution cycle timestamp

---

## `milimo payment`

Payment and marketplace operations.

### `milimo payment checkout`

Create a checkout session for a blueprint purchase.

```bash
openclaw milimo payment checkout --blueprint <id> [--success-url <url>] [--cancel-url <url>]
```

| Option | Description | Default |
|---|---|---|
| `--blueprint <id>` | Blueprint ID to purchase | Required |
| `--success-url <url>` | Redirect URL on success | `milimo://checkout/success` |
| `--cancel-url <url>` | Redirect URL on cancel | `milimo://checkout/cancel` |

### `milimo payment status`

Check payment session status.

```bash
openclaw milimo payment status --session <id>
```

### `milimo payment balance`

Show seller balance.

```bash
openclaw milimo payment balance
```

### `milimo payment history`

Show transaction history.

```bash
openclaw milimo payment history [--limit <n>]
```

| Option | Description | Default |
|---|---|---|
| `--limit <n>` | Number of transactions | 10 |

### `milimo payment invoice`

Generate invoice for a session.

```bash
openclaw milimo payment invoice --session <id> [--format <format>]
```

| Option | Description | Default |
|---|---|---|
| `--session <id>` | Session ID | Required |
| `--format <format>` | Output format: `text`, `json`, `html` | `text` |

### `milimo payment connect`

Connect a Stripe account for receiving payments.

```bash
openclaw milimo payment connect --display-name <name> --email <email>
```

| Option | Description |
|---|---|
| `--display-name <name>` | Display name for the account (Required) |
| `--email <email>` | Email address (Required) |

---

## `milimo verify`

Verify blueprint provenance and integrity.

```bash
openclaw milimo verify [options]
```

| Option | Description |
|---|---|
| `--blueprint <id>` | Blueprint ID to verify |
| `--version <version>` | Specific version (default: current) |
| `--chain` | Validate entire provenance chain |
| `--strict` | Enable strict verification mode |
| `--json` | Output as JSON |

**Verification checks:**
- Signature validity (Ed25519)
- Content hash integrity (SHA-256)
- Timestamp validity
- Provenance chain continuity (with `--chain`)

---

## `milimo badge`

Performance verification badges.

```bash
openclaw milimo badge [options]
```

| Option | Description |
|---|---|
| `--blueprint <id>` | Blueprint ID |
| `--performance` | Generate performance attestation |
| `--verify <file>` | Verify an attestation file |
| `--list` | List all attestations |
| `--auditor <email>` | Request auditor verification |
| `--json` | Output as JSON |

**Badge levels:**

| Level | Threshold | Icon |
|-------|-----------|------|
| Verified | 0% | ✅ |
| Bronze | 5% | 🥉 |
| Silver | 10% | 🥈 |
| Gold | 15% | 🥇 |
| Platinum | 25% | 💎 |
| Elite | 40% | 👑 |

---

## `milimo provenance-keygen`

Generate Ed25519 key pair for blueprint signing.

```bash
openclaw milimo provenance-keygen --squad <name> [--force]
```

| Option | Description |
|---|---|
| `--squad <name>` | Squad name for key identification (Required) |
| `--force` | Overwrite existing key |

**Output:**
- Key file path: `~/.milimo/keys/<squad>.json`
- Public key (hex)
- Key ID (first 8 bytes)

---

## `milimo warroom`

Launch the War Room interactive operator dashboard with split-pane TUI.

```bash
openclaw milimo warroom [-o <operator>]
```

| Option | Description | Default |
|---|---|---|
| `-o, --operator <name>` | Override operator ID | `local-operator` |

### War Room TUI Layout

The War Room now features a modern split-pane interface:

```
┌─ WAR ROOM ─────────────────┬─ CLAW HEALTH ──────────────┐
│                            │ CONTENT ● active 11 tools  │
│ 🔴 HOLD BUILD CLAW         │ OPS ● active 8 tools       │
│ PR #52 ready to merge      │ ANALYTICS ● active 9 tools │
│ [A]pprove [B]lock          │ FINANCE ● active 7 tools   │
│                            │ BUILD ● active 12 tools    │
│ 🟡 REVIEW OPS CLAW         ├────────────────────────────┤
│ Proposal for @ArcLight     │ Revenue this week          │
│ $3,200                     │ $4,240 ↑18%                │
│ [A]pprove [E]dit [B]lock   │ 3 paid · 1 pending         │
│                            ├────────────────────────────┤
│ ✓ AUTO CONTENT CLAW        │ Evolution Log              │
│ post_047 published ✓       │ BUILD: PR enforcer built   │
│                            │ 5 days ago · +12% approval │
└────────────────────────────┴────────────────────────────┘
[Q]uit [R]efresh [H]elp [F]inals Mode
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑`/`↓` | Navigate through actions |
| `Enter` | Select/expand action |
| `A` | Approve selected action |
| `B` | Block (reject) selected action |
| `E` | Edit (hold) selected action |
| `Q` | Quit War Room |
| `R` | Refresh queue |
| `H` | Toggle help overlay |
| `F` | Toggle Finals Mode |

### Color Coding

| Color | Mode | Description |
|-------|------|-------------|
| 🔴 Coral | `HOLD` / `VETO` | Requires manual approval |
| 🟡 Amber | `REVIEW` | Recommended for review |
| 🟢 Teal | `AUTO` | Auto-approval eligible |

### Polling Interval

The War Room refreshes every **3 seconds** (reduced from 5s for faster response).

### Finals Mode

When Finals Mode is enabled (press `F`):
- All `AUTO` actions are automatically approved
- No operator input required for auto-eligible actions
- Actions are processed immediately and logged

### Approval Modes

Actions are evaluated by the approval engine before appearing in the queue:

| Mode | Behavior |
|---|---|
| `AUTO` | Executed immediately, logged for review |
| `REVIEW` | Queued for human approval |
| `HOLD` | Paused, requires explicit confirmation |
| `VETO` | Blocked, requires squad-wide re-vote |

### Rate Limiting

Auto-approvals are subject to rate limits based on subscription tier:

| Tier | Daily Limit | Burst Limit | Burst Window |
|------|-------------|-------------|--------------|
| **Free** | 10 | 3 | 1 hour |
| **Pro** | Unlimited | N/A | N/A |

When rate limit is reached:
- Message remains in queue for manual review
- Audit trail logs `RATE_LIMITED` action
- War Room displays remaining quota

Rate limit status is visible in the right panel.

---

## `/milimo` Slash Command

Available from chat interfaces (Telegram bridge, TUI):

| Command | Description |
|---|---|
| `/milimo` | Show help |
| `/milimo status` | Squad status summary |
| `/milimo role` | Show your claw role details |
| `/milimo finals` | Show Finals Mode status |
| `/milimo approve <id>` | Approve a pending War Room action |
| `/milimo veto <id>` | Block a pending action |
| `/milimo health` | One-line health summary per claw |
| `/milimo evolution` | Last tool built by each claw with performance delta |
| `/milimo help` | Full command list |

---

## Configuration

### Plugin Config (`openclaw.plugin.json`)

```json
{
  "pluginConfig": {
    "squadName": "my-squad",
    "clawRole": "content",
    "meshSecret": "",
    "blueprintDir": "/opt/milimo-blueprint"
  }
}
```

| Property | Type | Description |
|---|---|---|
| `squadName` | string | Name of the squad this claw belongs to |
| `clawRole` | string | Role: `content`, `ops`, `analytics`, `finance`, `build` |
| `meshSecret` | string | Shared secret for mesh authentication |
| `blueprintDir` | string | Path to the milimo-blueprint directory |

### State File (`~/.milimo/config.json`)

Created by `milimo onboard`. Single source of truth for all configuration (previously split between `state.json` and `config.json`).

```json
{
  "squadName": "my-squad",
  "clawRole": "content",
  "template": "solo-founder",
  "solo": true,
  "meshMembers": ["content"],
  "meshSecret": "enc:v1:...",
  "operatorName": "operator",
  "warRoomMode": "full",
  "onboardedAt": "2026-03-19T12:00:00.000Z",
  "initializedAt": "2026-03-19T12:00:00.000Z",
  "blueprintVersion": "0.1.0",
  "serverUrl": "https://api.milimoclaw.com"
}
```

| Property | Type | Description |
|---|---|---|
| `squadName` | string | Squad identifier |
| `clawRole` | string | Role: `content`, `ops`, `analytics`, `finance`, `build` |
| `template` | string | Template ID (e.g., `solo-founder`) |
| `solo` | boolean | Solo mode flag |
| `meshMembers` | string[] | Array of claw roles in mesh |
| `meshSecret` | string \| null | Encrypted shared secret for mesh auth (prefix `enc:v1:`) |
| `operatorName` | string | Human operator name |
| `warRoomMode` | string | `full`, `minimal`, or `disabled` |
| `onboardedAt` | string | ISO timestamp of onboarding |
| `initializedAt` | string | ISO timestamp of initialization |
| `blueprintVersion` | string | Current blueprint version |
| `serverUrl` | string \| null | Payment API server URL |

### Configuration Encryption

Sensitive fields are automatically encrypted using AES-256-GCM:

**Encrypted fields:**
- `meshSecret`
- `apiKey`
- `apiToken`
- `accessToken`
- `refreshToken`

**Encryption characteristics:**
- Encrypted values prefixed with `enc:v1:`
- Key derived from machine ID (Linux: `/etc/machine-id`, macOS: hardware UUID)
- Backwards compatible: plaintext values are read as-is
- Automatic encryption on save, transparent decryption on load

**Legacy State File (`~/.milimo/state.json`):**

Previously created by `milimo init`. Automatically migrated to `config.json` on first load. The legacy file is removed after successful migration.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MILIMO_SERVER_URL` | Payment API server URL | `https://api.milimoclaw.com` |
| `MILIMO_BLUEPRINT_DIR` | Blueprint directory path | `/opt/milimo-blueprint` |

### Server URL Configuration

The payment API URL is resolved in this order:

1. `MILIMO_SERVER_URL` environment variable
2. `serverUrl` in `config.json`
3. Default: `https://api.milimoclaw.com`

For local development, set:
```bash
export MILIMO_SERVER_URL=http://localhost:3001
```

### Audit Trail (`~/.milimo/audit/<squadId>/audit.jsonl`)

JSONL-formatted log of every War Room decision and claw action.

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
