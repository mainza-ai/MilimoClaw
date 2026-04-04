# Telegram Setup Guide

## Overview

MilimoClaw uses NemoClaw's **Telegram bridge** — an auxiliary service that runs on the host machine and forwards messages between your Telegram bot and the agent inside the sandbox. This is **not** configured inside the sandbox.

## Prerequisites

1. **Telegram Bot Token** — Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` to BotFather
   - Follow the prompts to name your bot
   - Copy the token (format: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`)

2. **NemoClaw installed and sandbox running** — The Telegram bridge requires an active sandbox

## Setup

### Step 1: Set the Bot Token

```bash
# Set as environment variable
export TELEGRAM_BOT_TOKEN="your-bot-token-here"

# Or add to your shell profile for persistence
echo 'export TELEGRAM_BOT_TOKEN="your-bot-token-here"' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Start Auxiliary Services

```bash
# This launches the Telegram bridge alongside the sandbox
nemoclaw start

# Verify everything is running
nemoclaw status
```

### Step 3: Test the Connection

1. Open Telegram on your phone or desktop
2. Search for your bot by username
3. Send any message (e.g., "hello")
4. The message should appear in the OpenClaw TUI inside the sandbox

### Step 4: Restrict Access (Optional but Recommended)

By default, anyone who finds your bot can message it. Restrict to your Telegram account:

```bash
# Send a message to your bot first, then get your chat ID from the logs
nemoclaw logs --follow | grep -i "chat_id\|from:"

# Once you have your chat ID, set it
export ALLOWED_CHAT_IDS="your_chat_id_here"

# Restart the bridge
nemoclaw stop
nemoclaw start
```

## Stopping the Bridge

```bash
# Stop the Telegram bridge (sandbox remains running)
nemoclaw stop
```

## Troubleshooting

### Bot Not Responding

1. Check the bridge is running: `nemoclaw status`
2. Check the token is correct: `echo $TELEGRAM_BOT_TOKEN`
3. Check bridge logs: `nemoclaw logs --follow`

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

### "channels.telegram" Config in openclaw.json

**Do NOT manually edit the `channels` section in `/sandbox/.openclaw/openclaw.json`.** The Telegram bridge is managed by `nemoclaw start` on the host, not by OpenClaw's built-in channel system. Manual edits will cause permission conflicts and won't work.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Telegram   │────▶│  Telegram Bridge  │────▶│  OpenClaw    │
│  (your bot) │     │  (host process)   │     │  (sandbox)   │
└─────────────┘     └──────────────────┘     └──────────────┘
```

The bridge is a separate Node.js process launched by `nemoclaw start` that:
1. Polls the Telegram Bot API for new messages
2. Forwards them to the OpenClaw gateway via WebSocket
3. Sends agent responses back to Telegram
