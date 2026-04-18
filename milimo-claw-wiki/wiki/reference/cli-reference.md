# CLI Reference

**Summary**: Command-line interface commands for MilimoClaw.

**Sources**:
- `milimo-claw-docs/CLI_REFERENCE.md`
- `milimo/src/cli.ts`

**Last updated**: 2026-04-14

**Tags**: #reference #cli #commands

---

## Overview

MilimoClaw CLI is accessed via `milimo` command (TypeScript plugin for OpenClaw).

---

## Core Commands

### `milimo init`

Initialize a new MilimoClaw project.

```bash
milimo init --solo --operator-name "Your Name" --squad-name "my-squad"
```

### `milimo onboard`

Run the onboarding wizard.

```bash
milimo onboard --non-interactive
```

### `milimo squad`

Manage squad configuration.

```bash
milimo squad status
milimo squad start
milimo squad stop
```

---

## Claw Commands

### `milimo action`

Execute actions on claws.

```bash
milimo action <claw> <action> [options]
```

### `milimo assistant`

Manage the assistant (Lucy).

```bash
milimo assistant status
milimo assistant restart
```

---

## Blueprint Commands

### `milimo blueprint`

Manage blueprints.

```bash
milimo blueprint list
milimo blueprint fork @squadname/blueprint-name --into my-claw
milimo blueprint diff v2.1 v8.3
milimo blueprint publish --name "description" --price 0.05eth
milimo blueprint rollback --to v3.0 --reason "reason"
```

---

## War Room Commands

### `milimo warroom`

Open the War Room TUI.

```bash
milimo warroom
```

Keyboard shortcuts:
- **A**: Approve current REVIEW
- **B**: Block current item
- **E**: Edit inline
- **R**: Release current HOLD
- **D**: Toggle digest
- **F**: Toggle Deep Work Mode
- **H**: Help
- **Q**: Quit

---

## Deep Work Mode

### `milimo finals-mode`

Enable focused work mode.

```bash
milimo squad finals-mode --duration 2weeks --resume-date 2026-05-12
milimo squad finals-resume
```

---

## Logs and Monitoring

### `milimo logs`

View claw logs.

```bash
milimo logs [claw] [--follow] [--tail N]
```

### `milimo verify`

Verify system health.

```bash
milimo verify --all
milimo verify --claw content
```

---

## Payment Commands

### `milimo payment`

Payment management.

```bash
milimo payment status
milimo payment connect
```

---

## Slash Commands

### `milimo slash`

Custom slash commands.

```bash
milimo slash list
milimo slash add <name> <command>
milimo slash remove <name>
```

---

## Badge Commands

### `milimo badge`

Performance badge management.

```bash
milimo badge list
milimo badge generate
```

---

## Options

| Option | Description |
|--------|-------------|
| `--non-interactive` | Run without prompts |
| `--solo` | Use solo-founder template |
| `--operator-name` | Set operator name |
| `--squad-name` | Set squad name |
| `--sandbox-name` | Specify sandbox |
| `--verbose` | Enable verbose output |
| `--dry-run` | Show actions without executing |
| `--help` | Show help |
| `--version` | Show version |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `MILIMO_SANDBOX_NAME` | Default sandbox name |
| `NVIDIA_API_KEY` | NVIDIA inference key |
| `GITHUB_TOKEN` | GitHub API token |
| `VERCEL_TOKEN` | Vercel deploy token |
| `SENTRY_AUTH_TOKEN` | Sentry error tracking |
| `STRIPE_SECRET_KEY` | Stripe API key |

---

## Related Pages

- [[war-room]] — War Room TUI
- [[solo-founder]] — Solo template
- [[conventions]] — Development conventions
