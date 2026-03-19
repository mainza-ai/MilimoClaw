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

## `milimo warroom`

Launch the War Room interactive operator dashboard.

```bash
openclaw milimo warroom [-o <operator>]
```

| Option | Description | Default |
|---|---|---|
| `-o, --operator <name>` | Override operator ID | `local-operator` |

### War Room Commands

Once inside the TUI:

| Command | Description |
|---|---|
| `ls` | List all pending actions in queue |
| `view <id>` | View full details of a pending action (timestamp, route, payload) |
| `approve <id>` | Approve — routes the action to its intended recipient |
| `veto <id>` | Reject — moves the action to rejected queue |
| `hold <id>` | Defer — leaves the action in queue for later review |
| `feed` | View the last 10 entries in the audit trail |
| `help` | Show command help |
| `exit` / `quit` | Leave the War Room (claws continue operating) |

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

Rate limit status is visible in the War Room header.

---

## `/milimo` Slash Command

Available from chat interfaces (Telegram bridge, TUI):

| Command | Description |
|---|---|
| `/milimo` | Show help |
| `/milimo status` | Squad status summary |
| `/milimo roles` | List available claw roles |
| `/milimo mesh` | Show mesh topology |
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

Created by `milimo onboard`. Contains:

```json
{
  "squadName": "my-squad",
  "clawRole": "content",
  "template": "solo-founder",
  "solo": true,
  "meshMembers": ["content"],
  "meshSecret": null,
  "operatorName": "operator",
  "warRoomMode": "full",
  "onboardedAt": "2026-03-19T12:00:00.000Z",
  "initializedAt": "2026-03-19T12:00:00.000Z",
  "blueprintVersion": "0.1.0"
}
```

| Property | Type | Description |
|---|---|---|
| `squadName` | string | Squad identifier |
| `clawRole` | string | Role: `content`, `ops`, `analytics`, `finance`, `build` |
| `template` | string | Template ID (e.g., `solo-founder`) |
| `solo` | boolean | Solo mode flag |
| `meshMembers` | string[] | Array of claw roles in mesh |
| `meshSecret` | string \| null | Shared secret for mesh auth |
| `operatorName` | string | Human operator name |
| `warRoomMode` | string | `full`, `minimal`, or `disabled` |
| `onboardedAt` | string | ISO timestamp of onboarding |

### Legacy State File (`~/.milimo/state.json`)

Created by `milimo init` (legacy). Contains squad configuration, role assignment, template selection, and initialization timestamp.

### Audit Trail (`~/.milimo/audit/<squadId>/audit.jsonl`)

JSONL-formatted log of every War Room decision and claw action.

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
