# Policy Overview

**Summary**: Sandbox policy structure and enforcement for MilimoClaw.

**Sources**:
- `milimo-blueprint/policies/`

**Last updated**: 2026-04-28

**Tags**: #policies #sandbox #security

---

## Overview

Sandbox policies define what each claw can access — filesystem, network, and process permissions. Policies are enforced by the NemoClaw runtime.

## Policy Files

| Policy | Claw | Purpose |
|--------|------|---------|
| `content-sandbox.yaml` | [[content-claw]] | Content Claw permissions |
| `ops-sandbox.yaml` | [[ops-claw]] | Ops Claw permissions |
| `analytics-sandbox.yaml` | [[analytics-claw]] | Analytics Claw permissions |
| `finance-sandbox.yaml` | [[finance-claw]] | Finance Claw permissions |
| `build-sandbox.yaml` | [[build-claw]] | Build Claw permissions |
| `assistant-sandbox.yaml` | [[assistant-lucy]] | Assistant permissions |

---

## Policy Structure

```yaml
version: 1

filesystem_policy:
  include_workdir: false
  read_only:
    - /usr
    - /lib
    - /sandbox/.openclaw-data/milimo/claws/analytics/reports
  read_write:
    - /sandbox/.openclaw-data/milimo/claws/content
    - /tmp

landlock:
  compatibility: best_effort

process:
  run_as_user: sandbox
  run_as_group: sandbox

network_policies:
  twitter_api:
    name: twitter_api
    endpoints:
      - host: api.twitter.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Filesystem Policy

### Writable Paths

| Path | Purpose |
|------|---------|
| `/tmp` | Temporary files and logs |
| `/sandbox/.openclaw-data/` | Agent state, workspace, plugins, extensions (via symlinks) |
| `/sandbox/.openclaw-data/milimo/` | MilimoClaw plugin data |
| `/sandbox/.nemoclaw/` | Plugin state and config; blueprints are DAC-protected (root-owned) |
| `/sandbox/.openclaw/workspace/` | Agent workspace files (persist across restarts, not across rebuilds) |
| `/dev/null` | Null device (write-only) |

Each claw also has full write access to its own data directory under `.openclaw-data/milimo/claws/`:

| Claw | Mount |
|------|-------|
| Content | `/sandbox/.openclaw-data/milimo/claws/content` |
| Ops | `/sandbox/.openclaw-data/milimo/claws/ops` |
| Analytics | `/sandbox/.openclaw-data/milimo/claws/analytics` |
| Finance | `/sandbox/.openclaw-data/milimo/claws/finance` |
| Build | `/sandbox/.openclaw-data/milimo/claws/build` |
| Assistant | `/sandbox/.openclaw-data/milimo/claws/assistant` |

### Read-Only Paths

> **Note:** `/sandbox` is writable at the container mount level, but **read-only via Landlock** on kernel 5.13+. Only `/sandbox/.openclaw/` is also read-only at the mount level (root-owned, `chattr +i`, SHA256-verified). On kernels without Landlock, `/sandbox` is writable and protection falls back to DAC only. See [Sandbox Hardening](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html) for details.

| Path | Purpose | Level |
|------|---------|-------|
| `/sandbox/` | Agent home directory | Read-only via Landlock; writable at mount level |
| `/sandbox/.openclaw/` | Gateway config, immutable, root-owned, integrity-verified (SHA256) | Read-only at mount level |
| `/usr/` | System binaries | Read-only at mount level |
| `/lib/` | System libraries | Read-only at mount level |
| `/proc/` | Process filesystem | Read-only at mount level |
| `/dev/urandom` | Random device | Read-only at mount level |
| `/app/` | Application directory | Read-only at mount level |
| `/etc/` | System configuration | Read-only at mount level |
| `/var/log/` | System logs | Read-only at mount level |

### Read-Only Cross-Mounts

Analytics Claw's shared report:

```yaml
read_only:
- /sandbox/.openclaw-data/milimo/claws/analytics/reports # All claws can read
```

---

## Network Policy

### API Allowlists

Each claw has specific API access:

| Claw | Allowed APIs |
|------|--------------|
| Content | Twitter, LinkedIn, TikTok, Gmail |
| Ops | Email APIs, Calendly |
| Analytics | Read-only platform analytics, Google Trends |
| Finance | Stripe, payment gateways |
| Build | GitHub (preset), Vercel, Sentry |
| Assistant | NVIDIA (baseline), GitHub (preset), Vercel, Sentry, Stripe |

### Binary Allowlists

Only specific binaries can make network requests:

```yaml
binaries:
  - { path: /usr/bin/python3 }
  - { path: /usr/local/bin/node }
  - { path: /usr/local/bin/gh }
  - { path: /usr/local/bin/openclaw }
