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

## Host File Access Synchronization

Because the claws run inside an isolated Docker sandbox container, files they create (such as generated source code, draft blog posts, invoices, logs, and spreadsheets) reside inside the container's overlay storage layer.

To easily read, run, or edit these files on your host Mac, you have three primary access options:

### 1. Live Host File Synchronization Script (Recommended)

A lightweight host-side bash utility is provided in your workspace root at `scripts/pull_claw_files.sh`. This script auto-detects the running claws container and extracts files directly to the `./claws_data/` folder on your host Mac.

* **To pull files for all six claws:**
  ```bash
  ./scripts/pull_claw_files.sh
  ```
* **To pull files for a specific claw role only (e.g. build claw):**
  ```bash
  ./scripts/pull_claw_files.sh build
  ```

* **Note:** The entire `./claws_data/` directory is registered in your host `.gitignore` so operational files and client-sensitive data are never accidentally pushed to GitHub.

---

### 2. VS Code "Attach to Container" Explorer (Visual & Interactive)

For a fully visual and interactive experience where you can browse directories, open, read, edit, and save claw files in real-time within the container namespace, you can attach VS Code directly to the sandbox container.

1. **Install Dev Containers**: Install the official **Dev Containers** extension by Microsoft in your host VS Code.
2. **Attach to Container**:
   * Open the Command Palette (`Cmd+Shift+P` on Mac).
   * Select **"Dev Containers: Attach to Running Container..."**
   * Choose the active claws container from the list (prefixed with `openshell-my-assistant`).
3. **Explore Filesystem**: VS Code will open a new window attached directly to the sandbox container. Select **Open Folder** and navigate to `/sandbox/.openclaw/milimo/claws/` to browse and edit claw code and files visually in the sidebar tree.

---

### 3. Direct One-Off Terminal Extraction (Quick CLI)

If you just need a single file or directory and do not want to run a script, you can execute a standard `docker cp` command from your host Mac terminal.

* **Extract the generated Tetris game from the Build Claw:**
  ```bash
  docker cp $(docker ps --filter "name=openshell-my-assistant" --format "{{.Names}}" | head -n 1):/sandbox/.openclaw/milimo/claws/build/repo/tetris.py ./
  ```
* **Extract all content draft variants from the Content Claw:**
  ```bash
  docker cp $(docker ps --filter "name=openshell-my-assistant" --format "{{.Names}}" | head -n 1):/sandbox/.openclaw/milimo/claws/content/drafts ./claws_drafts
  ```

---

## Related Pages

- [[sandbox-isolation]] — Sandbox architecture
- [[workspace-files]] — Workspace file persistence model
- [[common-issues]] — Other common problems
- [[issues-and-fixes]] — Comprehensive fix history
- [[mesh-coordinator]] — Message routing
