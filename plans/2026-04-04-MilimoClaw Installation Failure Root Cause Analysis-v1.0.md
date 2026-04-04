# MilimoClaw Installation Failure — Root Cause Analysis

## Executive Summary

Four distinct failure modes were identified, each with a different root cause. The issues span from a fundamental bash scripting bug to architectural problems in how OpenClaw discovers and loads plugins.

---

## Issue 1: "Unknown option: mainza / zulu" — Bash Argument Parsing Bug

### Root Cause
**`for arg in "$@"` loop is incompatible with `shift`**

`install.sh:77` uses `for arg in "$@"; do` which iterates over a **snapshot** of the arguments at loop entry. When `--operator-name)` calls `shift`, it modifies the positional parameters (`$1`, `$2`, etc.) but the `for` loop is already iterating over the original captured array. So after processing `--operator-name`, the loop's next iteration picks up `mainza` as a fresh argument — which hits the `*)` catch-all at line 116.

### Flow
```
$@ = ["--solo", "--operator-name", "mainza", "--squad-name", "zulu"]
Iteration 1: arg="--solo" → matched ✓
Iteration 2: arg="--operator-name" → shift (now $1="mainza", $2="--squad-name"...)
             OPERATOR_NAME="mainza" ← correct BUT...
Iteration 3: arg="--squad-name" ← this was $3 in original array, now $2
             shift → OPERATOR_NAME gets "--squad-name" value... no wait
             Actually: arg is "mainza" (from original $3) → hits *) catch-all → ERROR
```

### Fix
Replace `for arg in "$@"` with `while [[ $# -gt 0 ]]; do case "$1" in ...; shift; done` pattern.

---

## Issue 2: Plugin Not Showing in `openclaw plugins list`

### Root Cause
**Plugin installed to wrong path + ownership mismatch + no restart**

Three compounding issues:

1. **`openclaw plugins install /sandbox/extensions/milimo`** installs the plugin to `/root/.openclaw/extensions/milimo` (the OpenClaw default extension directory) but copies the source from `/sandbox/extensions/milimo`. The `dist/index.js` may not be included in the tar archive if the build-bundle.sh's `npm install --production` happens **before** `npm run build`, which removes `@types/blessed` and causes the TypeScript build to fail silently (tsc still emits but with errors).

2. **Ownership mismatch**: The tar archive is created with `--owner=sandbox --group=sandbox`, but when extracted to `/root/.openclaw/extensions/milimo` (owned by root), OpenClaw's plugin loader may reject files not owned by root.

3. **No gateway restart**: OpenClaw loads plugins at startup. After `openclaw plugins install`, the plugin registry is updated but the gateway process may need to reload to actually load the plugin's JavaScript. The `openclaw plugins list` shows "loaded" vs "not loaded" based on whether the plugin's entry point was successfully required.

### The Real Problem
The plugin is being installed but **not loaded** because:
- The plugin entry point (`dist/index.js`) either has runtime errors (missing deps)
- OpenClaw's plugin loader silently fails to require it
- No mechanism exists to restart the OpenClaw process inside the sandbox

---

## Issue 3: `openclaw milimo` → "unknown command 'milimo'"

### Root Cause
**Direct consequence of Issue 2**

The `milimo` subcommand only exists if the Milimo Claw plugin is **loaded**. Since the plugin failed to load (Issue 2), OpenClaw has no `milimo` command registered. This is not a separate bug — it's the symptom of the plugin not being loaded.

---

## Issue 4: Silent Failures Throughout

### Root Cause
**`2>/dev/null` suppresses all error output**

Throughout `install.sh`, nearly every sandbox command has `2>/dev/null` or `|| true`, which means:
- `docker cp` failures are hidden
- `kubectl cp` failures are hidden
- `openclaw plugins install` errors are hidden
- Plugin registration failures are hidden
- The install reports "success" even when steps silently failed

The `deploy_to_sandbox()` function at lines 386-393 has `2>/dev/null` on the entire kubectl exec block, so if `openclaw plugins install` fails with an error, the user never sees it.

---

## Detailed Fix Plan

### Fix 1: Rewrite CLI argument parser
```bash
# Replace for loop with while loop
while [[ $# -gt 0 ]]; do
  case "$1" in
    --operator-name) OPERATOR_NAME="$2"; shift 2 ;;
    --squad-name) SQUAD_NAME="$2"; shift 2 ;;
    ...
  esac
done
```

### Fix 2: Fix plugin loading pipeline
1. Build plugin **before** pruning devDependencies
2. Verify `dist/index.js` exists and is valid JS before packaging
3. Install plugin to the correct path
4. After `openclaw plugins install`, verify the plugin is actually loadable by running `openclaw milimo --help`
5. If not loaded, check `openclaw plugins list` for error details

### Fix 3: Remove `2>/dev/null` from critical paths
- Keep stderr visible for `openclaw plugins install`
- Add explicit error checking after each deployment step
- Fail fast instead of continuing with broken state

### Fix 4: Add plugin reload mechanism
- After installing the plugin, restart the OpenClaw gateway process
- Or use OpenClaw's hot-reload if available
- Verify with `openclaw milimo --help` before reporting success

---

## Priority

| Fix | Priority | Effort | Impact |
|---|---|---|---|
| 1. CLI argument parser | Critical | Low | User can't pass options |
| 2. Plugin loading | Critical | Medium | Core functionality broken |
| 3. Error visibility | High | Low | Can't debug failures |
| 4. Plugin reload | High | Low | Plugin won't activate |
