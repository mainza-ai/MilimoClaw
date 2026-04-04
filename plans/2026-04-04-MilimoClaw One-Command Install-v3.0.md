# MilimoClaw One-Command Install — Definitive Implementation Plan

**Version:** 3.0  
**Date:** 2026-04-04  
**Status:** Ready for review

---

## What We Know Works (Verified)

The `QUICK_DEPLOY_COMMANDS.md` document contains the **verified working deployment flow** — every step was tested and confirmed. The `PLUGIN_DEPLOYMENT_TROUBLESHOOTING.md` documents every failure mode and its resolution. This plan is built exclusively from those verified patterns.

### The Verified Working Pattern

```
1. Build on host:     npm install && npm run build
2. Create tar:        COPYFILE_DISABLE=1 tar czf ... --no-mac-metadata
3. Find sandbox PID:  docker exec ... ps aux | grep "sleep infinity"
4. Transfer via pipe: cat file.tar.gz | docker exec -i ... nsenter -t $PID -a -- bash -c 'cat > /tmp/file.tar.gz'
5. Extract in sandbox: nsenter -t $PID -a -- bash -c 'tar xzf ... && chown -R sandbox:sandbox ...'
6. Update config:     nsenter -t $PID -a -- python3 -c "update /sandbox/.openclaw/openclaw.json"
7. Restart gateway:   nsenter -t $PID -a -- pkill -f openclaw (auto-restarts)
8. Verify:            nsenter -t $PID -a -- openclaw milimo --help
```

### What We Know DOESN'T Work

| Approach | Why It Fails |
|---|---|
| `docker cp` + `kubectl cp` | Files land in container overlayfs, NOT visible in sandbox mount namespace |
| Installing to `/tmp/` | OpenClaw rejects world-writable paths (mode 777) |
| Installing to `/root/.openclaw/extensions/` | Sandbox user (uid 999) can't access root's home |
| `openclaw plugins install --link` with symlinked dir | OpenClaw requires real directories |
| `kill -HUP` gateway | Kills the gateway, crashes the sandbox |
| `npm install` inside sandbox | Times out due to limited resources/network |
| Building bundle scripts that `rm -rf` each other's output | Second script deletes first script's work |

---

## The Problem

The current `install.sh` uses **every approach that doesn't work**:
- `docker cp` + `kubectl cp` for file transfer
- Extracts to wrong paths
- Never updates `/sandbox/.openclaw/openclaw.json`
- Never restarts the gateway
- `build-bundle.sh` and `build-blueprint-bundle.sh` clobber each other

The result: the plugin is never actually loaded in the sandbox, `openclaw milimo` doesn't exist, and the installer reports false success.

---

## The Plan

### Phase 1: Delete Broken Scripts (3 tasks)

| # | Task | File | Reason |
|---|---|---|---|
| 1.1 | Delete `scripts/build-bundle.sh` | `scripts/build-bundle.sh` | Clobbers blueprint bundle output, uses wrong tar flags |
| 1.2 | Delete `scripts/build-blueprint-bundle.sh` | `scripts/build-blueprint-bundle.sh` | Clobbers plugin bundle output |
| 1.3 | Delete `scripts/deploy-to-sandbox.sh` | `scripts/deploy-to-sandbox.sh` | Uses `docker cp` + `kubectl cp` (broken mechanism) |

### Phase 2: Rewrite install.sh — The Single Source of Truth (8 tasks)

The new `install.sh` will be a single script that does everything correctly, following the verified working pattern exactly.

| # | Task | Detail | Verified Pattern |
|---|---|---|---|
| 2.1 | Prerequisite check | Docker running, Node.js ≥22, npm, Python 3, `NVIDIA_API_KEY` env var | Same as current |
| 2.2 | NemoClaw bootstrap | If sandbox running → skip. If NemoClaw CLI exists → `nemoclaw start`. If not → clone + install non-interactively | Same as current |
| 2.3 | Build Milimo plugin on host | `cd milimo && npm install && npm run build` — build on host, not in sandbox | `QUICK_DEPLOY:60` |
| 2.4 | Create plugin tar with correct flags | `COPYFILE_DISABLE=1 tar czf --no-mac-metadata dist openclaw.plugin.json package.json node_modules` | `QUICK_DEPLOY:63-65` |
| 2.5 | Create blueprint tar | `tar czf --exclude='__pycache__' --exclude='*.pyc' milimo-blueprint/` | Same pattern |
| 2.6 | Transfer via nsenter pipe | `cat file.tar.gz | docker exec -i $GATEWAY nsenter -t $PID -a -- bash -c 'cat > /tmp/file.tar.gz'` | `QUICK_DEPLOY:71-73` |
| 2.7 | Extract + register in sandbox | nsenter to extract, chown, update openclaw.json, deploy support files | `QUICK_DEPLOY:76-84` + `QUICK_DEPLOY:135-165` |
| 2.8 | Restart gateway + verify | pkill openclaw (auto-restarts), then `openclaw milimo --help` | Verified manually |

### Phase 3: Fix Plugin Registration (2 tasks)

