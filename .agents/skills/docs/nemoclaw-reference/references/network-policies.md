# Network Policies

NemoClaw runs with a deny-by-default network policy.
The sandbox can only reach endpoints that are explicitly allowed.
Any request to an unlisted destination is intercepted by OpenShell, and the operator is prompted to approve or deny it in real time through the TUI.

## Baseline Policy

The baseline policy is defined in `nemoclaw-blueprint/policies/openclaw-sandbox.yaml`.

### Filesystem

| Path | Access |
|---|---|
| `/sandbox`, `/tmp`, `/dev/null` | Read-write |
| `/usr`, `/lib`, `/proc`, `/dev/urandom`, `/app`, `/etc`, `/var/log` | Read-only |

> **Note:** The official NemoClaw sandbox-hardening docs further restrict `/sandbox` to read-only via Landlock, with only `/sandbox/.openclaw-data`, `/sandbox/.nemoclaw`, and `/tmp` writable. The filesystem_policy `read_write` section in the baseline YAML lists `/sandbox` and `/tmp`, but Landlock enforcement makes `/sandbox` effectively read-only except for the declared writable subdirectories. See [Sandbox Hardening](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html) for details.

The sandbox process runs as a dedicated `sandbox` user and group.
Landlock LSM enforcement applies on a best-effort basis.

### Network Policies

The following endpoint groups are allowed by default in the baseline policy:

| Policy | Endpoints | Binaries | Rules |
|---|---|---|---|
| `claude_code` | `api.anthropic.com:443`, `statsig.anthropic.com:443`, `sentry.io:443` | `/usr/local/bin/claude` | POST to inference paths on `api.anthropic.com`, POST on `statsig.anthropic.com`, GET only on `sentry.io` |
| `nvidia` | `integrate.api.nvidia.com:443`, `inference-api.nvidia.com:443` | `/usr/local/bin/claude`, `/usr/local/bin/openclaw` | POST to inference and embedding paths, GET to model listings |
| `clawhub` | `clawhub.ai:443` | `/usr/local/bin/openclaw`, `/usr/local/bin/node` | GET, POST |
| `openclaw_api` | `openclaw.ai:443` | `/usr/local/bin/openclaw`, `/usr/local/bin/node` | GET, POST |
| `openclaw_docs` | `docs.openclaw.ai:443` | `/usr/local/bin/openclaw` | GET only |
| `npm_registry` | `registry.npmjs.org:443` | `/usr/local/bin/openclaw` only (openclaw plugins install) | GET only |

All endpoints use TLS termination and are enforced at port 443.

