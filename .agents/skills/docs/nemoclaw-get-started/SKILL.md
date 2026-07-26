---
name: nemoclaw-get-started
description: Installs NemoClaw, launches a sandbox, and runs your first agent prompt. Covers both OpenClaw and Hermes profiles. Use when install nemoclaw, install nemohermes, launch sandbox, nemoclaw install, nemoclaw quickstart, nemohermes quickstart, openclaw, openshell, sandboxing.
---

# NemoClaw Get Started

Install NemoClaw, launch a sandbox, and run your first agent prompt.

## Quick Install (macOS / Linux)

```console
$ curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

## Onboard (Create a Sandbox)

**OpenClaw profile (TUI):**

```console
$ nemoclaw onboard
```

**Hermes profile (web dashboard):**

```console
$ nemohermes onboard
```

**Non-interactive (Hermes + custom Dockerfile):**

```console
$ NVIDIA_API_KEY="nvapi-..." \
  NEMOCLAW_NON_INTERACTIVE=1 \
  NEMOCLAW_ACCEPT_THIRD_PARTY=1 \
  ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

## Connect to Your Sandbox

```console
$ nemoclaw my-sandbox connect    # OpenClaw
$ nemohermes my-sandbox connect  # Hermes
```

## Common Commands

| Action | OpenClaw | Hermes |
|--------|----------|--------|
| List sandboxes | `nemoclaw list` | `nemohermes list` |
| Sandbox status | `nemoclaw <n> status` | `nemohermes <n> status` |
| Run command | `nemoclaw <n> exec -- <cmd>` | `nemohermes <n> exec -- <cmd>` |
| View logs | `nemoclaw <n> logs` | `nemohermes <n> logs` |
| Destroy | `nemoclaw <n> destroy` | `nemohermes <n> destroy` |

## Related Skills

- `nemoclaw-configure-inference` — Change inference model
- `nemoclaw-manage-policy` — Manage network policies
- `nemoclaw-monitor-sandbox` — Monitor sandbox activity
- `nemoclaw-reference` — Full CLI reference
- `nemohermes-reference` — NemoHermes CLI reference
