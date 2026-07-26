---
name: nemoclaw-configure-inference
description: Changes the active inference model without restarting the sandbox. Supports both OpenClaw and Hermes profiles. Use when change inference runtime, inference routing, nemoclaw inference, nemohermes inference, switch model, switch provider, openclaw, openshell.
---

# NemoClaw Configure Inference

Change the active inference model without restarting the sandbox.

## Prerequisites

- A running NemoClaw sandbox.

## Check Current Inference Route

```console
$ nemoclaw inference get
$ nemohermes inference get
```

## Change Model and Provider

```console
$ nemoclaw inference set --model stepfun-ai/step-3.7-flash --provider nvidia-prod
$ nemohermes inference set --model stepfun-ai/step-3.7-flash --provider nvidia-prod
```

No sandbox restart required — the change takes effect immediately.

## Verify the Change

```console
$ nemoclaw <name> status
$ nemohermes <name> status
```

Add `--json` for machine-readable output.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `NVIDIA_INFERENCE_API_KEY` | API key for NVIDIA Endpoints |
| `NEMOCLAW_MODEL` | Default model (used during `onboard`) |
| `NEMOCLAW_INFERENCE_PROVIDER_ID` | Provider ID (v0.0.90+) |

## Related Skills

- `nemoclaw-reference` — Full CLI reference
- `nemohermes-reference` — NemoHermes CLI reference
