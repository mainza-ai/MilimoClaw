# CLI Commands

**Summary**: Reference for all CLI commands across MilimoClaw, NemoClaw, OpenShell, and in-sandbox OpenClaw.

**Sources**:
- `milimo/src/cli.ts`
- `milimo/src/commands/*.ts`
- NemoClaw official CLI reference (`.agents/skills/docs/nemoclaw-reference/references/commands.md`)
- OpenShell CLI (`.agents/skills/docs/nemoclaw-reference/references/network-policies.md`)
- `milimo-claw-wiki/wiki/security/credential-storage.md`

**Last updated**: 2026-04-29

**Tags**: #cli #commands #nemoclaw #openshell #openclaw #reference

---

## Overview

The CLI surface spans three layers:

1. **MilimoClaw plugin commands** -- `openclaw milimo <subcommand>` (in-sandbox TypeScript plugin)
2. **NemoClaw host commands** -- `nemoclaw` (host-side sandbox management)
3. **OpenShell host commands** -- `openshell` (host-side gateway and policy management)
4. **In-sandbox commands** -- `openclaw` and slash commands (run inside the sandbox)

---

## MilimoClaw Plugin Commands

The MilimoClaw plugin registers `openclaw milimo` subcommands and the `/milimo` slash command. These run inside the NemoClaw sandbox.

### `openclaw milimo` CLI Subcommands

```
openclaw milimo
├── onboard          # Interactive setup
├── init             # Initialize squad
├── squad
│   ├── status       # Show squad topology
│   ├── finals       # Toggle finals mode
│   └── resume       # Resume after finals
├── blueprint
│   ├── fork         # Fork blueprint
│   ├── diff         # Show changes
│   ├── publish      # Publish to registry
│   ├── rollback     # Revert changes
│   ├── list         # List blueprints
│   ├── search       # Search registry
│   ├── merge        # Merge branches
│   └── info         # Show blueprint info
├── warroom          # Launch TUI
├── payment
│   ├── checkout     # Start subscription
│   ├── status       # Show subscription
│   ├── balance      # Show balance
│   ├── history      # Payment history
│   ├── invoice      # Download invoice
│   └── connect      # Connect Stripe
├── verify           # Verify provenance
├── badge            # Generate badges
├── action (planned)
│   ├── approve      # Approve action
│   ├── block        # Block action
│   └── list         # List pending
├── logs (planned)
│   ├── search       # Search logs
│   └── list         # List log files
└── assistant (planned)
    ├── setup        # Configure assistant
    ├── verify       # Verify setup
    └── start        # Start assistant
```

### `/milimo` Slash Command

Available inside the OpenClaw TUI chat interface:

| Subcommand | Description |
|---|---|
| `/milimo status` | Show squad and claw status |
| `/milimo role` | Show current claw role details |
| `/milimo finals` | Show finals mode status |
| `/milimo approve <action_id>` | Approve a pending War Room action |
| `/milimo veto <action_id>` | Block a pending action |
| `/milimo health` | Print one-line health summary per claw |
| `/milimo evolution` | List last tool built by each claw |
| `/milimo` | Show help |

### Key MilimoClaw Commands

#### `milimo onboard`

Interactive setup wizard:
```bash
openclaw milimo onboard \
  --squad my-squad \
  --role content \
  --template solo-founder \
  --solo \
  --operator "John Doe"
```

#### `milimo init`

Initialize new squad:
```bash
openclaw milimo init \
  --squad my-squad \
  --role ops \
  --assistant-name Nova \
  --assistant-emoji 🦀
```

#### `milimo squad status`

Show topology:
```bash
openclaw milimo squad status --json
```

#### `milimo warroom`

Launch TUI:
```bash
openclaw milimo warroom
```

### Common Options

| Option | Description |
|--------|-------------|
| `--squad <name>` | Squad identifier |
| `--role <role>` | Claw role |
| `--template <name>` | Squad template |
| `--solo` | Solo operator mode |
| `--operator <name>` | Operator name |
| `--json` | JSON output |

