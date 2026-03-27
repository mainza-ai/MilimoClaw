# Quick Reference: Deploy Plugin to Sandbox

**Last Updated:** 2026-03-27
**Status:** ✅ Verified Working

> **Key insight:** `nemoclaw connect` runs as the `sandbox` user (uid 999, home `/sandbox`), NOT root.
> Plugin files must be at `/sandbox/extensions/milimo/` and registered in `/sandbox/.openclaw/openclaw.json`.

---

## One-Liner Full Deploy (Copy-Paste Ready)

```bash
# Full redeploy from host (run from MilimoClaw/milimo directory)
cd /Users/mck/Desktop/MilimoClaw/milimo && \
  npm run build && \
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-full.tar.gz --no-mac-metadata dist openclaw.plugin.json package.json node_modules && \
  PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}') && \
  cat /tmp/milimo-plugin-full.tar.gz | docker exec -i openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c 'cat > /tmp/milimo-plugin-full.tar.gz' && \
  docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c '
    mkdir -p /tmp/milimo-extract && cd /tmp/milimo-extract && \
    tar xzf /tmp/milimo-plugin-full.tar.gz --warning=no-unknown-keyword && \
    mkdir -p /sandbox/extensions/milimo && \
    rm -rf /sandbox/extensions/milimo/* && \
    cp -r dist openclaw.plugin.json package.json node_modules /sandbox/extensions/milimo/ && \
    chown -R sandbox:sandbox /sandbox/extensions/milimo && \
    find /sandbox/extensions/milimo -name "._*" -delete
  ' && \
  echo "✅ Plugin deployed successfully"
```

> **Also deploy support files** (needed for assistant setup during onboard):

```bash
# Copy system prompt template to sandbox
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}')
cat /Users/mck/Desktop/MilimoClaw/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md | \
  docker exec -i openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c '
    mkdir -p /sandbox/.milimo && \
    cat > /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md && \
    chown -R sandbox:sandbox /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
  '

# Copy assistant_setup.py to sandbox
cat /Users/mck/Desktop/MilimoClaw/milimo-blueprint/orchestrator/assistant_setup.py | \
  docker exec -i openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c '
    mkdir -p /sandbox/milimo-blueprint/orchestrator && \
    cat > /sandbox/milimo-blueprint/orchestrator/assistant_setup.py && \
    chown -R sandbox:sandbox /sandbox/milimo-blueprint
  '
echo "✅ Support files deployed"
```

---

## Step-by-Step Deploy

```bash
# 1. Build locally
cd /Users/mck/Desktop/MilimoClaw/milimo && npm run build

# 2. Create tar (MUST include node_modules, MUST use --no-mac-metadata)
COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-full.tar.gz \
  --no-mac-metadata \
  dist openclaw.plugin.json package.json node_modules

# 3. Find sandbox PID
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep 999 | awk '{print $2}')

# 4. Pipe into sandbox namespace
cat /tmp/milimo-plugin-full.tar.gz | \
  docker exec -i openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  bash -c 'cat > /tmp/milimo-plugin-full.tar.gz'

# 5. Extract, copy to /sandbox/extensions/, fix ownership
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- bash -c '
  mkdir -p /tmp/milimo-extract && cd /tmp/milimo-extract && \
  tar xzf /tmp/milimo-plugin-full.tar.gz --warning=no-unknown-keyword && \
  mkdir -p /sandbox/extensions/milimo && \
  rm -rf /sandbox/extensions/milimo/* && \
  cp -r dist openclaw.plugin.json package.json node_modules /sandbox/extensions/milimo/ && \
  chown -R sandbox:sandbox /sandbox/extensions/milimo && \
  find /sandbox/extensions/milimo -name "._*" -delete
'
```

---

## Verify Deployment

