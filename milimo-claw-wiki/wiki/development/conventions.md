# Conventions

**Summary**: Code style and project conventions for MilimoClaw.

**Sources**:
- `raw/AGENTS.md`
- `.editorconfig`

**Last updated**: 2026-04-14

**Tags**: #development #conventions

---

## Inference Calls

**Mandatory**: `data_type` on every call. No exceptions.

```python
response = inference_client.complete(
    prompt=prompt,
    data_type="scope_cost_estimation",  # ALWAYS INCLUDE
    max_tokens=800
)
```

All routes cloud during dev. `data_type` enables future NIM routing without changing call sites.

---

## Filesystem

Use `pathlib.Path` exclusively. Never `os.path`.

```python
# Good
path = Path("/sandbox/content/drafts")
path.mkdir(parents=True, exist_ok=True)

# Bad
import os
os.makedirs("/sandbox/content/drafts")
```

---

## YAML Parsing

Use `yaml.safe_load()` exclusively. Never `yaml.load()`.

```python
# Good
with open(config_path) as f:
    config = yaml.safe_load(f)

# Bad
config = yaml.load(f)  # Security risk
```

---

## Log Files

- Append-only JSONL
- `fcntl` file locking for thread safety
- Never truncate or overwrite

```python
import fcntl

def append_log(path: Path, entry: dict):
    with open(path, 'a') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(entry) + '\n')
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

## Atomic Writes

All summary JSON files: write temp file first, then `Path.rename()`.

```python
def write_summary(path: Path, data: dict):
    temp_path = path.with_suffix('.tmp')
    temp_path.write_text(json.dumps(data))
    temp_path.rename(path)  # Atomic
```

Never overwrite good data with a partial write.

---

## External Commands (TypeScript)

**The Milimo plugin uses zero `child_process` calls.** All external binary execution is delegated to the persistent Python RPC server (`bridge_server.py`) which handles subprocess isolation internally.

```typescript
// Use RPC bridge for Python operations
import { callPythonBridge } from "../lib/python-bridge";
const result = await callPythonBridge("command", { args }, { blueprintDir });

// Use native Node.js APIs for filesystem operations
import * as fs from "node:fs";
import * as os from "node:os";

// Desktop notifications use pending-file fallback (no subprocess)
import { OperatorNotifier } from "../warroom/notifier";
const notifier = new OperatorNotifier();
notifier.notify({ ... });  // Writes to pending JSON file
```

If you MUST execute an external command, add the handler to `bridge_server.py` which runs `subprocess.run` with array args (safe from shell injection). Never shell out from TypeScript directly.

---

## Config

`~/.milimo/config.json` is the single source of truth.

- No separate `state.json`
- All commands read from and write to one file

---

## Cost Guard

- Daily cloud token budget: 50,000
- Alert at 80%
- Fallback strategy: `lighter_prompt` (reduce max_tokens 50%, trim enrichment context)
- Never block a claw action — always fallback, never fail

---

## Python Style

- Type hints on all function signatures
- Docstrings on public methods
- Max line length: 100
- Use f-strings for formatting

---

## TypeScript Style

- Strict mode enabled
- Async/await over promises
- Interface over type alias for objects
- Explicit return types on functions

---

## Related Pages

- [[testing]] — Test conventions
- [[debugging]] — Debug guide
