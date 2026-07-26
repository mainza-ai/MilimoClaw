---
name: nemoclaw-monitor-sandbox
description: Inspects sandbox health, traces agent behavior, and diagnoses problems. Supports both OpenClaw and Hermes profiles. Use when debug nemoclaw, debug nemohermes, monitor sandbox, nemoclaw status, nemohermes status, nemoclaw logs, nemohermes logs, troubleshooting, openshell.
---

# NemoClaw Monitor Sandbox

Inspect sandbox health, trace agent behavior, and diagnose problems.

## Check Sandbox Health

```console
$ nemoclaw <name> status
$ nemohermes <name> status
```

## View Logs

```console
$ nemoclaw <name> logs              # Recent logs
$ nemoclaw <name> logs --follow     # Real-time streaming
$ nemohermes <name> logs --tail 100 # Last 100 lines
```

## Doctor / Diagnostics

```console
$ nemoclaw <name> doctor
$ nemohermes <name> doctor --json
```

## Debug (Collect Diagnostics)

```console
$ nemoclaw debug --output /tmp/nemoclaw-debug.tar.gz
$ nemohermes debug --quick
```

## Snapshot Management

```console
$ nemoclaw <name> snapshot create --name before-upgrade
$ nemoclaw <name> snapshot list
$ nemoclaw <name> snapshot restore before-upgrade
```

## Test Inference

```console
$ nemohermes <name> agent --local -m "Hello, world" --session-id test
```

## Recovery

```console
$ nemohermes <name> recover
$ nemohermes <name> shields up    # Lock config for sensitive workloads
```

## Related Skills

- `nemoclaw-reference` — Full CLI reference
- `nemohermes-reference` — NemoHermes CLI reference
- `nemoclaw-manage-policy` — Network policy management