---

## NemoClaw Host Commands

> Commands sourced from the official NemoClaw CLI reference. All `nemoclaw` commands run on the **host machine** (outside the sandbox).

### Sandbox Lifecycle

#### `nemoclaw <name> connect`

Connect to a sandbox by name.

```bash
nemoclaw my-squad connect
```

#### `nemoclaw <name> destroy`

Stop the NIM container and delete the sandbox. This removes the sandbox from the registry.

```bash
nemoclaw my-squad destroy
```

#### `nemoclaw <name> rebuild`

Upgrade sandbox to current agent version while preserving workspace state. Backs up workspace, destroys old sandbox, recreates with current image via `onboard --resume`, restores workspace. Policy presets are reapplied.

```bash
nemoclaw my-squad rebuild
```

#### `nemoclaw <name> list`

List all registered sandboxes with their model, provider, and policy presets.

```bash
nemoclaw list
```

#### `nemoclaw <name> snapshot`

Take a timestamped snapshot of sandbox state. Stored in `~/.nemoclaw/rebuild-backups/<name>/`.

```bash
nemoclaw my-squad snapshot create
nemoclaw my-squad snapshot create --name pre-upgrade
nemoclaw my-squad snapshot list
nemoclaw my-squad snapshot restore v2
nemoclaw my-squad snapshot restore pre-upgrade
nemoclaw my-squad snapshot restore 2026-04 --to my-squad-copy
```

#### `nemoclaw <name> status`

Show sandbox status, health, and inference configuration.

```bash
nemoclaw my-squad status
nemoclaw my-squad status --json
```

#### `nemoclaw <name> logs`

View sandbox logs. Use `--follow` to stream output in real time.

```bash
nemoclaw my-squad logs
nemoclaw my-squad logs --follow
```

### Policy Management

#### `nemoclaw <name> policy-add <preset>`

Add a policy preset to a sandbox. Presets extend the baseline network policy with additional endpoints.

```bash
nemoclaw my-squad policy-add
nemoclaw my-squad policy-add pypi --yes
```

#### `nemoclaw <name> policy-remove <preset>`

Remove a previously applied policy preset. Shows endpoints that would be removed and prompts for confirmation.

```bash
nemoclaw my-squad policy-remove
nemoclaw my-squad policy-remove --dry-run
nemoclaw my-squad policy-remove --yes
```

#### `nemoclaw <name> policy-list`

List available policy presets and show which ones are applied to the sandbox.

```bash
nemoclaw my-squad policy-list
```

### Channel Management

#### `nemoclaw <name> channels add <channel>`

Store credentials for a messaging channel (`telegram`, `discord`, `slack`) and rebuild sandbox to pick up the new channel.

```bash
nemoclaw my-squad channels add telegram
nemoclaw my-squad channels add discord
nemoclaw my-squad channels add slack
```

#### `nemoclaw <name> channels remove <channel>`

Clear stored credentials for a channel and rebuild sandbox to drop the channel. This is a **host-side only** operation -- `openclaw.json` is read-only at runtime inside the sandbox and cannot be modified directly.

```bash
nemoclaw my-squad channels remove telegram
```

#### `nemoclaw <name> channels stop <channel>`

Pause a single messaging bridge (`telegram`, `discord`, or `slack`) without clearing its credentials. The channel is marked disabled in the per-sandbox registry, and the sandbox is rebuilt so the onboard step skips registering the bridge with the gateway. Credentials stay in the OpenShell gateway store, so a later `channels start` brings the bridge back without re-entering tokens.

```bash
nemoclaw my-squad channels stop telegram
```

#### `nemoclaw <name> channels start <channel>`

Re-enable a channel previously paused with `channels stop`. The channel is removed from the disabled list, the sandbox is rebuilt, and the bridge registers with the gateway again using the stored credentials.

```bash
nemoclaw my-squad channels start telegram
```

#### `nemoclaw <name> channels list`

