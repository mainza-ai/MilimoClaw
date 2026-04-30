# Development Scripts

**Summary**: Development and debugging scripts for MilimoClaw.

**Sources**:
- `scripts/debug.sh`
- `scripts/check-coverage-ratchet.sh`

**Last updated**: 2026-04-29

**Tags**: #scripts #development #debugging

---

## Overview

Development scripts support debugging, testing, and code quality checks.

---

## debug.sh

Diagnostic collection for bug reports.

### Usage

```bash
# Full diagnostics to stdout
./scripts/debug.sh

# Minimal diagnostics
./scripts/debug.sh --quick

# Target specific sandbox
./scripts/debug.sh --sandbox mybox

# Save to tarball
./scripts/debug.sh --output /tmp/diag.tar.gz

# Via official NemoClaw CLI
nemoclaw debug
nemoclaw debug --quick --sandbox my-squad --output /tmp/diag.tar.gz

# Via MilimoClaw CLI wrapper (aliases nemoclaw debug)
milimo debug
milimo debug --quick --output /tmp/diag.tar.gz
```

### Collected Data

| Category | Quick Mode | Full Mode |
|----------|------------|-----------|
| System (date, uname, uptime) | ✓ | ✓ |
| Memory info | ✓ | ✓ |
| Processes (CPU) | ✓ | ✓ |
| Processes (memory) | — | ✓ |
| top output | — | ✓ |
| GPU (nvidia-smi) | ✓ | ✓ |
| GPU details | — | ✓ |
| Docker containers | ✓ | ✓ |
| Docker logs | 200 lines | 200 lines |
| Docker inspect | — | ✓ |
| OpenShell status | ✓ | ✓ |
| Sandbox internals | — | ✓ |
| Network info | — | ✓ |
| Kernel messages | ✓ | ✓ |

### Security

Auto-redacts sensitive patterns:
- API keys (`NVIDIA_API_KEY`, etc.)
- Tokens (`nvapi-*`, `ghp_*`)
- Bearer tokens
- Passwords/secrets

### Output

- Terminal output with sections
- Optional tarball for GitHub issues
- Redacted for secrets

---

## check-coverage-ratchet.sh

Enforces test coverage thresholds with ratchet mechanism.

### Usage

```bash
# Run tests with coverage first
npx vitest run --coverage

# Check against thresholds
./scripts/check-coverage-ratchet.sh
```

### How It Works

1. Reads `ci/coverage-threshold.json` for minimum thresholds
2. Compares against `coverage/coverage-summary.json`
3. Fails if coverage drops below threshold (1% tolerance)
4. Prints new thresholds when coverage improves

### Threshold File

```json
{
  "lines": 80,
  "functions": 75,
  "branches": 70,
  "statements": 80
}
```

### Output Examples

**Passing**:
```
=== Coverage Ratchet Check ===

OK: lines coverage is 82% (threshold 80%)
OK: functions coverage is 78% (threshold 75%)
OK: branches coverage is 72% (threshold 70%)
OK: statements coverage is 81% (threshold 80%)

Coverage ratchet passed.
```

**Regression**:
```
FAIL: lines coverage is 78%, threshold is 80% (tolerance 1%)
Coverage regression detected. Add tests to bring coverage back above the threshold.
```

**Improvement**:
```
IMPROVED: lines coverage is 85%, above threshold 80%
Coverage improved! Update ci/coverage-threshold.json to ratchet the floor:
{"lines": 85, "functions": 78, ...}
```

---

## Other Scripts

| Script | Purpose |
|--------|---------|
| `backup-workspace.sh` | Create workspace backup |
| `check-spdx-headers.sh` | Verify SPDX license headers |
| `smoke-macos-install.sh` | Test macOS installation |
| `post-sandbox-setup.sh` | Post-sandbox configuration |

---

## Related Pages

- [[installation-scripts]] — Installation scripts
- [[service-scripts]] — Service management
- [[testing]] — Test structure
