# Solo Sandbox

Creates filesystem mounts and generates NemoClaw-compatible sandbox policies.

## Purpose

Initializes solo founder sandbox environment by creating directories and generating policy YAML files for each claw.

## SandboxPolicy Data Class

```python
@dataclass
class SandboxPolicy:
    claw: str
    mount: str
    network_egress: list[str]
    inference_routes: dict[str, str]
    approval_mode: str
    created_at: str
    version: str
```

## Main Functions

| Function | Purpose |
|----------|---------|
| `init_solo_sandbox()` | Initialize all sandboxes |
| `create_mount_directories()` | Create filesystem directories |
| `load_sandbox_policy()` | Load policy for a claw |
| `get_read_only_mounts()` | Extract read-only paths |
| `get_all_accessible_mounts()` | All accessible paths |

## Policy Output Structure

Generated policy files (`{claw}-claw.yaml`):
```yaml
metadata:
  claw: content
  version: 1.0.0
  schema: nemoClaw-sandbox-policy-v1
filesystem:
  mount: /sandbox/content
  permissions: rw
  isolation: landlock
network:
  egress_policy: allowlist
  approved_domains: [...]
  default_action: deny
inference:
  routing: {...}
  default_route: local
operator_policy:
  approval_mode: REVIEW
  war_room_access: true
security:
  seccomp: strict
  capabilities: [CAP_NET_BIND_SERVICE]
```

## Inference Routes per Claw

| Claw | Data Types |
|------|------------|
| Content | client_facing_drafts, public_docs_changelogs |
| Ops | client_records, internal_ideation |
| Analytics | analytics_synthesis |
| Finance | financial_data (locked to local) |
| Build | source_code (locked to local) |

## Directory Creation

Creates standard subdirectories for each claw:
```
/sandbox/{claw}/
├── tools/
├── data/
└── logs/
```

## Policy Directory

Default: `milimo-blueprint/policies/`

File mapping:
- `content` → `content-sandbox.yaml`
- `ops` → `ops-sandbox.yaml` (also `clients` alias)
- `analytics` → `analytics-sandbox.yaml`
- `finance` → `finance-sandbox.yaml`
- `build` → `build-sandbox.yaml`

## Relationships

- Uses: [[solo-init]] — Configuration and paths
- Generates: Policy YAML files
- Creates: Sandbox directories

## Source

`milimo-blueprint/orchestrator/solo_sandbox.py`
