# Sandbox File Sharing Guide

This guide explains how to share files with Milimo Claw / NemocLaw running inside the Docker sandbox container.

## Sandbox Architecture

Each of the six claws (autonomous agents) has its own isolated filesystem mount under `/sandbox/`, enforced by Linux Landlock at the kernel level. The assistant claw can read from other claws' shared mounts but cannot write directly to any claw's filesystem — all state changes go through the Python bridge CLI.

## Sandbox Directory Paths

The container is named `MilimoClaw`. Each claw has its own sandbox directory:

| Claw | Container Path | Purpose |
|------|---------------|---------|
| **Content** | `/sandbox/content/` | Brand assets, style guides, drafts, social media files |
| **Ops** | `/sandbox/clients/` | Client records, contracts, templates, intake forms |
| **Analytics** | `/sandbox/analytics/` | Data files, market research, external reports |
| **Finance** | `/sandbox/finance/` | Pricing data, financial records, invoices |
| **Build** | `/sandbox/build/` | Source code, config files, deployment scripts |
| **Assistant** | `/sandbox/assistant/` | Session data, context files, operator interaction logs |
| **Shared (all claws read)** | `/sandbox/analytics/reports/` | Any file here is readable by all claws + assistant |
| **Workspace (agent)** | `/sandbox/.openclaw-data/workspace/` | Agent workspace files (SOUL.md, USER.md, etc.) |

## Copying Files Into the Container

Use `docker cp` to transfer files from your host machine into the container:

```bash
# Copy a single file to the Content claw
docker cp ./my-brand-guide.pdf MilimoClaw:/sandbox/content/data/

# Copy a directory to the Analytics claw
docker cp ./market-research/ MilimoClaw:/sandbox/analytics/data/

# Copy files to the shared reports directory (all claws can read)
docker cp ./my-report.json MilimoClaw:/sandbox/analytics/reports/

# Copy to the Build claw
docker cp ./my-script.py MilimoClaw:/sandbox/build/tools/
```

## Navigating Inside the Container

**Open a shell session:**
```bash
docker exec -it MilimoClaw bash
```

**Navigate to a specific sandbox directory:**
```bash
cd /sandbox/analytics/reports/
ls -la
```

**List contents without entering the container:**
```bash
docker exec -it MilimoClaw ls -la /sandbox/analytics/reports/
```

**Run a command from within a directory:**
```bash
docker exec -it MilimoClaw sh -c "cd /sandbox/analytics/reports/ && cat weekly-intelligence.json"
```

## File Ownership

The container runs as the `sandbox` user (UID/GID 1000). After copying files, fix ownership:

```bash
docker exec MilimoClaw chown -R sandbox:sandbox /sandbox/content/data/my-brand-guide.pdf
```

## Creating Sandbox Directories

If sandbox directories don't exist yet (they are created by the Python orchestrator on first init), create them manually:

```bash
docker exec -it MilimoClaw mkdir -p /sandbox/analytics/reports/
docker exec -it MilimoClaw chown -R sandbox:sandbox /sandbox/analytics/
```

Or run the Python initializer:
```bash
docker exec MilimoClaw python3 -c "from orchestrator.solo_init import setup_sandbox_directories; setup_sandbox_directories()"
```

## Shared File Access

The `/sandbox/analytics/reports/` directory is the only cross-claw shared filesystem mount. Every claw has read-only access to this directory, and the NemocLaw assistant can read files here via:

```
bridge: read_file("/sandbox/analytics/reports/your-file.json")
```

This is the recommended location for files that need to be accessible to all claws and the assistant.

## Backup and Restore

The project includes a backup/restore script at `scripts/backup-workspace.sh` that uses the `openshell` CLI:

```bash
# Upload files TO the sandbox
openshell sandbox upload --workspace /path/to/your/files

# Download files FROM the sandbox
openshell sandbox download --workspace /path/to/backup/
```

This backs up key workspace files (`SOUL.md`, `USER.md`, `IDENTITY.md`, `AGENTS.md`, `MEMORY.md`, and the `memory/` directory) from `/sandbox/.openclaw/workspace`.

## Security Considerations

- Files placed in claw-specific directories are only accessible to that claw
- Cross-claw file sharing is limited to `/sandbox/analytics/reports/` (read-only)
- The finance claw has the strictest isolation — no other claw has filesystem access to `/sandbox/finance/`
- All sandbox processes run as the unprivileged `sandbox` user
- Landlock enforces filesystem access controls at the kernel level
