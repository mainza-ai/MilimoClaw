# CLI Commands

**Summary**: Commander.js CLI for Milimo squad management.

**Sources**:
- `milimo/src/cli.ts`
- `milimo/src/commands/*.ts`

**Last updated**: 2026-04-15

**Tags**: #cli #typescript #commands

---

## Overview

The CLI provides squad lifecycle management through `openclaw milimo <subcommand>`.

---

## Command Structure

```
openclaw milimo
├── onboard        # Interactive setup
├── init           # Initialize squad
├── squad
│   ├── status     # Show squad topology
│   ├── finals     # Toggle finals mode
│   └── resume     # Resume after finals
├── blueprint
│   ├── fork       # Fork blueprint
│   ├── diff       # Show changes
│   ├── publish    # Publish to registry
│   ├── rollback   # Revert changes
│   ├── list       # List blueprints
│   ├── search     # Search registry
│   ├── merge      # Merge branches
│   └── info       # Show blueprint info
├── warroom        # Launch TUI
├── payment
│   ├── checkout   # Start subscription
│   ├── status     # Show subscription
│   ├── balance    # Show balance
│   ├── history    # Payment history
│   ├── invoice    # Download invoice
│   └── connect    # Connect Stripe
├── verify         # Verify provenance
├── badge          # Generate badges
├── action
│   ├── approve    # Approve action
│   ├── block      # Block action
│   └── list       # List pending
├── logs
│   ├── search     # Search logs
│   └── list       # List log files
└── assistant
    ├── setup      # Configure assistant
    ├── verify     # Verify setup
    └── start      # Start assistant
```

---

## Key Commands

### `milimo onboard`

Interactive setup wizard:
```bash
openclaw milimo onboard \
  --squad my-squad \
  --role content \
  --template solo-founder \
  --solo \
  --operator "John Doe"
```

### `milimo init`

Initialize new squad:
```bash
openclaw milimo init \
  --squad my-squad \
  --role ops \
  --assistant-name Nova \
  --assistant-emoji 🦀
```

### `milimo squad status`

Show topology:
```bash
openclaw milimo squad status --json
```

### `milimo warroom`

Launch TUI:
```bash
openclaw milimo warroom
```

---

## Options

### Common Options

| Option | Description |
|--------|-------------|
| `--squad <name>` | Squad identifier |
| `--role <role>` | Claw role |
| `--template <name>` | Squad template |
| `--solo` | Solo operator mode |
| `--operator <name>` | Operator name |
| `--json` | JSON output |

---

## Source Files

| File | Commands |
|------|----------|
| `commands/onboard.ts` | `onboard` |
| `commands/init.ts` | `init` |
| `commands/squad.ts` | `squad status|finals|resume` |
| `commands/blueprint.ts` | `blueprint fork|diff|publish|...` |
| `commands/warroom.ts` | `warroom` |
| `commands/payment.ts` | `payment checkout|status|...` |
| `commands/verify.ts` | `verify` |
| `commands/action.ts` | `action approve|block|list` |
| `commands/logs.ts` | `logs search|list` |
| `commands/assistant.ts` | `assistant setup|verify|start` |

---

## Related Pages

- [[warroom-tui]] — TUI documentation
- [[bridge-tools]] — Python bridge
- [[onboard-flows]] — Onboarding flows