List the messaging channels NemoClaw knows about with descriptions.

```bash
nemoclaw my-squad channels list
```

### Credential Management

#### `nemoclaw credentials list`

List provider credential names registered with the OpenShell gateway (values not printed). This is equivalent to `openshell provider list`.

```bash
nemoclaw credentials list
```

#### `nemoclaw credentials reset <PROVIDER>`

Remove a provider credential from the OpenShell gateway. Any subsequent inference requests to that provider will fail until a new credential is registered.

```bash
nemoclaw credentials reset openai
```

### Configuration

#### `nemoclaw config rotate-token`

Rotate the **sandbox-side OpenClaw auth token**. This does **not** rotate provider credentials. Provider credential rotation requires re-onboarding with the new value.

```bash
nemoclaw config rotate-token
```

#### `nemoclaw <name> gateway-token`

Print the OpenClaw gateway auth token. Use `--quiet` to suppress the security warning.

```bash
nemoclaw my-squad gateway-token
nemoclaw my-squad gateway-token --quiet
```

### Setup and Deployment

#### `nemoclaw onboard`

Run the interactive setup wizard. The wizard creates an OpenShell gateway, registers inference providers, builds the sandbox image, and creates the sandbox.

```bash
nemoclaw onboard
```

Key flags:

| Flag | Description |
|------|-------------|
| `--resume` | Resume onboarding with existing configuration (used by `nemoclaw rebuild`) |
| `--recreate-sandbox` | Destroy and recreate the sandbox (required for cross-provider inference switches) |
| `--non-interactive --yes-i-accept-third-party-software` | Non-interactive mode (use with `NEMOCLAW_POLICY_TIER` env var) |

Cross-provider switching example:

```bash
NEMOCLAW_MODEL_OVERRIDE=openai/gpt-5.4 \
NEMOCLAW_INFERENCE_API_OVERRIDE=openai-completions \
nemoclaw onboard --resume --recreate-sandbox
```

#### `nemoclaw deploy`

Deploy NemoClaw to a remote GPU instance through Brev. Reads credentials from environment variables only -- the gateway cannot act as a credential source for new deployments.

```bash
nemoclaw deploy <instance-name>
```

#### `nemoclaw uninstall`

Remove sandboxes, gateway, images, and local state.

```bash
nemoclaw uninstall --yes
nemoclaw uninstall --yes --keep-openshell
nemoclaw uninstall --yes --delete-models
```

### Maintenance

#### `nemoclaw backup-all`

Back up all running sandboxes to `~/.nemoclaw/rebuild-backups/`.

```bash
nemoclaw backup-all
```

#### `nemoclaw upgrade-sandboxes`

Rebuild sandboxes whose base image is older than current.

```bash
nemoclaw upgrade-sandboxes --check
nemoclaw upgrade-sandboxes --auto --yes
```

#### `nemoclaw gc`

Remove orphaned sandbox Docker images.

```bash
nemoclaw gc
nemoclaw gc --dry-run
nemoclaw gc --yes
```

### Diagnostics

#### `nemoclaw debug`

Collect diagnostics for bug reports.

```bash
nemoclaw debug
nemoclaw debug --quick
nemoclaw debug --sandbox my-squad --output ./debug-output
```

#### `nemoclaw <name> skill install <path>`

Deploy a skill directory to a running sandbox. Validates `SKILL.md` frontmatter, uploads files, and refreshes agent session index.

```bash
nemoclaw my-squad skill install ./skills/my-skill
```

### Tunnel (Auxiliary Services)

#### `nemoclaw tunnel start`

Start optional host auxiliary services (e.g., cloudflared tunnel when `cloudflared` is installed for a public URL to the dashboard). Channel messaging is not started here; it is configured during `nemoclaw onboard`.

```bash
nemoclaw tunnel start
```

`nemoclaw start` remains as a deprecated alias that prints a warning and delegates to `tunnel start`.

#### `nemoclaw tunnel stop`