```bash
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}')

# Check files are present
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- ls -la /sandbox/extensions/milimo/

# Verify runtime deps exist
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  ls /sandbox/extensions/milimo/node_modules/ | grep -E '^(blessed|commander|ws|yaml|zod)$'

# Check plugin loaded AS SANDBOX USER (should show "loaded", not "error")
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  su - sandbox -c "openclaw plugins list 2>&1" | grep milimo

# Or connect interactively:
nemoclaw my-assistant connect
# Inside sandbox:
openclaw milimo --help
openclaw milimo onboard
```

### Verify Solo Template Fix

```bash
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}')

# Should return 1 (fix is present)
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  grep -c "definitively solo" /sandbox/extensions/milimo/dist/commands/onboard.js

# Verify assistant template is available
docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- \
  ls -la /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
```

---

## First-Time Setup: Update Sandbox openclaw.json

Only needed once. Injects plugin config into the **sandbox user's** config:

```bash
PID=$(docker exec openshell-cluster-nemoclaw ps aux | grep "sleep infinity" | grep -v grep | awk '{print $1}')

docker exec openshell-cluster-nemoclaw nsenter -t $PID -a -- python3 -c "
import json
with open('/sandbox/.openclaw/openclaw.json') as f:
    config = json.load(f)

config['plugins'] = {
    'load': {
        'paths': ['/sandbox/extensions/milimo']
    },
    'entries': {
        'milimo': {
            'enabled': True
        }
    },
    'installs': {
        'milimo': {
            'source': 'path',
            'sourcePath': '/sandbox/extensions/milimo',
            'installPath': '/sandbox/extensions/milimo',
            'version': '0.1.0',
            'installedAt': '2026-03-27T18:50:00.000Z'
        }
    }
}

with open('/sandbox/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print('Sandbox config updated successfully')
"
```

> **Warning:** Do NOT edit `/root/.openclaw/openclaw.json` — that is NOT the config used by `nemoclaw connect` sessions.

---

## Sandbox Management

```bash
# Create sandbox
NVIDIA_API_KEY="nvapi-..." NEMOCLAW_RECREATE_SANDBOX=1 nemoclaw onboard --non-interactive

# Connect (opens shell as sandbox user)
nemoclaw my-assistant connect

# Check status
nemoclaw my-assistant status

# View logs
nemoclaw my-assistant logs --tail 50

# Destroy
nemoclaw my-assistant destroy --yes
```

---

## Common Issues

| Issue | Fix |
|-------|-----|
| `unknown command 'milimo'` | Plugin not in sandbox user's config — update `/sandbox/.openclaw/openclaw.json` |
| Plugin shows `error` status | Missing `node_modules` — rebuild tar with deps included |
| Can't find PID | `docker exec openshell-cluster-nemoclaw ps aux \| grep "sleep infinity"` |
| Files not visible in sandbox | Use pipe method (`cat \| docker exec -i nsenter`), not `docker cp` |
| World-writable error | Copy to `/sandbox/extensions/`, not `/tmp` |
| Wrong ownership | `chown -R sandbox:sandbox /sandbox/extensions/milimo` |
| macOS `._*` files | Use `COPYFILE_DISABLE=1 tar --no-mac-metadata` |
| `Invalid extensions directory` | Extensions dir is a symlink — use `/sandbox/extensions/` instead |
| Config points to `/root/` | Wrong config — update `/sandbox/.openclaw/openclaw.json` |

---

## Key Path Reference

| Path | User | Purpose |
|------|------|---------|
| `/sandbox/extensions/milimo/` | sandbox | ✅ Plugin install location (working) |
| `/sandbox/.openclaw/openclaw.json` | sandbox | ✅ Config read by `nemoclaw connect` sessions |
| `/root/.openclaw/openclaw.json` | root | ❌ Root-only config, not used by sandbox |
| `/sandbox/.openclaw-data/extensions/` | sandbox | ❌ Overlayfs blocks writes here |
| `/tmp/` | any | ❌ World-writable, rejected by OpenClaw security |
