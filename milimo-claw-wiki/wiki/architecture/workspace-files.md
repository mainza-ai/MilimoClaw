# Workspace Files

**Summary**: How workspace files persist inside the NemoClaw sandbox, including multi-agent layout and rebuild behavior.

**Sources**:
- [NemoClaw Architecture Reference](https://docs.nvidia.com/nemoclaw/latest/reference/architecture.html)
- [NemoClaw Sandbox Environment](https://docs.nvidia.com/nemoclaw/latest/reference/sandbox-environment.html)
- [[sandbox-isolation]]

**Last updated**: 2026-04-29

**Tags**: #architecture #workspace #files #persistence

---

> **NemoClaw Compliance Notice:** This page reflects the current NemoClaw sandbox filesystem behavior. The workspace path, persistence model, and Landlock policy are defined by the NemoClaw blueprint and OpenShell runtime. If behavior documented here conflicts with the current NemoClaw release, the NemoClaw documentation is authoritative.

## Location

Workspace files live at:

```
/sandbox/.openclaw/workspace/
```

This path is inside the sandbox container. The `.openclaw/` directory is mounted read-only (root-owned, immutable, integrity-verified), but `workspace/` is writable because the sandbox entrypoint provisions it as a **symlink into `/sandbox/.openclaw-data/`**, which is writable. This is the official NemoClaw mechanism — see [Workspace Files](https://docs.nvidia.com/nemoclaw/latest/workspace/workspace-files.html) and [Architecture](https://docs.nvidia.com/nemoclaw/latest/reference/architecture.html).

> **NemoClaw Path Note:** The official NemoClaw v0.0.29 grants read-write access to `/sandbox`, `/tmp`, and `/dev/null` (see [Security Best Practices](https://docs.nvidia.com/nemoclaw/latest/security/best-practices.html)). The `/sandbox/.openclaw/` directory is an explicit read-only exception (root-owned, `chattr +i`, SHA256-verified). The `workspace/` subdirectory is writable because it is symlinked into `/sandbox/.openclaw-data/`, which is part of the writable `/sandbox` tree. Per-agent `workspace-<name>/` directories follow the same symlink pattern.

## Multi-Agent Support

In multi-agent setups, each agent gets its own subdirectory:

```
/sandbox/.openclaw/workspace/
├── content-claw/
├── ops-claw/
├── analytics-claw/
├── finance-claw/
├── build-claw/
└── assistant-claw/
```

Each agent writes only to its own `workspace-name/` directory. Cross-agent data sharing uses typed message contracts through the OpenShell gateway, not direct filesystem access.

## Persistence Model

| Event | Workspace Preserved? | Notes |
|-------|---------------------|-------|
| Sandbox restart (same container) | Yes | Files survive process restart |
| `nemoclaw rebuild` (new container) | **Best-effort** | Rebuild auto-backs up workspace to `~/.nemoclaw/rebuild-backups/<name>/` and restores after creating new container. Verify critical files after rebuild. |
| `nemoclaw onboard --recreate-sandbox` | **No** | Full sandbox recreation; workspace is not backed up or restored |
| `nemoclaw <name> destroy` | **No** | All data removed |

> **Important:** `nemoclaw backup` (aka `nemoclaw backup-all`) does **not** include workspace files. The rebuild auto-backup is a separate, best-effort mechanism. For guaranteed persistence, copy critical files explicitly before any destructive operation.

> **Rebuild vs recreate-sandbox:** `nemoclaw rebuild` is a managed upgrade path that attempts workspace preservation. `nemoclaw onboard --recreate-sandbox` is a clean recreation that does not preserve workspace. Always prefer `rebuild` for upgrades.

## Filesystem Policy

Under the NemoClaw filesystem policy:

- `/sandbox` is writable at the container mount level (Landlock may add finer restrictions on 5.13+ kernels, `compatibility: best_effort`)
- `/sandbox/.openclaw/` is explicitly read-only (root-owned, `chattr +i`, SHA256-verified)
- `/sandbox/.openclaw/workspace/` is writable (symlinked into `/sandbox/.openclaw-data/`)
- Other writable paths: `/sandbox/.openclaw-data/`, `/sandbox/.nemoclaw/`, `/tmp/`

The workspace directory is writable because the entrypoint provisions it as a symlink into `.openclaw-data/`, which is part of the writable `/sandbox` tree.

## Use Cases

| Use Case | Example |
|----------|---------|
| Agent memory | Remembering user preferences, past interactions |
| Conversation context | Storing multi-turn conversation state |
| Task state | Tracking in-progress tasks, partial results |
| Intermediate artifacts | Draft content, code snippets, analysis results before approval |

## Backup and Recovery

Since workspace files are not included in `nemoclaw backup`, operators must copy important files explicitly:

```bash
# Manual backup before destructive operations
cp -r /sandbox/.openclaw/workspace/ ~/workspace-backup/

# Manual restore
cp -r ~/workspace-backup/ /sandbox/.openclaw/workspace/
```

### Structured Alternative: `nemoclaw snapshot`

> **Note:** `nemoclaw snapshot create/list/restore` are official NemoClaw v0.0.29 commands (see [Commands reference](https://docs.nvidia.com/nemoclaw/latest/reference/commands.html) and [Backup & Restore](https://docs.nvidia.com/nemoclaw/latest/workspace/backup-restore.html)). They are the recommended way to back up and restore workspace state.

```bash
# Create a named snapshot before risky changes
nemoclaw my-squad snapshot create --name pre-upgrade

# List available snapshots
nemoclaw my-squad snapshot list

# Restore from a snapshot
nemoclaw my-squad snapshot restore pre-upgrade
```

For critical agent state that must survive rebuilds, store durable data in `/sandbox/.openclaw-data/milimo/claws/<role>/` — this path is persisted via symlinks into `.openclaw-data/` and may survive certain deployment configurations.

## Related Pages

- [[sandbox-isolation]] — Overall isolation model and Landlock policy
- [[sandbox-sync]] — Troubleshooting sync and persistence issues
- [[privacy-router]] — Inference routing and data sensitivity
- [[network-egress]] — Network policy for external access
