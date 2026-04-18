# Solo Deep Work

Focused work mode for solo founders — hot-reloads claw policies.

## Purpose

Activates deep work mode that reduces interruptions. Hot-reloads each claw's policy to reduce noise while maintaining essential operations.

## Deep Work Policies

| Policy | Description | Blocked | Queued |
|--------|-------------|---------|--------|
| `pause_drafts` | Queue only, no publishing | publish, send | draft, create, schedule |
| `maintenance` | Auto-responses to active clients | new_outreach, follow_up | maintenance, status_update |
| `passive` | Collect data, no new experiments | experiment, test | collect, analyze |
| `invoices_only` | Sends continue, no new intake | new_invoice, new_client | send_reminder, process |
| `issues_only` | Triage only, no new PRs | open_pr, merge | triage, label, comment |

## Default Claw Activation

| Claw | Policy |
|------|--------|
| Content | `pause_drafts` |
| Ops | `maintenance` |
| Analytics | `passive` |
| Finance | `invoices_only` |
| Build | `issues_only` |

## Main Functions

| Function | Purpose |
|----------|---------|
| `activate_deep_work_mode()` | Enable deep work mode |
| `deactivate_deep_work_mode()` | Resume normal operations |
| `get_deep_work_status()` | Check current status |
| `is_deep_work_active()` | Boolean check |

## Activation Flow

1. Parse resume_date (YYYY-MM-DD)
2. For each claw:
   - Get current policy
   - Apply deep work policy
   - Update policy file
3. Save state to `~/.milimo/state/deep_work.json`
4. Set auto-response template

## DeepWorkState Data Class

```python
@dataclass
class DeepWorkState:
    active: bool
    activated_at: datetime
    resume_date: datetime
    auto_response_template: str
    claw_policies: dict[str, str]
```

## Policy File Updates

Each claw's policy file gets added fields:
```yaml
deep_work_policy: pause_drafts
deep_work_active: true
deep_work_activated_at: 2026-01-15T10:00:00Z
deep_work_blocked_actions: [publish, send]
deep_work_queued_actions: [draft, create, schedule]
```

## CLI Commands

```bash
milimo squad finals-mode --until 2026-01-20
milimo squad finals-mode --resume
```

## Relationships

- Uses: [[solo-init]] — Configuration loading
- Modifies: Claw policy files
- Notifies: War Room — Status changes

## Source

`milimo-blueprint/orchestrator/solo_deep_work.py`