> **GitHub is NOT in the baseline policy.** Apply the `github` preset during onboarding if your agent needs GitHub access. See [Customize the Network Policy](https://docs.nvidia.com/nemoclaw/latest/network-policy/customize-network-policy.html).

## Policy Tiers

During onboarding, the wizard prompts for a policy tier that determines the default set of presets applied on top of the baseline policy. The baseline policy is always applied regardless of the selected tier.

| Tier | Presets included | Description |
|---|---|---|
| Restricted | None | Base sandbox only. No third-party network access beyond inference and core agent tooling. |
| Balanced (default) | npm, pypi, huggingface, brew, brave | Full dev tooling and web search. No messaging platform access. |
| Open | npm, pypi, huggingface, brew, brave, slack, discord, telegram, jira, outlook | Broad access across third-party services including messaging and productivity. |

After selecting a tier, a combined preset and access-mode screen lets you include or exclude individual presets and toggle each between read (GET only) and read-write (GET + POST/PUT/PATCH) access.

In non-interactive mode, set the tier with `NEMOCLAW_POLICY_TIER`:

```console
$ NEMOCLAW_POLICY_TIER=open nemoclaw onboard --non-interactive --yes-i-accept-third-party-software
```

## protocol: rest — L7 HTTP Inspection

When an endpoint sets `protocol: rest`, the OpenShell proxy performs L7 HTTP inspection. This enables fine-grained access control by HTTP method and path, instead of raw TCP passthrough.

### Endpoint Fields (protocol: rest)

| Field | Type | Required | Description |
|---|---|---|---|
| `host` | string | Yes | Hostname or IP. Supports wildcards (`*.example.com`). |
| `port` | integer | Yes | TCP port number. |
| `protocol` | string | No | Set to `rest` to enable HTTP request inspection. Omit for TCP passthrough. |
| `tls` | string | No | TLS handling. Auto-detected when `protocol: rest`; set to `skip` for mTLS or non-standard protocols. Values `terminate` and `passthrough` are deprecated. |
| `enforcement` | string | No | `enforce` actively blocks disallowed requests. `audit` logs violations but allows traffic through. |
| `access` | string | No | HTTP access level: `read-only` (GET, HEAD, OPTIONS), `read-write` (GET, HEAD, OPTIONS, POST, PUT, PATCH), or `full` (all methods). Mutually exclusive with `rules`. |
| `rules` | list | No | Fine-grained per-method, per-path allow rules. Mutually exclusive with `access`. |
| `deny_rules` | list | No | L7 deny rules that block specific requests even when allowed by `access` or `rules`. Deny rules take precedence over allow rules. |
| `allowed_ips` | list | No | CIDR or IP allowlist for SSRF override. Loopback, link-local, and unspecified addresses are rejected. |

### Access Levels

| Value | Allowed HTTP Methods |
|---|---|
| `full` | All methods and paths |
| `read-only` | GET, HEAD, OPTIONS |
| `read-write` | GET, HEAD, OPTIONS, POST, PUT, PATCH |

### Rule Object

Used when `access` is not set. Each rule explicitly allows a method and path combination.

| Field | Type | Required | Description |
|---|---|---|---|
| `allow.method` | string | Yes | HTTP method to allow (e.g., `GET`, `POST`). |
| `allow.path` | string | Yes | URL path pattern. Supports `*` and `**` glob syntax. |
| `allow.query` | map | No | Query parameter matchers. Values can be glob strings or objects with `any`. |

### Deny Rule Object

Blocks specific operations on endpoints that otherwise have broad access. Deny rules are evaluated after allow rules and take precedence.

| Field | Type | Required | Description |
|---|---|---|---|
| `method` | string | No | HTTP method to deny. `*` matches any method. |
| `path` | string | No | URL path pattern. Same glob syntax as allow rules. |
| `command` | string | No | SQL command to deny (`SELECT`, `INSERT`, etc.). For `protocol: sql` only. |
| `query` | map | No | Query parameter matchers. Same syntax as allow rule `query`. |

### Example — REST API with Deny Rules

```yaml
network_policies:
  github_rest_api:
    name: github-rest-api
    endpoints:
      - host: api.github.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
        deny_rules:
          - method: POST
            path: "/repos/*/pulls/*/reviews"
          - method: PUT
            path: "/repos/*/branches/*/protection"
          - method: "*"
            path: "/repos/*/rulesets"
    binaries:
      - path: /usr/local/bin/claude
      - path: /usr/bin/node
      - path: /usr/bin/gh
```

### Example — Custom Preset with protocol: rest

```yaml
preset:
  name: influxdb
  description: "InfluxDB time-series database"
  network_policies:
    influxdb:
      name: influxdb
      endpoints:
        - host: influxdb.internal.example.com
          port: 8086
          protocol: rest
          enforcement: enforce
          rules:
            - allow: { method: GET, path: "/**" }
            - allow: { method: POST, path: "/api/v2/write" }
      binaries:
        - { path: /usr/bin/curl }
```

### Inference

The baseline policy allows only the `local` inference route. External inference
providers are reached through the OpenShell gateway, not by direct sandbox egress.

## Operator Approval Flow

When the agent attempts to reach an endpoint not listed in the policy, OpenShell intercepts the request and presents it in the TUI for operator review:

1. The agent makes a network request to an unlisted host.
2. OpenShell blocks the connection and logs the attempt.
3. The TUI command `openshell term` displays the blocked request with host, port, and requesting binary.
4. The operator approves or denies the request.
5. If approved, the endpoint is added to the running policy for the session.

To try this, run the walkthrough:

```console
$ ./scripts/walkthrough.sh
```

This opens a split tmux session with the TUI on the left and the agent on the right.

## Modifying the Policy

### Static Changes

Edit `nemoclaw-blueprint/policies/openclaw-sandbox.yaml` and re-run the onboard wizard:

```console
$ nemoclaw onboard
```

### Dynamic Changes — Recommended: policy-add

Apply policy updates to a running sandbox without restarting. The recommended path is `nemoclaw <name> policy-add`, which structurally merges new entries into the live policy without dropping existing presets:

```console
$ nemoclaw my-assistant policy-add
```

For scripted workflows:

```console
$ nemoclaw my-assistant policy-add pypi --yes
$ nemoclaw my-assistant policy-remove pypi --yes
```

### Dynamic Changes — Advanced: openshell policy set

> **WARNING:** `openshell policy set` **replaces** the sandbox's live policy with the contents of the file you provide; it does not merge. A running sandbox's live policy is the baseline plus every preset layered on during onboarding. Applying a file that contains only the baseline silently drops every other preset.

If you must use this path, snapshot the live policy first, edit, then apply:

```console
$ openshell policy get --full my-assistant > live-policy.yaml
# Edit live-policy.yaml to add entries under network_policies:
$ openshell policy set --policy live-policy.yaml my-assistant
```

Dynamic changes apply only to the current session. When the sandbox stops, the running policy resets to the baseline plus recorded presets. To make custom policies survive recreation, ship a preset file under `nemoclaw-blueprint/policies/presets/` or edit the baseline and re-run `nemoclaw onboard`.
