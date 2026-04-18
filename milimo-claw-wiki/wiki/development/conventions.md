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

## Shell Commands (TypeScript)

Use `child_process.spawn` with array args.

```typescript
// Good
import { spawn } from 'child_process';
spawn('git', ['commit', '-m', message]);

// Bad
exec(`git commit -m "${message}"`);  // Injection risk
```

Never template literal shell strings — injection risk.

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
