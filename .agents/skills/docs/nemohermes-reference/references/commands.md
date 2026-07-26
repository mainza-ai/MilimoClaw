# NemoHermes CLI Commands

## Global Commands

| Command | Description |
|---------|-------------|
| `nemohermes onboard` | Interactive onboarding (inference, credentials, sandbox) |
| `nemohermes onboard --from <Dockerfile>` | Onboard with custom sandbox Dockerfile |
| `nemohermes onboard --agent <agent>` | Choose agent runtime (hermes, openclaw, deep-agents-code) |
| `nemohermes agents list` | List available agent runtimes |
| `nemohermes list` | List all sandboxes |
| `nemohermes use <name>` | Set default sandbox |
| `nemohermes credentials add <provider>` | Register provider credential |
| `nemohermes credentials list` | List stored credential providers |
| `nemohermes credentials reset <provider>` | Remove provider credential |
| `nemohermes backup-all` | Back up all sandbox state before upgrade |
| `nemohermes update` | Run NemoHermes installer update |
| `nemohermes upgrade-sandboxes` | Detect and rebuild stale sandboxes |
| `nemohermes resources` | Show hardware inventory (CPU, RAM, GPU) |
| `nemohermes gc` | Remove orphaned sandbox Docker images |
| `nemohermes uninstall` | Run uninstall.sh |
| `nemohermes debug` | Collect diagnostics for bug reports |

## Sandbox-Scoped Commands

| Command | Description |
|---------|-------------|
| `nemohermes <name> connect` | Shell into a running sandbox |
| `nemohermes <name> dashboard-url` | Print dashboard URL |
| `nemohermes <name> recover` | Repair stopped sandbox gateway |
| `nemohermes <name> status` | Show sandbox health and runtime status |
| `nemohermes <name> exec -- <cmd>` | Run command non-interactively in sandbox |
| `nemohermes <name> agent [flags]` | Run one agent turn non-interactively |
| `nemohermes <name> download <path>` | Download file from sandbox |
| `nemohermes <name> upload <path>` | Upload file to sandbox |
| `nemohermes <name> doctor` | Diagnose sandbox and gateway health |
| `nemohermes <name> logs` | Stream sandbox logs |
| `nemohermes <name> snapshot create` | Create sandbox state snapshot |
| `nemohermes <name> snapshot list` | List available snapshots |
| `nemohermes <name> snapshot restore` | Restore state from snapshot |
| `nemohermes <name> share mount` | Mount sandbox filesystem on host |
| `nemohermes <name> share unmount` | Unmount shared sandbox filesystem |
| `nemohermes <name> share status` | Show share mount status |
| `nemohermes <name> gateway-token --quiet` | Get sandbox API bearer token |
| `nemohermes <name> destroy --yes` | Destroy sandbox (add NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 to skip backup) |
| `nemohermes <name> shields up` | Lock sandbox config for sensitive workloads |
| `nemohermes <name> policy-add` | Apply network policy presets |
| `nemohermes <name> policy-list` | List applied network policies |
| `nemohermes <name> policy-remove` | Remove network policy |
| `nemohermes inference get` | Check current inference route |
| `nemohermes inference set --model <m> --provider <p>` | Change inference model/provider |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `NVIDIA_INFERENCE_API_KEY` | API key for NVIDIA Endpoints (required for non-interactive) |
| `NEMOCLAW_NON_INTERACTIVE` | Set to `1` for non-interactive mode |
| `NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE` | Set to `1` to accept third-party software |
| `NEMOCLAW_RECREATE_SANDBOX` | Set to `1` to recreate existing sandbox |
| `NEMOCLAW_RECREATE_WITHOUT_BACKUP` | Set to `1` to skip backup during recreate |
| `NEMOCLAW_POLICY_TIER` | Policy tier: `restricted`, `balanced`, `open` |
| `NEMOCLAW_MODEL` | Default inference model |
| `NEMOCLAW_INFERENCE_PROVIDER_ID` | Inference provider ID (v0.0.90+) |
| `NEMOCLAW_AUTH_MODE` | Auth mode: `api_key` or `nous_oauth` |
| `NEMOCLAW_AGENT` | Agent profile: `hermes` (for nemohermes) |
