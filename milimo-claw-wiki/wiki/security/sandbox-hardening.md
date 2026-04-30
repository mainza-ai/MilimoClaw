# Sandbox Image Hardening

> **NemoClaw Compliance Notice**: This page documents security controls as implemented by NVIDIA NemoClaw and OpenShell. MilimoClaw operates within the NemoClaw sandbox and inherits all controls described here. Any discrepancy between this page and the [official NemoClaw documentation](https://docs.nvidia.com/nemoclaw/latest/security/sandbox-hardening.html) should be reported and resolved in favor of the official docs.

## Removed Unnecessary Tools

Build toolchains and network probes are explicitly purged from the sandbox image:

- `gcc`, `gcc-12`
- `g++`, `g++-12`
- `cpp`, `cpp-12`
- `make`
- `netcat-openbsd`, `netcat-traditional`, `ncat`

Removing these prevents agents from compiling native exploits or using network probing tools from within the sandbox. If a build toolchain is needed during image construction, use a multi-stage build: compile in the builder stage and copy only the resulting binaries to the final image.

---

## Process Limits

The maximum number of processes is constrained to mitigate fork bombs and resource exhaustion:

- `ulimit -u 512` is set in the container `ENTRYPOINT` and `nemoclaw-start.sh`
- For `docker run`, apply the limit with: `--ulimit nproc=512:512`

---

## Dropping Linux Capabilities

All Linux capabilities are dropped at container runtime:

```bash
docker run --cap-drop=ALL ...
```

### Docker Compose Example

```yaml
services:
  sandbox:
    image: nemoclaw/sandbox@sha256:<digest>
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
      - FOWNER
      - KILL
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:size=64m
```

Key properties:

- `cap_drop: ALL` removes all capabilities at the container runtime level
- `cap_add` restores only the capabilities needed for `gosu` user switching: `CHOWN`, `SETUID`, `SETGID`, `FOWNER`, `KILL`
- The container entrypoint additionally drops these capabilities via `capsh`: `cap_net_raw`, `cap_dac_override`, `cap_sys_chroot`, `cap_fsetid`, `cap_setfcap`, `cap_mknod`, `cap_audit_write`, `cap_net_bind_service`
- `no-new-privileges:true` prevents any child process from gaining more privileges (also set via `prctl()` inside the sandbox)
- `read_only: true` makes the container filesystem read-only at the mount level
- `tmpfs` provides a writable `/tmp` within memory

### Entrypoint Capability Drops (capsh)

In addition to the container runtime `--cap-drop=ALL`, the entrypoint drops the following capabilities via `capsh`:

- `cap_net_raw`
- `cap_dac_override`
- `cap_sys_chroot`
- `cap_fsetid`
- `cap_setfcap`
- `cap_mknod`
- `cap_audit_write`
- `cap_net_bind_service`

The following capabilities are **retained** for `gosu` user switching:

- `cap_chown`
- `cap_setuid`
- `cap_setgid`
- `cap_fowner`
- `cap_kill`

---

## Home Directory

The official NemoClaw docs grant read-write access to `/sandbox`, `/tmp`, and `/dev/null` at the container mount level. `/sandbox/.openclaw/` is the only path explicitly mounted read-only (root-owned, `chattr +i`, SHA256-verified). Landlock may add finer-grained restrictions on `/sandbox` subdirectories when the kernel supports it (5.13+), but `compatibility: best_effort` means this is not guaranteed on all platforms.

### Path Access

| Path | Access | Purpose |
|---|---|---|
| `/sandbox` | Read-write | Home directory (container mount level; Landlock may restrict on 5.13+ kernels) |
| `/sandbox/.openclaw` | Read-only | Immutable gateway config (root-owned, `chattr +i`, SHA256 verified) |
| `/sandbox/.openclaw-data` | Read-write | Agent state, workspace, plugins (via symlinks) |
| `/sandbox/.openclaw/workspace` | Read-write | Workspace files (symlinked into `.openclaw-data/`) |
| `/sandbox/.nemoclaw` | Read-write | Plugin state and config; blueprints are DAC-protected (root-owned) |
| `/tmp` | Read-write | Temporary files and logs |

### What This Prevents

- Modifying the gateway configuration in `/sandbox/.openclaw/` (root-owned, immutable, SHA256-verified)
- Overwriting system binaries in read-only mounts (`/usr`, `/lib`, `/etc`, etc.)
- Data staging for exfiltration in protected paths

### Shell Environment Proxy

The image pre-creates `.bashrc` and `.profile` in `/sandbox`, which source `/tmp/nemoclaw-proxy-env.sh`. This ensures the agent's shell environment is loaded from a known-good location while the actual environment values come from a writable `/tmp` path.

---

## Landlock Kernel Requirements

Landlock LSM provides mandatory access control for filesystem paths inside the sandbox.

### Requirements

- Linux kernel 5.13 or later
- Kernel must be compiled with `CONFIG_SECURITY_LANDLOCK=y`

### Compatibility Mode

NemoClaw configures Landlock with `compatibility: best_effort`. On kernels that do not meet the requirements, Landlock is silently skipped and the sandbox falls back to discretionary access control (DAC) only.

### Verification

Check whether Landlock is available on the host kernel:

```bash
ls /sys/kernel/security/landlock
```

If the directory exists, Landlock is available. If it does not exist, the kernel does not support Landlock and filesystem restrictions will rely on DAC only.

### Production Guidance

Kernel 5.13+ is **strongly recommended** for production deployments. Without Landlock, the sandbox loses mandatory filesystem access control and relies solely on file permissions and mount options.

### Test Script

NemoClaw includes an end-to-end test for Landlock enforcement:

```
test/e2e/e2e-cloud-experimental/checks/04-landlock-readonly.sh
```

This script verifies that write attempts to read-only paths are blocked when Landlock is active.
