---
name: nemoclaw-manage-policy
description: Manages sandbox network policies using the NemoClaw/NemoHermes CLI. Covers applying presets, adding custom endpoints, and managing running sandbox egress. Use when approve deny network, customize network policy, customize sandbox network, nemoclaw, nemohermes, nemoclaw policy, nemohermes policy, network policy, openshell.
---

# NemoClaw Manage Policy

Manage sandbox network policies using `nemoclaw <name> policy-add` and related commands.

## Prerequisites

- A running NemoClaw sandbox (OpenClaw or Hermes profile).

## List Current Policies

```console
$ nemoclaw <name> policy-list
$ nemohermes <name> policy-list
```

## Apply a Policy Preset

NemoClaw ships preset policy files for common integrations.
MilimoClaw presets are in `milimo-blueprint/policies/presets/`:

| Preset | Endpoints |
|--------|-----------|
| `nous-portal` | portal.nousresearch.com, inference-api.nousresearch.com |
| `sentry` | sentry.io, *.ingest.sentry.io |
| `stripe-link` | api.link.com, login.link.com, app.link.com |
| `stripe` | api.stripe.com |
| `vercel` | api.vercel.com |

Apply a preset to a running sandbox:

```console
$ nemoclaw <name> policy-add --from-file milimo-blueprint/policies/presets/nous-portal.yaml
```

## Add a Custom Endpoint

Create a YAML file and apply it:

```yaml
name: my-custom-service
endpoints:
  - host: "api.example.com"
    port: 443
    protocol: rest
```

```console
$ nemoclaw <name> policy-add --from-file my-policy.yaml
```

## Remove a Policy

```console
$ nemoclaw <name> policy-remove my-custom-service
```

## Check Sandbox Status

```console
$ nemoclaw <name> status
```

## Related Skills

- `nemoclaw-reference` — Full CLI reference
- `nemoclaw-monitor-sandbox` — Sandbox monitoring
