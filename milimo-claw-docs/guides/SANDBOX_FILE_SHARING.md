# Sandbox File Sharing Guide

> **Updated 2026-04-28:** Claw data paths migrated from `/sandbox/<role>` to `/sandbox/.openclaw-data/milimo/claws/<role>` due to Landlock filesystem restrictions. The `.milimo` directory is now a symlink to `.openclaw-data/milimo/`.

This guide explains how to share files with Milimo Claw / NemocLaw running inside the Docker sandbox container.

## Sandbox Architecture

Each of the six claws (autonomous agents) has its own isolated filesystem mount under `/sandbox/`, enforced by Linux Landlock at the kernel level. The assistant claw can read from other claws' shared mounts but cannot write directly to any claw's filesystem — all state changes go through the Python bridge CLI.

## Sandbox Directory Paths

The container is named `openshell-cluster-nemoclaw` (the OpenShell K3s cluster that hosts the sandbox). Each claw has its own data directory:

| Claw | Container Path | Purpose |
|------|---------------|---------|
| **Content** | `/sandbox/.openclaw-data/milimo/claws/content/` | Brand assets, style guides, drafts, social media files |
| **Ops** | `/sandbox/.openclaw-data/milimo/claws/ops/` | Client records, contracts, templates, intake forms |
| **Analytics** | `/sandbox/.openclaw-data/milimo/claws/analytics/` | Data files, market research, external reports |
| **Finance** | `/sandbox/.openclaw-data/milimo/claws/finance/` | Pricing data, financial records, invoices |
| **Build** | `/sandbox/.openclaw-data/milimo/claws/build/` | Source code, config files, deployment scripts |
| **Assistant** | `/sandbox/.openclaw-data/milimo/claws/assistant/` | Session data, context files, operator interaction logs |
| **Shared (all claws read)** | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` | Any file here is readable by all claws + assistant |
| **Workspace (agent)** | `/sandbox/.openclaw-data/workspace/` | Agent workspace files (SOUL.md, USER.md, etc.) |
| **Mesh state** | `/sandbox/.openclaw-data/milimo/mesh/` | Heartbeats, logs, topology |
| **Blueprints** | `/sandbox/.openclaw-data/milimo/blueprints/0.1.0/` | Blueprint code and configuration |

## Copying Files Into the Container

Use `docker cp` to transfer files from your host machine into the container:

```bash
# Copy a single file to the Content claw
docker cp ./my-brand-guide.pdf openshell-cluster-nemoclaw:/tmp/my-brand-guide.pdf
# Then transfer into sandbox via kubectl cp
docker exec openshell-cluster-nemoclaw kubectl cp /tmp/my-brand-guide.pdf openshell/my-assistant:/sandbox/.openclaw-data/milimo/claws/content/data/my-brand-guide.pdf

# Or connect to the sandbox directly:
nemoclaw my-assistant connect
# Inside sandbox:
# Files can be placed directly at /sandbox/.openclaw-data/milimo/claws/<role>/
```

## Navigating Inside the Container

**Open a shell session:**
```bash
nemoclaw my-assistant connect
# Or directly via OpenShell:
openshell term
```

**Navigate to a specific sandbox directory:**
```bash
cd /sandbox/.openclaw-data/milimo/claws/analytics/reports/
ls -la
```

## File Ownership

The sandbox runs as the `sandbox` user (UID 999, GID 999 in NemoClaw). After copying files, fix ownership:

```bash
chown -R sandbox:sandbox /sandbox/.openclaw-data/milimo/claws/content/data/my-brand-guide.pdf
```

## Creating Sandbox Directories

If sandbox directories don't exist yet (they are created by the Python orchestrator on first init), create them manually:

```bash
# Inside the sandbox (nemoclaw my-assistant connect)
mkdir -p /sandbox/.openclaw-data/milimo/claws/analytics/reports/
chown -R sandbox:sandbox /sandbox/.openclaw-data/milimo/claws/analytics/
```

Or run the Python initializer (inside the sandbox):
```bash
python3 -c "from orchestrator.solo_init import setup_sandbox_directories; setup_sandbox_directories()"
```

## Shared File Access

The `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` directory is the only cross-claw shared filesystem mount. Every claw has read-only access to this directory, and the NemocLaw assistant can read files here via:

```
bridge: read_file("/sandbox/.openclaw-data/milimo/claws/analytics/reports/your-file.json")
```

This is the recommended location for files that need to be accessible to all claws and the assistant.

## Backup and Restore

The project includes a backup/restore script at `scripts/backup-workspace.sh`. For workspace file backup, use the OpenShell CLI from the host:

```bash
# Download workspace files FROM the sandbox
openshell sandbox download --workspace /path/to/backup/
```

This backs up key workspace files (`SOUL.md`, `USER.md`, `IDENTITY.md`, `AGENTS.md`, `MEMORY.md`, and the `memory/` directory) from `/sandbox/.openclaw/workspace`.

## Security Considerations

- `/sandbox/<role>` paths are **read-only** under NemoClaw's Landlock policy — this is why data directories moved to `/sandbox/.openclaw-data/milimo/claws/`
- The `milimo_paths.py` module provides `claw_base(role)` for sandbox-aware path resolution
- Always clear `__pycache__` after deploying updated Python files to avoid stale bytecode issues
- Files placed in claw-specific directories are only accessible to that claw
- Cross-claw file sharing is limited to `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` (read-only)
- The finance claw has the strictest isolation — no other claw has filesystem access to `/sandbox/.openclaw-data/milimo/claws/finance/`
- All sandbox processes run as the unprivileged `sandbox` user
- Landlock enforces filesystem access controls at the kernel level
