# Commands

The `nemoclaw` CLI is the primary interface for managing NemoClaw sandboxes. It is installed when you run `npm install -g nemoclaw`.

### `/nemoclaw` Slash Command

The `/nemoclaw` slash command is available inside the OpenClaw chat interface for quick actions:

| Subcommand | Description |
|---|---|
| `/nemoclaw status` | Show sandbox and inference state |

## Standalone Host Commands

The `nemoclaw` binary handles host-side operations that run outside the OpenClaw plugin context.

### `nemoclaw onboard`

Run the interactive setup wizard.
The wizard creates an OpenShell gateway, registers inference providers, builds the sandbox image, and creates the sandbox.
Use this command for new installs and for recreating a sandbox after changes to policy or configuration.

```console
$ nemoclaw onboard
```

The first run prompts for your NVIDIA API key and registers it with the OpenShell gateway. `~/.nemoclaw/credentials.json` is a legacy file from earlier releases; on first `nemoclaw onboard` after upgrading, NemoClaw auto-migrates credentials from that file to the gateway and securely deletes it.

The wizard prompts for a sandbox name.
Names must follow RFC 1123 subdomain rules: lowercase alphanumeric characters and hyphens only, and must start and end with an alphanumeric character.
Uppercase letters are automatically lowercased.

Before creating the gateway, the wizard runs preflight checks.
On systems with cgroup v2 (Ubuntu 24.04, DGX Spark, WSL2), it verifies that Docker is configured with `"default-cgroupns-mode": "host"` and provides fix instructions if the setting is missing.

### `nemoclaw list`

List all registered sandboxes with their model, provider, and policy presets.

```console
$ nemoclaw list
```

### `nemoclaw deploy`

> **Warning:** The `nemoclaw deploy` command is experimental and may not work as expected.

Deploy NemoClaw to a remote GPU instance through [Brev](https://brev.nvidia.com).
The deploy script installs Docker, NVIDIA Container Toolkit if a GPU is present, and OpenShell on the VM, then runs the nemoclaw setup and connects to the sandbox.

```console
$ nemoclaw deploy <instance-name>
```

### `nemoclaw <name> connect`

Connect to a sandbox by name.

```console
$ nemoclaw my-assistant connect
```

### `nemoclaw <name> status`

Show sandbox status, health, and inference configuration.

```console
$ nemoclaw my-assistant status
```

### `nemoclaw <name> logs`

View sandbox logs.
Use `--follow` to stream output in real time.

```console
$ nemoclaw my-assistant logs [--follow]
```

### `nemoclaw <name> destroy`

Stop the NIM container and delete the sandbox.
This removes the sandbox from the registry.

```console
$ nemoclaw my-assistant destroy
```

### `nemoclaw <name> policy-add`

Add a policy preset to a sandbox.
Presets extend the baseline network policy with additional endpoints.

```console
$ nemoclaw my-assistant policy-add
```

### `nemoclaw <name> policy-list`

List available policy presets and show which ones are applied to the sandbox.

```console
$ nemoclaw my-assistant policy-list
```

### `openshell term`

Open the OpenShell TUI to monitor sandbox activity and approve network egress requests.
Run this on the host where the sandbox is running.

```console
$ openshell term
```

For a remote Brev instance, SSH to the instance and run `openshell term` there, or use a port-forward to the gateway.

### `nemoclaw tunnel start`

Start optional host auxiliary services. This is the cloudflared tunnel when `cloudflared` is installed (for a public URL to the dashboard). Channel messaging (Telegram, Discord, Slack) is not started here; it is configured during `nemoclaw onboard` and runs through OpenShell-managed constructs.

```console
$ nemoclaw tunnel start
```

`nemoclaw start` remains as a deprecated alias that prints a warning and delegates to `tunnel start`.

### `nemoclaw tunnel stop`

Stop host auxiliary services started by `nemoclaw tunnel start` (for example cloudflared). This does not affect messaging channels running inside the sandbox; use `nemoclaw <name> channels stop <channel>` to pause a specific bridge without destroying the sandbox.

```console
$ nemoclaw tunnel stop
```

`nemoclaw stop` remains as a deprecated alias that prints a warning and delegates to `tunnel stop`.

### `nemoclaw <name> channels stop <channel>`

Pause a single messaging bridge (`telegram`, `discord`, or `slack`) without clearing its credentials. The channel is marked disabled in the per-sandbox registry, and the sandbox is rebuilt so the onboard step skips registering the bridge with the gateway. Credentials stay in the OpenShell gateway store (env vars take precedence), so a later `channels start` brings the bridge back without re-entering tokens. `~/.nemoclaw/credentials.json` is a legacy file that is auto-migrated and deleted on first `nemoclaw onboard` after upgrading.

```console
$ nemoclaw my-assistant channels stop telegram
```

### `nemoclaw <name> channels start <channel>`

Re-enable a channel previously paused with `channels stop`. The channel is removed from the disabled list, the sandbox is rebuilt, and the bridge registers with the gateway again using the stored credentials.

```console
$ nemoclaw my-assistant channels start telegram
```

### `nemoclaw status`

Show the sandbox list and the status of auxiliary services.

```console
$ nemoclaw status
```

### `nemoclaw setup-spark`

> **Warning:** The `nemoclaw setup-spark` command is deprecated. Use the standard installer and run `nemoclaw onboard` instead.

Set up NemoClaw on DGX Spark.
This command applies cgroup v2 and Docker fixes required for Ubuntu 24.04.
Run with `sudo` on the Spark host.
After the fixes complete, the script prompts you to run `nemoclaw onboard` to continue setup.

```console
$ sudo nemoclaw setup-spark
```
