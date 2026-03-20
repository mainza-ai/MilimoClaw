# MilimoClaw Quick Start Guide

> Get MilimoClaw running on macOS (Apple Silicon) with native NemoClaw onboarding.

---

## Overview

MilimoClaw extends NVIDIA NemoClaw for multi-agent autonomous hustle operations. This guide covers the proper setup flow using **native NemoClaw onboarding**.

**Platform**: macOS Apple Silicon (M1/M2/M3)
**Architecture**: Docker + k3s + NemoClaw sandbox

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **macOS** | Apple Silicon (M1/M2/M3) |
| **Docker Desktop** | Latest version, running |
| **Node.js** | v20.0.0 or later |
| **NVIDIA API Key** | Free tier at [build.nvidia.com](https://build.nvidia.com/) |

---

## Setup Flow

The correct setup order is critical:

```
HOST (macOS)                    SANDBOX (inside k3s)
    │                                   │
    ▼                                   │
┌─────────────────┐                     │
│ 1. Install      │                     │
│    NemoClaw     │                     │
│    (native)     │                     │
└────────┬────────┘                     │
         ▼                              │
┌─────────────────┐                     │
│ 2. Run Native   │                     │
│    Onboarding   │                     │
│    (7-step)     │                     │
└────────┬────────┘                     │
         │                              │
         │  Creates:                    │
         │  ├─ Gateway container        │
         │  ├─ k3s cluster              │
         │  └─ Sandbox pod ────────────▶│
         │                              │
         │                              ▼
         │                     ┌─────────────────┐
         │                     │ 3. Install      │
         │                     │    MilimoClaw   │
         │                     │    Plugin       │
         │                     └────────┬────────┘
         │                              │
         │                              ▼
         │                     ┌─────────────────┐
         │                     │ 4. Run Milimo   │
         │                     │    Onboarding   │
         └─────────────────────┴─────────────────┘
```

---

## Step 1: Install NemoClaw on Host

```bash
cd /Users/mck/Desktop/MilimoClaw/NemoClaw-original-repo
export NVIDIA_API_KEY="nvapi-your-key-here"
./install.sh
```

This installs `nemoclaw` and `openshell` to `/opt/homebrew/bin/`.

---

## Step 2: Run Native Onboarding (7-Step)

**CRITICAL**: Use native onboarding (`nemoclaw onboard`), NOT plugin onboarding (`openclaw nemoclaw onboard`).

### Interactive Mode

```bash
export NVIDIA_API_KEY="nvapi-your-key-here"
nemoclaw onboard
```

### Non-Interactive Mode

```bash
export NVIDIA_API_KEY="nvapi-your-key-here"
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_PROVIDER=cloud
export NEMOCLAW_MODEL="nvidia/nemotron-3-super-120b-a12b"
nemoclaw onboard
```

### What Native Onboarding Does

| Step | Action | Creates |
|------|--------|---------|
| 1. Preflight | Check Docker, OpenShell, ports | — |
| 2. Gateway | `openshell gateway start --name nemoclaw` | Gateway container + k3s |
| 3. Sandbox | `openshell sandbox create --name my-assistant` | Sandbox pod |
| 4. NIM | Choose inference provider | Provider config |
| 5. Inference | Configure model routing | Inference config |
| 6. OpenClaw | Configure inside sandbox | Agent config |
| 7. Policies | Apply network policies | Policy rules |

---

## Step 3: Verify Sandbox

```bash
# Check sandbox status
nemoclaw my-assistant status

# Expected output:
# Sandbox: my-assistant
# Phase: Ready
# Model: nvidia/nemotron-3-super-120b-a12b
# Provider: nvidia-nim
# Policies: pypi, npm
```

---

## Step 4: Set Up Port Forward

```bash
# Forward sandbox port to localhost
openshell forward start --background 18789 my-assistant
```

Access the dashboard at: http://127.0.0.1:18789/

---

## Step 5: Connect to Sandbox

```bash
# Connect to sandbox shell
openshell sandbox connect my-assistant
```

---

## Step 6: Install MilimoClaw Plugin

Inside the sandbox:

```bash
# Check if plugin source exists
ls /tmp/milimo

# Install the plugin
openclaw plugins install /tmp/milimo

# Verify installation
openclaw plugins list
```

If plugin source is not in `/tmp/milimo`, copy it:

```bash
# On HOST (from another terminal)
# Package the plugin
cd /Users/mck/Desktop/MilimoClaw/milimo
tar czf /tmp/milimo.tar.gz .

# Copy to sandbox
kubectl cp /tmp/milimo.tar.gz my-assistant-pod:/tmp/ -n openshell

# Inside sandbox
cd /tmp && tar xzf milimo.tar.gz -C /tmp/milimo
```

---

## Step 7: Run MilimoClaw Onboarding

Inside the sandbox:

```bash
# Run MilimoClaw onboarding
openclaw milimo onboard

# Follow the prompts:
# 1. Select: Solo Founder
# 2. Select: milimoquantum
# 3. Select: Build Claw
```

---

## Step 8: Test Build Claw

Inside the sandbox:

```bash
# Test inference
openclaw agent --agent main --local -m "Hello, what model are you running?" --session-id test

# Test code generation
openclaw agent --agent main --local -m "Write a Python function is_prime(n) with type hints and docstring." --session-id build-test

# Launch TUI
openclaw tui
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ HOST MACHINE (macOS)                                                │
│                                                                     │
│  $ nemoclaw onboard                                                 │
│  └─ Creates gateway + sandbox                                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Docker: openshell-cluster-nemoclaw                           │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ k3s Kubernetes                                         │  │   │
│  │  │                                                        │  │   │
│  │  │  ┌─────────────────┐  ┌────────────────────────────┐  │  │   │
│  │  │  │ openshell-0     │  │ my-assistant (sandbox)     │  │  │   │
│  │  │  │ (gateway)       │  │                            │  │  │   │
│  │  │  │ Port: 30051     │  │ - OpenClaw                 │  │  │   │
│  │  │  └─────────────────┘  │ - MilimoClaw Plugin        │  │  │   │
│  │  │                       │ - Build Claw               │  │  │   │
│  │  │                       └────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Port Forward: 127.0.0.1:18789 → my-assistant                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Common Commands

### Host Machine

```bash
# Check sandbox status
nemoclaw my-assistant status

# List all sandboxes
nemoclaw list

# Check gateway
openshell gateway info

# Port forward
openshell forward start --background 18789 my-assistant
openshell forward stop 18789
```

### Inside Sandbox

```bash
# Connect to sandbox
openshell sandbox connect my-assistant

# Test inference
openclaw agent --agent main --local -m "Hello" --session-id test

# Launch TUI
openclaw tui

# Check plugins
openclaw plugins list

# MilimoClaw commands
openclaw milimo squad status
openclaw milimo warroom
```

---

## Troubleshooting

### "No gateway metadata found"

Gateway config missing. Run native onboarding first:
```bash
nemoclaw onboard
```

### "Connection refused" to gateway

Gateway not running. Check Docker:
```bash
docker ps | grep nemoclaw
openshell gateway info
```

### Dashboard shows "Disconnected"

Browser cannot provide mTLS client certificate. Use TUI instead:
```bash
openshell sandbox connect my-assistant
openclaw tui
```

### Sandbox not ready

Check sandbox phase:
```bash
nemoclaw my-assistant status
openshell sandbox list
```

---

## Key Files

| File | Location | Purpose |
|------|----------|---------|
| Gateway config | `~/.config/openshell/gateways/nemoclaw/` | Gateway connection |
| TLS certs | `~/.config/openshell/gateways/nemoclaw/mtls/` | Client authentication |
| Sandbox config | Inside sandbox at `~/.openclaw/` | Agent configuration |

---

## Next Steps

1. Test Build Claw functionality
2. Explore War Room: `openclaw milimo warroom`
3. Review [Architecture Guide](../milimo-claw-docs/ARCHITECTURE.md)
4. Read [CLI Reference](../milimo-claw-docs/CLI_REFERENCE.md)