| # | Task | Detail |
|---|---|---|
| 3.1 | Update `/sandbox/.openclaw/openclaw.json` with plugin entries via Python inline script | Must set `plugins.load.paths`, `plugins.entries.milimo`, `plugins.installs.milimo` — exactly as in `QUICK_DEPLOY:140-157` |
| 3.2 | Deploy assistant system prompt template | Copy `MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md` to `/sandbox/.milimo/` via nsenter pipe |

### Phase 4: Non-Interactive Onboarding (2 tasks)

| # | Task | Detail |
|---|---|---|
| 4.1 | Write `/sandbox/.milimo/config.json` via Python inline script | Must include all 5 claws enabled, squad name, operator name, inference config — as current install.sh does but via nsenter |
| 4.2 | Run `openclaw milimo onboard --non-interactive` inside sandbox | After config is written, run onboard to finalize |

### Phase 5: Verification (2 tasks)

| # | Task | Detail |
|---|---|---|
| 5.1 | Verify plugin loaded | `openclaw plugins list | grep milimo` must show "loaded" status |
| 5.2 | Verify all 5 claws | Check `/sandbox/milimo-blueprint/orchestrator/{content,ops,analytics,finance,build}/` all exist with Python modules |

---

## Critical Design Rules (From Spec Documents)

1. **Solo template = all 5 claws active** — no role selection (`MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md`)
2. **Plugin MUST be at `/sandbox/extensions/milimo/`** — not `/root/`, not `/tmp/`
3. **Config MUST be `/sandbox/.openclaw/openclaw.json`** — not `/root/.openclaw/openclaw.json`
4. **Tar MUST include `node_modules/`** — sandbox can't run `npm install` reliably
5. **Tar MUST use `--no-mac-metadata`** — macOS adds `._*` resource fork files
6. **Tar MUST use `COPYFILE_DISABLE=1`** — prevents macOS metadata contamination
7. **Transfer MUST use nsenter pipe** — `docker cp` doesn't cross mount namespace
8. **Gateway MUST restart after plugin install** — no hot-reload exists
9. **Ownership MUST be `sandbox:sandbox`** — OpenClaw rejects non-root ownership on plugin files

---

## Target User Experience

```bash
$ ./install.sh --solo --operator-name "mainza" --squad-name "zulu" --non-interactive

  ── MilimoClaw v2.0 Installer ──────────────────────────────

  [✓] Docker running
  [✓] Node.js 22.22.1
  [✓] npm 10.9.4
  [✓] Python 3.12
  [✓] NVIDIA_API_KEY configured

  [INFO] Sandbox "my-assistant" already running
  [✓] Skipping NemoClaw bootstrap

  [INFO] Building Milimo plugin...
  [✓] Plugin built (dist/index.js)

  [INFO] Deploying to sandbox...
  [✓] Plugin transferred (nsenter pipe)
  [✓] Plugin extracted to /sandbox/extensions/milimo
  [✓] Blueprint deployed to /sandbox/milimo-blueprint
  [✓] Plugin registered in openclaw.json
  [✓] Support files deployed
  [✓] Gateway restarted

  [INFO] Configuring squad...
  [✓] Squad: zulu (solo template)
  [✓] Operator: mainza
  [✓] Claws: Content, Ops, Analytics, Finance, Build — all enabled

  [INFO] Verifying...
  [✓] Plugin loaded: Milimo Claw v0.1.0
  [✓] Commands: 16 available
  [✓] Build Claw: 13 modules present

  ──────────────────────────────────────────────────────────────
  MilimoClaw v2.0 — Installation Complete
  ──────────────────────────────────────────────────────────────

  Launch War Room:  nemoclaw my-assistant connect
                    openclaw milimo warroom

  Check status:     openclaw milimo health
  Connect:          nemoclaw my-assistant connect
```

---

## File Changes

| Action | File | Detail |
|---|---|---|
| **DELETE** | `scripts/build-bundle.sh` | Replaced by inline build in install.sh |
| **DELETE** | `scripts/build-blueprint-bundle.sh` | Replaced by inline build in install.sh |
| **DELETE** | `scripts/deploy-to-sandbox.sh` | Replaced by inline deploy in install.sh |
| **REWRITE** | `install.sh` | Complete rewrite using nsenter pipe transfer pattern |
| **KEEP** | `milimo-cli` | CLI wrapper — will be updated to proxy to sandbox correctly |
| **KEEP** | `uninstall.sh` | Already updated for sandbox-based approach |

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| nsenter not available in gateway container | Fallback to `docker exec` with PID discovery via `ps aux` |
| Sandbox PID changes between steps | Discover PID once, store in variable, use throughout |
| Gateway doesn't auto-restart after pkill | Detect and restart manually via `openclaw gateway run &` |
| openclaw.json is read-only (Landlock) | Write via nsenter as root, not as sandbox user |
| Tar too large for pipe | Split into plugin + blueprint transfers (already planned) |

---

## Implementation Order

1. Delete broken scripts (Phase 1)
2. Rewrite install.sh (Phase 2)
3. Test with existing sandbox: `./install.sh --solo --operator-name "mainza" --squad-name "zulu" --non-interactive`
4. Verify: `nemoclaw my-assistant connect` → `openclaw milimo --help`
5. Update milimo-cli wrapper to proxy commands correctly
6. Push to GitHub (only when asked)
