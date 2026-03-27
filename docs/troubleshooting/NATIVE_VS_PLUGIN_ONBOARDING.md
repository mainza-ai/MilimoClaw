# Native vs Plugin Onboarding

## The Critical Difference

**Native onboarding** (`nemoclaw onboard` on HOST) is NOT the same as **plugin onboarding** (`openclaw nemoclaw onboard` inside sandbox).

| Aspect | Native Onboarding | Plugin Onboarding |
|--------|-------------------|-------------------|
| **Location** | Host machine | Inside sandbox |
| **Steps** | 7 | 5 |
| **Creates Gateway** | ✅ Yes | ❌ No |
| **Creates Sandbox** | ✅ Yes | ❌ No |
| **Applies Policies** | ✅ Yes | ❌ No |
| **Configures Inference** | ✅ Full | ⚠️ Partial |

---

## Native Onboarding (7-Step Wizard)

Run on the **HOST machine**:

```bash
export NVIDIA_API_KEY="nvapi-your-key"
nemoclaw onboard
```

### Steps

1. **Preflight** — Check Docker, OpenShell CLI, ports
2. **Gateway** — `openshell gateway start --name nemoclaw`
3. **Sandbox** — `openshell sandbox create --name my-assistant`
4. **NIM** — Choose inference provider (cloud/ollama/vllm)
5. **Inference** — `openshell provider create` + `openshell inference set`
6. **OpenClaw** — Configure OpenClaw inside sandbox
7. **Policies** — Apply network policies (pypi, npm, etc.)

### What It Creates

```
~/.config/openshell/gateways/nemoclaw/
├── metadata.json      # Gateway connection info
└── mtls/
    ├── ca.crt         # Gateway CA certificate
    ├── client.crt     # Client certificate
    └── client.key     # Client key
```

---

## Plugin Onboarding (5-Step Wizard)

Run **inside sandbox**:

```bash
openclaw nemoclaw onboard
```

### Steps

1. Select endpoint type (build, ncp, ollama, vllm, nim-local)
2. Enter API key
3. Select model
4. Validate credential
5. Save config

### What It Does

- Saves config to `~/.nemoclaw/config.json`
- Calls `openshell provider create` (if gateway exists)
- Sets inference route

### What It Does NOT Do

- ❌ Create gateway
- ❌ Create sandbox
- ❌ Apply network policies
- ❌ Set up mTLS certificates

---

## When to Use Which

### Use Native Onboarding When:

- First-time setup
- Creating a new sandbox
- Gateway not running
- Need full configuration

### Use Plugin Onboarding When:

- Reconfiguring inference provider
- Changing model
- Already inside sandbox with working gateway

---

## The Mistake We Made

We ran plugin onboarding (`openclaw nemoclaw onboard`) in a container that:
- Had no gateway connection
- Had no sandbox created
- Had no network policies

This resulted in inference failures because the OpenShell infrastructure was missing.

---

## Correct Flow

```
HOST MACHINE                         SANDBOX
    │                                   │
    ▼                                   │
┌─────────────────┐                     │
│ nemoclaw        │                     │
│ onboard         │                     │
│ (7-step)        │                     │
└────────┬────────┘                     │
         │                              │
         │  Creates:                    │
         │  ├─ Gateway                  │
         │  ├─ Sandbox ────────────────▶│
         │  └─ Policies                 │
         │                              │
         │                              ▼
         │                     ┌─────────────────┐
         │                     │ openclaw        │
         │                     │ milimo onboard  │
         │                     │ (MilimoClaw)    │
         └─────────────────────┴─────────────────┘
```

---

## Quick Reference

```bash
# NATIVE (on HOST)
nemoclaw onboard          # Full 7-step setup

# PLUGIN (inside SANDBOX)
openclaw nemoclaw onboard  # Reconfigure inference only
openclaw milimo onboard    # MilimoClaw-specific setup
```
