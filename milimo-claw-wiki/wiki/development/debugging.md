# Debugging

**Summary**: Debug guide and tools for MilimoClaw development.

**Sources**:
- `raw/AGENTS.md`
- `milimo-blueprint/`

**Last updated**: 2026-04-15

**Tags**: #development #debugging

---

## Debug Mode

Enable debug logging for detailed output:

```bash
# Enable debug mode
export MILIMO_DEBUG=1

# Run with verbose logging
python -m orchestrator.main --debug
```

---

## Log Locations

| Component | Log Path | Purpose |
|-----------|----------|---------|
| Claw processes | `/var/log/milimo/{claw}/` | Per-claw execution logs |
| Mesh coordinator | `/var/log/milimo/mesh/` | Inter-claw message logs |
| War Room | `/var/log/milimo/warroom/` | Approval queue logs |
| Evolution | `/var/log/milimo/evolution/` | Tool generation logs |

---

## Common Debug Scenarios

### Claw Not Starting

1. Check process status: `ps aux | grep milimo`
2. Verify sandbox isolation: `ls -la /sandbox/{claw}/`
3. Check for policy violations: `journalctl -u milimo-{claw}`
4. Review startup logs: `tail -f /var/log/milimo/{claw}/startup.log`

### Message Not Routing

1. Verify message contract: Check [[message-contracts]]
2. Check mesh routing: `cat /var/log/milimo/mesh/routing.log`
3. Verify destination claw is running
4. Check [[privacy-router]] for blocked inference calls

### Evolution Tool Generation Failing

1. Check evolution config: See [[evolution-config]]
2. Review tool proposal logs: `/var/log/milimo/evolution/proposals/`
3. Verify sandbox has write access to `/sandbox/build/generated-tools/`
4. Check inference routing for [[privacy-router]] issues

---

## Debug Tools

### Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add debug statements
logger.debug("Variable value: %s", variable)
```

### Process Inspection

```bash
# List all milimo processes
ps aux | grep milimo

# Check open file descriptors
lsof -p <pid>

# Check network connections
netstat -anp | grep <pid>
```

---

## Sandbox Debugging

See [[sandbox-isolation]] for isolation verification.

```bash
# Check sandbox mount points
findmnt | grep sandbox

# Verify Landlock rules
cat /proc/self/landlock

# Check seccomp filter
cat /proc/self/status | grep Seccomp
```

---

## War Room Debugging

See [[war-room]] for TUI issues.

```bash
# Check pending approvals
cat /var/log/milimo/warroom/queue.json

# Force approval (emergency)
milimo approve --action-id <id>

# Reject pending action
milimo reject --action-id <id>
```

---

## Performance Debugging

### Profiling

```bash
# CPU profiling
python -m cProfile -o output.prof orchestrator/main.py

# Memory profiling
python -m memory_profiler orchestrator/main.py
```

### Latency Tracking

See [[latency-monitor]] for inter-region latency metrics.

---

## Related Pages

- [[conventions]] — Code conventions
- [[testing]] — Test structure and coverage
- [[common-issues]] — Frequently encountered problems
- [[issues-and-fixes]] — Comprehensive audit of past fixes
- [[sandbox-isolation]] — Isolation verification
