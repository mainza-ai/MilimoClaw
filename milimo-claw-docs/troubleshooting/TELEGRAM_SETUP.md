# Telegram Setup Guide

## Overview

MilimoClaw uses NemoClaw's **OpenShell-managed channel messaging** for Telegram integration. Telegram is configured during `nemoclaw onboard` and runs through OpenShell gateway constructs — **not** via a separate host-side bridge process or direct API polling from the sandbox.

Per the official NemoClaw docs (docs.nvidia.com/nemoclaw/latest/deployment/set-up-telegram-bridge.html):

> Channel messaging (Telegram, Discord, Slack) is not started [by `nemoclaw tunnel start`]; it is configured during `nemoclaw onboard` and runs through OpenShell-managed constructs.

The agent inside the sandbox **never** calls `api.telegram.org` directly. OpenShell intercepts messaging platform APIs and delivers messages to the agent through its channel messaging subsystem. Outbound responses flow back through the same OpenShell-managed path.

## Architecture

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐
│ Telegram     │────▶│ OpenShell Gateway     │────▶│ OpenClaw     │
│ (your bot)   │    │ (channel messaging)   │    │ (sandbox)    │
└──────────────┘     └──────────────────────┘     └──────────────┘
```

Flow:
1. Telegram Bot API → OpenShell gateway (platform webhooks or polling)
2. OpenShell channel messaging validates and delivers to agent
3. Agent responds → OpenShell gateway → Telegram Bot API

The sandbox receives **placeholder credentials**, not raw tokens. The L7 proxy injects real credentials at egress.

## Prerequisites

1. **Telegram Bot Token** — Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` to BotFather
   - Follow the prompts to name your bot
   - Copy the token (format: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`)

2. **NemoClaw installed** — `nemoclaw` CLI available on host

## Setup

### Step 1: Provide the Bot Token

```bash
# Option A: Environment variable (before running nemoclaw onboard)
export TELEGRAM_BOT_TOKEN="your-bot-token-here"

# Option B: Enter interactively during nemoclaw onboard
# The wizard prompts for the token if not found in env or credential store
```

### Step 2: Run `nemoclaw onboard`

```bash
nemoclaw onboard
```

During onboarding:
1. The wizard shows **Messaging channels** — toggle Telegram on (press 1)
2. If `TELEGRAM_BOT_TOKEN` is not in env/credential store, the wizard prompts for it
3. Optionally set `TELEGRAM_ALLOWED_IDS` for DM access control
4. NemoClaw creates an OpenShell provider (`<sandbox>-telegram-bridge`)
5. Channel config is baked into the sandbox image (`NEMOCLAW_MESSAGING_CHANNELS_B64`)

**Important:** Channel entries in `/sandbox/.openclaw/openclaw.json` are fixed at image build time. Landlock keeps that path read-only at runtime. To change Telegram config after a sandbox exists, run `nemoclaw onboard` again.

### Step 3: Confirm Delivery

1. Open Telegram on your phone or desktop
2. Search for your bot by username
3. Send any message (e.g., "hello")
4. The message should appear in the OpenClaw TUI inside the sandbox

If something fails, use `openshell term` on the host to check gateway logs and verify network policy allows the Telegram API.

## Pausing and Resuming

```bash
# Pause Telegram without removing credentials (requires sandbox rebuild)
nemoclaw my-assistant channels stop telegram

# Resume Telegram
nemoclaw my-assistant channels start telegram
```

Use `channels stop` for temporary pauses. Use `channels remove` only when you want to clear stored credentials entirely.

## Cloudflared Tunnel (Not Telegram)

```bash
# This only starts cloudflared for a public dashboard URL — NOT Telegram
nemoclaw tunnel start

# Deprecated alias (prints warning, delegates to tunnel start)
nemoclaw start
```

`nemoclaw tunnel start` does **not** affect Telegram connectivity. It only starts optional cloudflared tunneling for the dashboard.

## Restricting Access

By default, anyone who finds your bot can message it. Restrict to specific Telegram accounts:

```bash
# Option A: Environment variable before onboard
export TELEGRAM_ALLOWED_IDS="123456789,987654321"

# Option B: Enter interactively during nemoclaw onboard
# The wizard prompts for "Telegram User ID (for DM access)"
```

Per NemoClaw docs: "NemoClaw applies that allowlist to Telegram DMs only. Group chats stay open by default so rebuilt sandboxes do not silently drop Telegram group messages because of an empty group allowlist."

## Troubleshooting

### Bot Not Responding

1. Verify channel is configured: `nemoclaw my-assistant status` — should show Telegram in messaging channels
2. Verify network policy allows `api.telegram.org:443` — the `telegram` preset covers this
3. Check gateway logs: `nemoclaw my-assistant logs --follow`
4. Verify no cross-sandbox token conflict: `nemoclaw my-assistant status` warns if another sandbox uses the same bot token

### "channels.telegram" Config in openclaw.json

**Do NOT manually edit the `channels` section in `/sandbox/.openclaw/openclaw.json`.** It is read-only under Landlock. Changes require re-running `nemoclaw onboard` to rebuild the sandbox image with new channel config.

### 409 Conflict Errors

If you see `409 Conflict` errors in gateway logs, it means two consumers are polling the same Telegram bot token. This happens if:
- Another sandbox uses the same `TELEGRAM_BOT_TOKEN`
- Lucy's old `TelegramBridge` class was polling `api.telegram.org` directly (removed in latest version)

The fix is to ensure only one sandbox uses a given bot token, and that Lucy **never** polls Telegram directly — OpenShell handles all messaging.

### Permission Errors in Sandbox

If you see `EACCES: permission denied` when running `openclaw pairing` commands:

```bash
# Fix from host terminal
docker exec openshell-cluster-nemoclaw kubectl exec -n openshell my-assistant -- bash -c '
rm -rf /sandbox/.openclaw/credentials
mkdir -p /sandbox/.openclaw/credentials
chown 999:999 /sandbox/.openclaw/credentials
chmod 755 /sandbox/.openclaw/credentials
echo "Credentials dir fixed"
'
```

## Key Documentation References

- [NemoClaw Telegram Setup](https://docs.nvidia.com/nemoclaw/latest/deployment/set-up-telegram-bridge.html) — Official NemoClaw docs
- [NemoClaw Architecture](https://docs.nvidia.com/nemoclaw/latest/reference/architecture.html) — System overview showing `MSGAPI → CHMSG → AGENT` flow
- [NemoClaw Commands](https://docs.nvidia.com/nemoclaw/latest/reference/commands.html) — `channels stop/start`, `tunnel start` reference
- [NemoClaw Network Policies](https://docs.nvidia.com/nemoclaw/latest/reference/network-policies.html) — Telegram API allowlist in baseline policy
