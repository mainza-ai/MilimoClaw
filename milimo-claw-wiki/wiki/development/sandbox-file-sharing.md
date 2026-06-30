---
title: Sandbox File Sharing
tags: [development, sandbox, files, guides, file-sync]
created: 2026-05-28
updated: 2026-06-30
---

# Sandbox File Sharing

**Summary**: Documents how to synchronize claw-generated files (invoices, reports, PRs, drafts, etc.) from an isolated sandbox to the host machine.

**Sources**: `scripts/hermes-sync.sh`, `milimo-hermes-sandbox/scripts/hermes-inventory.py`, `milimo-core/src/milimo_core/claw_layouts.py`, `milimo-core/src/milimo_core/milimo_paths.py`

**Last updated**: 2026-06-30

---

## Claw File Layout

Claw data is stored in profile-aware root directories. Paths resolve automatically based on `MILIMO_PROFILE`:

| Profile | Base Path |
|---------|-----------|
| **OpenClaw** | `/sandbox/.openclaw/milimo/claws/{role}/` |
| **Hermes** | `/sandbox/.hermes/claws/{role}/` |

All six claw roles share the same subdirectory structure (defined centrally in `[[hermes-profile|claw_layouts.py]]`):

| Role | Purpose |
|------|---------|
| `content/` | Drafts, campaigns, brand assets |
| `ops/` | Relationship health, briefs, risk |
| `analytics/` | Reports, anomaly detection, scores |
| `finance/` | Invoices, pricing, tax categories |
| `build/` | PRs, source code, dependency audits |
| `assistant/` | Process supervision, operator queries |

---

## Hermes Sync CLI (`hermes-sync.sh`)

The primary tool for extracting files from a running Hermes sandbox. Uses `docker cp` (auto-detected container), with `nemohermes exec` + tar as fallback.

```console
# Sync all claws to ./claws_data/
$ ./scripts/hermes-sync.sh

# Sync only the finance claw
$ ./scripts/hermes-sync.sh --role finance

# Sync to custom output directory
$ ./scripts/hermes-sync.sh --output /tmp/my-claws

# Watch mode: sync every 5 minutes
$ ./scripts/hermes-sync.sh --watch --interval 300

# Archive mode: produce tarball
$ ./scripts/hermes-sync.sh --archive --output ./claws-export.tar.gz

# Dry run (show what would sync without copying)
$ ./scripts/hermes-sync.sh --dry-run
```

### Transport Discovery

The script auto-discovers the sandbox container (via `nemohermes` or `docker ps`), detects whether claw data is at the Hermes-native path or legacy location, and chooses `docker cp` (preferred) or `nemohermes exec` + tar (fallback).

---

## Sandbox Inventory (`hermes-inventory.py`)

Baked into the Docker image at `/opt/hermes/scripts/hermes-inventory.py`. Lists all claw files with metadata in JSON format.

```console
# List all files across all claws
$ nemohermes milimo-hermes exec -- python3 /opt/hermes/scripts/hermes-inventory.py

# Filter by role and file type
$ nemohermes milimo-hermes exec -- python3 /opt/hermes/scripts/hermes-inventory.py --role finance --pattern '*.json'

# Only files modified since a date
$ nemohermes milimo-hermes exec -- python3 /opt/hermes/scripts/hermes-inventory.py --since 2026-06-01
```

Output format:

```json
[
  {
    "role": "finance",
    "path": "finance/invoices/inv_12345.pdf",
    "size": 24576,
    "mtime": "2026-06-30T12:00:00+00:00",
    "type": "pdf"
  }
]
```

---

## Direct Docker Commands

For one-off file extractions:

```console
# Find the container name
$ docker ps --filter "name=openshell-milimo-hermes" --format "{{.Names}}"

# Copy a specific file
$ docker cp <container>:/sandbox/.hermes/claws/finance/stripe/report.csv ./claws_data/

# Copy an entire claw directory
$ docker cp <container>:/sandbox/.hermes/claws/build/. ./claws_data/build/
```

---

## Security

The `claws_data/` directory in the workspace root is registered in `.gitignore` to prevent accidental commits of generated client data, invoices, and development assets.

---

## Related Pages

- [[hermes-profile]] — Profile-based path resolution
- [[sandbox-isolation]] — Sandbox security model
- [[network-egress]] — Network policy for sync transports
- [[file-structure]] — Repository file layout
- [[testing]] — Testing the sync workflow
- [[debugging]] — Troubleshooting sync issues
