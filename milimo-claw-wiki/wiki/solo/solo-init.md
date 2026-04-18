# Solo Init

Solo Founder Template Loader — loads and validates `solo-founder.yaml`.

## Purpose

Handles filesystem mount automation based on available permissions. Validates template configuration including required fields, field types, and locked routes.

## Filesystem Mount Automation

### Detection Logic

```python
if can_write_to_system_sandbox():
    sandbox_base = /sandbox  # System sandbox
else:
    sandbox_base = ~/.milimo/sandboxes/{squad_id}  # User sandbox
```

### Permission Check

- If `/sandbox` exists and is writable → System sandbox
- If `/sandbox` doesn't exist and parent writable → Can create system sandbox
- Otherwise → Fall back to user sandbox

## Required Fields

Every `solo-founder.yaml` must define:

| Section | Required Fields |
|---------|-----------------|
| `template` | name, display_name, category, description, squad_size, claws_active |
| `operator_policy` | squad_lead, approval_modes |
| `filesystem` | content, ops, analytics, finance, build |
| `inference` | routing_overrides, cost_guard |
| `war_room` | operator, mode, queue_priority, digest_schedule |
| `evolution` | cycle_day, schedule, per_claw |
| `network_egress` | content, ops, analytics, finance, build |
| `deep_work_mode` | alias, on_activate, auto_response_template |

## Locked Routes

These routes must always be `local`:
- `financial_data` — Financial information
- `source_code` — Code must stay local

Exception: `docker_testing: true` allows cloud for testing.

## Main Functions

| Function | Purpose |
|----------|---------|
| `load_solo_founder_template()` | Load and validate template YAML |
| `detect_filesystem_config()` | Auto-detect sandbox paths |
| `setup_sandbox_directories()` | Create sandbox directories |
| `get_effective_paths()` | Main entry point for path resolution |
| `get_claws_to_initialize()` | Determine which claws to init |
| `get_claw_network_policy()` | Extract network egress for a claw |
| `get_approval_modes()` | Get all approval mode configs |

## Error Classes

- `TemplateValidationError` — Base validation error
- `MissingFieldError` — Required field missing
- `InvalidFieldTypeError` — Wrong type for field

## Relationships

- Loads: `templates/solo-founder.yaml`
- Creates: Sandbox directories for all claws
- Used by: [[solo-sandbox]], [[solo-warroom]], [[solo-privacy]]

## Source

`milimo-blueprint/orchestrator/solo_init.py`
