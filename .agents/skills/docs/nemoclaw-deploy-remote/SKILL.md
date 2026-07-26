---
name: nemoclaw-deploy-remote
description: Deploys NemoClaw to a headless Linux server. Covers unattended installation, loopback-only access, policy setup, updates, and recovery after reboot. Supports both OpenClaw and Hermes agent profiles. Use when deploy nemoclaw remote, headless, headless server, nemohermes deploy, remote gpu, deployment, nemoclaw, nemohermes, openshell.
---

# NemoClaw Deploy Remote

Deploy NemoClaw to a remote headless Linux server (provider-neutral).
This replaces the legacy Brev-based deployment workflow.

## Prerequisites

- A Linux server with SSH access (AMD64 or ARM64)
- NVIDIA GPU recommended but not required
- Docker installed on the server
- An NVIDIA API key from [build.nvidia.com](https://build.nvidia.com)

## Step 1: Install NemoClaw on the Server

SSH into the server and run:

```console
$ curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

For non-interactive installation:

```console
$ curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash -s -- --non-interactive
```

## Step 2: Onboard (Headless Mode)

For OpenClaw profile:

```console
$ nemoclaw onboard --headless --name my-sandbox \
    --chat-ui-url https://your-dashboard.example.com
```

For Hermes profile:

```console
$ nemohermes onboard --headless --name my-sandbox \
    --chat-ui-url https://your-dashboard.example.com
```

## Step 3: Verify the Sandbox

```console
$ nemoclaw my-sandbox status
```

## Step 4: Access Remotely

Use SSH tunneling for the dashboard:

```console
$ ssh -L 18790:127.0.0.1:18790 user@your-server
```

Then open http://127.0.0.1:18790/ in your local browser.

## Step 5: Updates and Recovery

Update NemoClaw:

```console
$ nemoclaw update
```

Recover a stopped sandbox:

```console
$ nemoclaw my-sandbox recover
```

## Related Skills

- `nemoclaw-get-started` — Local quickstart
- `nemoclaw-monitor-sandbox` — Sandbox monitoring
- `nemohermes-reference` — NemoHermes CLI reference