Stop host auxiliary services started by `nemoclaw tunnel start`. This does not affect messaging channels running inside the sandbox; use `nemoclaw <name> channels stop <channel>` to pause a specific bridge.

```bash
nemoclaw tunnel stop
```

`nemoclaw stop` remains as a deprecated alias that prints a warning and delegates to `tunnel stop`.

### Version

#### `nemoclaw --version` / `nemoclaw -v`

Print installed CLI version.

```bash
nemoclaw --version
nemoclaw -v
```

---

## OpenShell Host Commands

> OpenShell CLI commands run on the **host machine**. They manage the gateway, policy, providers, and port forwarding.

### Policy Management

#### `openshell policy get` / `openshell policy get --full`

View the current live policy. Use `--full` to dump the complete running policy (baseline plus all presets) to stdout.

```bash
openshell policy get my-squad
openshell policy get --full my-squad > live-policy.yaml
```

#### `openshell policy set`

> **WARNING:** `openshell policy set` **replaces** the sandbox's live policy with the contents of the file you provide; it does **not** merge. A running sandbox's live policy is the baseline plus every preset layered on during onboarding. Applying a file that contains only the baseline silently drops every other preset. If you must use this path, snapshot the live policy first with `openshell policy get --full`, edit, then apply.

```bash
openshell policy set --policy live-policy.yaml my-squad
```

For structured merges that preserve existing presets, prefer `nemoclaw <name> policy-add` instead.

### Provider Management

#### `openshell provider list`

List registered providers (same as `nemoclaw credentials list`). Credential values cannot be read back from the CLI.

```bash
openshell provider list
```

#### `openshell provider create` / `openshell provider update`

Register or update provider credentials in the OpenShell gateway store. Values are held in process memory only for the duration of the operation and then stored in the gateway. They are never written to disk.

```bash
openshell provider create
openshell provider update
```

### Inference Management

#### `openshell inference set`

Change the active inference routing and model while the sandbox is running. No restart is required.

```bash
openshell inference set --provider nvidia-nim --model nvidia/nemotron-3-super-120b-a12b
```

### Monitoring

#### `openshell term`

Open the OpenShell TUI to monitor sandbox activity and approve network egress requests. Run this on the host where the sandbox is running. For a remote Brev instance, SSH to the instance and run `openshell term` there, or use a port-forward to the gateway.

```bash
openshell term
```

### Port Forwarding

#### `openshell forward start <port>`

Start port forwarding to a sandbox. Use `--background` to run in the background.

```bash
openshell forward start --background 18789 my-squad
```

#### `openshell forward list`

List active port forwards.

```bash
openshell forward list
```

#### `openshell forward stop <port>`

Stop an active port forward.

```bash
openshell forward stop 18789
```

---

## In-Sandbox Commands

> These commands run **inside the NemoClaw sandbox** after connecting via `nemoclaw <name> connect`.

### OpenClaw Interface

#### `openclaw tui`

Start the OpenClaw TUI -- the main interactive chat interface with the agent.

```bash
openclaw tui
```

#### `openclaw agent`

Run the agent in headless mode. Prints the complete response directly in the terminal. Useful for scripted interactions or long output.

```bash
openclaw agent --agent main --local -m "hello" --session-id test
```

### Plugin Management

#### `openclaw plugins install <path>`

Install a plugin from a local path into the OpenClaw plugin registry. Validates the plugin manifest and registers it with the gateway.

```bash
openclaw plugins install /sandbox/extensions/milimo
```

#### `openclaw plugins allow <id>`

Allow a blocked plugin that was flagged by OpenClaw's supply chain scanner. Critical findings block installation entirely; this command overrides the block for a specific plugin.

```bash
openclaw plugins allow <plugin-id>
```

#### `openclaw plugins list`

List loaded plugins and their status.

```bash
openclaw plugins list
```

### Security

#### `openclaw security audit`

Run 50+ distinct security check types including synced-folder leak detection, plaintext secrets scanning, hooks hardening validation, gateway no-auth detection, sandbox misconfiguration checks, weak-model susceptibility analysis, and more. Run regularly and before any production deployment.

