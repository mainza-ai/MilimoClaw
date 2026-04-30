# Sandbox Sync

**Summary**: Troubleshooting sandbox synchronization issues between claws.

**Sources**:
- `raw/AGENTS.md`
- `milimo-blueprint/orchestrator/`

**Last updated**: 2026-04-29

**Tags**: #troubleshooting #sandbox #sync

---

> **NemoClaw Compliance Notice:** Workspace files live at `/sandbox/.openclaw/workspace/`. In multi-agent setups, each agent gets a `workspace-name/` subdirectory. Files persist across sandbox restarts (same container) but **NOT** across `nemoclaw rebuild` (new container = all non-persisted data lost). Workspace is not backed up by `nemoclaw backup` — use explicit file copies if needed. See [[workspace-files]] for full details.

## Overview

Sandbox sync issues occur when:
- Cross-claw mounts become stale
- Shared resources are locked
- File permissions prevent read/write
- Network partitions delay message delivery
- Workspace files are lost after a sandbox rebuild

---

## Common Issues

### Cross-Mount Stale Data

**Symptom**: Claw reads outdated data from another claw's mount.

**Cause**: Kernel doesn't immediately propagate changes across bind mounts.

**Fix**:
```bash
# Force sync
sync

# Remount the cross-mount
mount -o remount /sandbox/content/drafts/

# Check mount status
findmnt | grep cross
```

---

### Permission Denied

**Symptom**: Claw cannot read/write to shared location.

**Cause**: Incorrect ownership or mode on sandbox directories.

**Fix**:
```bash
# Check permissions
ls -la /sandbox/{claw}/

# Fix ownership (run as root)
chown -R milimo:milimo /sandbox/{claw}/

# Fix mode
chmod -R 750 /sandbox/{claw}/
```

---

### File Lock Contention

**Symptom**: Claw hangs waiting for file access.

**Cause**: Multiple processes holding locks on same file.

**Fix**:
```bash
# Find processes holding locks
fuser -v /sandbox/shared/file.json

# Kill blocking process (careful!)
fuser -k /sandbox/shared/file.json

# Or use lock timeout in code
```

---

### Network Partition

**Symptom**: Messages not arriving at destination claw.

**Cause**: Mesh coordinator network issue.

**Fix**:
```bash
# Check mesh status
milimo mesh status

# Restart mesh coordinator
systemctl restart milimo-mesh

# Verify network connectivity
ping mesh-gateway.internal
```

---

## Sync Verification

### Manual Check

```bash
# Compare source and destination
diff /sandbox/content/drafts/post.md /sandbox/ops/inbox/post.md

# Check timestamps
stat /sandbox/content/drafts/post.md
stat /sandbox/ops/inbox/post.md
```

### Automated Check

```python
import os
import time

def check_sync(source, dest, max_delay_seconds=5):
    """Verify dest is within max_delay of source."""
    source_mtime = os.path.getmtime(source)
    dest_mtime = os.path.getmtime(dest)
    return abs(source_mtime - dest_mtime) < max_delay_seconds
```

---

## Prevention

### Best Practices

1. **Use message passing** instead of direct file access when possible
2. **Implement retry logic** with exponential backoff
3. **Add timeout handling** for cross-claw operations
4. **Log sync operations** for debugging

### Code Example

```python
import time
import os

def wait_for_sync(file_path, timeout=30):
    """Wait for file to exist and be stable."""
    start = time.time()
    prev_size = -1

    while time.time() - start < timeout:
        if os.path.exists(file_path):
            current_size = os.path.getsize(file_path)
            if current_size == prev_size and current_size > 0:
                return True  # File is stable
            prev_size = current_size
        time.sleep(0.5)

    return False  # Timeout
```

---

## Workspace Persistence and Rebuilds

### Files Lost After Rebuild

**Symptom**: Agent state, conversation context, or task artifacts disappear after `nemoclaw rebuild`.

**Cause**: Workspace files at `/sandbox/.openclaw/workspace/` persist across sandbox restarts (same container) but are **NOT** preserved across `nemoclaw rebuild` by default. A rebuild creates a new container; all non-persisted data is lost unless explicitly backed up.

> **Note:** `nemoclaw rebuild` does automatically back up the workspace to `~/.nemoclaw/rebuild-backups/<name>/` before destroying the old sandbox and restores it after creating the new one. However, this backup-restore is best-effort — always verify critical files after a rebuild.

**Fix**:
```bash
# Before rebuild: copy workspace files to a persistent location
cp -r /sandbox/.openclaw/workspace/ ~/workspace-backup/

# After rebuild: restore
cp -r ~/workspace-backup/ /sandbox/.openclaw/workspace/
```

### Multi-Agent Workspace Paths

**Symptom**: Agent writes to wrong workspace directory.

**Cause**: In multi-agent setups, each agent gets a `workspace-name/` subdirectory under `/sandbox/.openclaw/workspace/`.

**Fix**:
```bash
# Verify correct workspace path for each agent
ls /sandbox/.openclaw/workspace/
# Expected: workspace-name/ per agent
```

---

## Related Pages

- [[sandbox-isolation]] — Sandbox architecture
- [[workspace-files]] — Workspace file persistence model
- [[common-issues]] — Other common problems
- [[issues-and-fixes]] — Comprehensive fix history
- [[mesh-coordinator]] — Message routing