```

Binary paths support glob patterns: `/sandbox/.vscode-server/**` matches any executable under that tree.

### protocol: rest — L7 HTTP Inspection

When `protocol: rest` is set on an endpoint, the OpenShell proxy inspects HTTP requests at L7 instead of passing raw TCP. This enables method/path-level access control:

| Field | Values | Purpose |
|-------|--------|---------|
| `protocol` | `rest` (or omit for TCP) | Enable HTTP inspection |
| `enforcement` | `enforce`, `audit` | Block or log-only |
| `access` | `read-only`, `read-write`, `full` | Coarse HTTP access (mutually exclusive with `rules`) |
| `rules` | list of `{allow: {method, path}}` | Fine-grained per-method/path allows |
| `deny_rules` | list of `{method, path}` | Override allow rules — deny takes precedence |

See [[network-egress]] for full examples per claw.

### Policy Tiers

Onboarding prompts for a policy tier (default: Balanced). See [[network-egress#Policy Tiers]] for details.

---

## Process Policy

The sandbox process runs as a dedicated `sandbox:sandbox` user and group with UID/GID 999 (not 1000, not 998). All processes inside the sandbox run as this user. Landlock LSM enforcement restricts filesystem access. Process limits cap the number of spawnable processes (`ulimit -u 512`) to mitigate fork-bomb attacks. Linux capabilities are dropped at two levels:

1. **Container runtime** (`--cap-drop=ALL`): Removes all capabilities at the Docker/K8s level
2. **Entrypoint `capsh` drops**: Additionally removes `cap_net_raw`, `cap_dac_override`, `cap_sys_chroot`, `cap_fsetid`, `cap_setfcap`, `cap_mknod`, `cap_audit_write`, `cap_net_bind_service`

The following 5 capabilities are **retained** (via `cap_add`) for `gosu` user switching: `cap_chown`, `cap_setuid`, `cap_setgid`, `cap_fowner`, `cap_kill`.

### No-New-Privileges Enforcement

OpenShell sets `PR_SET_NO_NEW_PRIVS` using `prctl()` inside the sandbox process. This is a separate `prctl()` call, not part of a seccomp filter. NemoClaw does NOT add its own seccomp BPF filters. This prevents privilege escalation via setuid/setgid binaries — once set, the process and all its descendants cannot gain privileges through execve(). Docker Compose also enforces this at the container level with `security_opt: no-new-privileges:true`.

### Seccomp Filters

OpenShell applies seccomp filters internally as part of the sandbox process setup. NemoClaw does NOT add its own seccomp BPF filters on top of what OpenShell provides. The full set of sandbox protections applied by OpenShell is: seccomp filters, Landlock filesystem restrictions, privilege dropping, network namespace isolation, and no-new-privileges enforcement.

### Landlock LSM

Landlock LSM requires Linux kernel 5.13+ with `CONFIG_SECURITY_LANDLOCK=y`. On macOS Docker Desktop or older kernels, Landlock is silently skipped (`compatibility: best_effort`) and the sandbox falls back to DAC-only protection. Production deployments should use kernel 5.13+.

See [Sandbox Hardening](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html) for details.

---

## Updating Policies

### Dynamic Update (Recommended — non-destructive merge)

```bash
# Add a preset — merges into live policy without dropping existing presets
nemoclaw my-assistant policy-add github --yes

# Remove a preset
nemoclaw my-assistant policy-remove github --yes

# List applied presets
nemoclaw my-assistant policy-list
```

### Static Update (persists across recreations)

```bash
# Edit baseline, then re-onboard
nemoclaw onboard
```

### Advanced: openshell policy set (full replacement)

> **WARNING**: `openshell policy set` REPLACES the live policy — it does NOT merge. Always snapshot first:

```bash
openshell policy get --full my-assistant > live-policy.yaml
openshell policy set --policy live-policy.yaml my-assistant
```

---

## Verification

### Phase A Tests

```bash
pytest -m phase_a tests/test_phase_a_isolation.py
```

Tests verify:
- Filesystem isolation
- Network egress restrictions
- Cross-mount permissions

---

## Related Pages

- [[sandbox-isolation]] — Isolation details
- [[network-egress]] — Network policy
- [[ground-truth-hierarchy]] — Policy authority