```bash
openclaw security audit
```

### Slash Commands

| Command | Description |
|---|---|
| `/milimo` | MilimoClaw slash command -- squad management (see [[#`/milimo` Slash Command]] above) |
| `/nemoclaw status` | Show sandbox and inference state |
| `/nemoclaw onboard` | Show onboarding status and reconfiguration guidance |
| `/nemoclaw eject` | Show rollback instructions for returning to host installation |

---

## Credential Storage

> **Important:** As of recent NemoClaw releases, provider credentials are stored in the **OpenShell gateway store**, not in `~/.nemoclaw/credentials.json`. The legacy `credentials.json` file is automatically migrated and deleted during `nemoclaw onboard`. Do not rely on or edit the legacy file directly. Environment variables take precedence over stored credentials. `nemoclaw config rotate-token` rotates the **sandbox-side OpenClaw auth token** only -- it does **not** rotate provider credentials. Provider credential rotation requires re-onboarding with the new value.

---

## Environment Variables (v0.0.29)

### Core Inference

| Variable | Default | Description |
|----------|---------|-------------|
| `NEMOCLAW_MODEL` | (set during onboard) | Model identifier for inference routing |
| `NEMOCLAW_MODEL_OVERRIDE` | — | Override model for cross-provider switch |
| `NEMOCLAW_INFERENCE_API_OVERRIDE` | — | API format for cross-provider: `openai-completions` or `anthropic-messages` |
| `NEMOCLAW_PREFERRED_API` | `openai-responses` | Preferred API protocol (new in v0.0.29) |

### Context and Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `NEMOCLAW_CONTEXT_WINDOW` | `65536` | Maximum context window (tokens) |
| `NEMOCLAW_MAX_TOKENS` | `4096` | Maximum output tokens per request |
| `NEMOCLAW_REASONING` | — | Enable reasoning mode (`true`/`false`) |
| `NEMOCLAW_INFERENCE_INPUTS` | `text` | Accepted input types: `text` or `text,image` |

### Timeouts

| Variable | Default | Description |
|----------|---------|-------------|
| `NEMOCLAW_AGENT_TIMEOUT` | `600` | Agent-level timeout (seconds) |
| `NEMOCLAW_LOCAL_INFERENCE_TIMEOUT` | `180` | Local inference timeout (seconds) |

### Proxy and Experimental

| Variable | Default | Description |
|----------|---------|-------------|
| `NEMOCLAW_PROXY_HOST` | — | HTTP proxy host for outbound requests |
| `NEMOCLAW_PROXY_PORT` | — | HTTP proxy port |
| `NEMOCLAW_EXPERIMENTAL` | — | Set to `1` to enable experimental providers (NIM, vLLM) |
| `NEMOCLAW_FRESH` | — | Force fresh inference session (bypass cache) |

---

## Source Files

| File | Commands |
|------|----------|
| `commands/onboard.ts` | `onboard` |
| `commands/init.ts` | `init` |
| `commands/squad.ts` | `squad status\|finals\|resume` |
| `commands/blueprint.ts` | `blueprint fork\|diff\|publish\|...` |
| `commands/warroom.ts` | `warroom` |
| `commands/payment.ts` | `payment checkout\|status\|...` |
| `commands/verify.ts` | `verify` |
| `commands/action.ts` | `action approve\|block\|list` |
| `commands/logs.ts` | `logs search\|list` |
| `commands/assistant.ts` | `assistant setup\|verify\|start` |
| `commands/slash.ts` | `/milimo` slash command handler |

---

## Related Pages

- [[warroom-tui]] -- TUI documentation
- [[bridge-tools]] -- Python bridge
- [[onboard-flows]] -- Onboarding flows
- [[credential-storage]] -- Credential storage and rotation
- [[network-egress]] -- Network policy and egress rules
- [[policy-overview]] -- Policy tiers and presets
