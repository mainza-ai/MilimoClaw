# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# MilimoClaw Hermes Sandbox Dockerfile
#
# Extends the NVIDIA hermes-sandbox-base image (which pre-bakes Hermes Agent
# from GitHub releases) by adding milimo-core, the milimo-hermes-plugin,
# War Room assets, and Milimo-specific configuration.
#
# Build:  docker build -t milimo-hermes-sandbox:latest -f milimo-hermes-sandbox/Dockerfile .
# Onboard: nemohermes onboard --name milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile
#          (uses the Dockerfile as the "custom" layer on top of the base)

# ── NVIDIA Hermes Sandbox Base (Public GHCR) ────────────────────────────────
# Pin by SHA for reproducible builds. To bump: pull the new image, run
# `docker inspect ghcr.io/nvidia/nemoclaw/hermes-sandbox-base:latest --format '{{index .RepoDigests 0}}'`
# and update the digest in .hermes-base-digest.
ARG BASE_IMAGE=ghcr.io/nvidia/nemoclaw/hermes-sandbox-base@sha256:8dad3b989a9ed1e601743310b97be21be5f59f89f7913a47d04f3ec3c40b8ce6

FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── MilimoClaw Hermes Plugin Layer ──────────────────────────────────────────
# Install milimo-core and the Hermes plugin into the existing Hermes venv.
# The base image provides uv globally; use it to install into the Hermes venv.
USER root

# Use uv to install into the Hermes venv (base image has uv at /usr/local/bin/uv)
ENV UV_PROJECT_ENVIRONMENT=/opt/hermes/.venv

# Copy milimo-core first (changes less often → better layer caching)
COPY milimo-core/ /opt/milimo-core/
RUN chmod -R a+rX,go-w /opt/milimo-core/ \
    && uv pip install --no-cache-dir /opt/milimo-core/

# Also make milimo-core importable from the system Python interpreter
# (Hermes agent subprocesses may resolve `python3` to /usr/bin/python3)
RUN /usr/bin/python3 -c "import os, site; [open(os.path.join(d, 'milimo-core.pth'), 'w').write('/opt/milimo-core/src\n') for d in site.getsitepackages()]" || true \
    && /usr/bin/python3 -m pip install --break-system-packages pyyaml 2>/dev/null || true

# Copy the Hermes plugin
COPY milimo-hermes-plugin/ /opt/milimo-hermes-plugin/
RUN chmod -R a+rX,go-w /opt/milimo-hermes-plugin/
RUN uv pip install --no-cache-dir --no-deps -r /opt/milimo-hermes-plugin/requirements.txt \
    && uv pip install --no-cache-dir --no-deps -e /opt/milimo-hermes-plugin/

# Install plugin into Hermes plugin directory (standard Hermes location)
RUN mkdir -p /sandbox/.hermes/plugins/milimo-hermes \
    && cp -a /opt/milimo-hermes-plugin/. /sandbox/.hermes/plugins/milimo-hermes/ \
    && chown -R sandbox:sandbox /sandbox/.hermes/plugins/milimo-hermes \
    && chmod -R a+rX /sandbox/.hermes/plugins/milimo-hermes

# Ensure the sandbox user can read the editable-install source trees at
# runtime. sys.path contains /opt/milimo-core/src and the editable
# finder for milimo_hermes_plugin originally points to /opt/milimo-hermes-plugin/;
# the chowns below make both trees world-readable, then we reinstall the
# milimo-hermes-plugin editable install so its .pth finder points at the
# sandbox-owned copy under /sandbox/.hermes/plugins/milimo-hermes/.
RUN chown -R sandbox:sandbox /opt/milimo-core \
    && chmod -R a+rX /opt/milimo-core \
    && chown -R sandbox:sandbox /opt/milimo-hermes-plugin \
    && chmod -R a+rX /opt/milimo-hermes-plugin \
    && rm -f /opt/hermes/.venv/lib/python3.13/site-packages/__editable__.milimo_hermes_plugin-0.2.0.pth \
         /opt/hermes/.venv/lib/python3.13/site-packages/__editable___milimo_hermes_plugin_0_2_0_finder.py \
    && uv pip install --no-cache-dir --no-deps -e /sandbox/.hermes/plugins/milimo-hermes/

# Copy War Room static assets
COPY milimo-hermes-plugin/warroom/ /opt/hermes/warroom/
RUN chmod -R a+rX,go-w /opt/hermes/warroom/

# Copy blueprint for delegation/workflows
COPY milimo-blueprint/ /opt/nemoclaw-blueprint/
RUN chmod -R a+rX,go-w /opt/nemoclaw-blueprint/
RUN mkdir -p /sandbox/.nemoclaw/blueprints/0.1.0 \
    && cp -r /opt/nemoclaw-blueprint/* /sandbox/.nemoclaw/blueprints/0.1.0/ \
    && chown -R sandbox:sandbox /sandbox/.nemoclaw/blueprints/0.1.0

# Bake Milimo install stamp alongside the agent code
RUN printf 'milimo-hermes\n' > /opt/hermes/.milimo_install

# Generate Hermes config.yaml and .env from build args (adapted from NemoHermes)
# This mirrors agents/hermes/generate-config.ts but for Milimo profile
COPY generate-config.ts /opt/nemoclaw-hermes-config/generate-config.ts
COPY config/ /opt/nemoclaw-hermes-config/config/
RUN chmod -R a+rX /opt/nemoclaw-hermes-config/generate-config.ts \
    && find /opt/nemoclaw-hermes-config -type d -exec chmod 755 {} + \
    && find /opt/nemoclaw-hermes-config -type f -exec chmod 444 {} +

# Build args for config that varies per deployment
ARG NEMOCLAW_MODEL=stepfun-ai/step-3.7-flash
ARG NEMOCLAW_PROVIDER_KEY=inference
ARG NEMOCLAW_INFERENCE_BASE_URL=https://inference.local/v1
ARG CHAT_UI_URL=http://127.0.0.1:8642
ARG NEMOCLAW_MESSAGING_CHANNELS_B64=W10=
ARG NEMOCLAW_MESSAGING_ALLOWED_IDS_B64=e30=
ARG NEMOCLAW_DISCORD_GUILDS_B64=e30=
ARG NEMOCLAW_TELEGRAM_CONFIG_B64=e30=
ARG NEMOCLAW_WECHAT_CONFIG_B64=e30=
ARG NEMOCLAW_SLACK_CONFIG_B64=e30=
ARG NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER=0
ARG NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64=W10=
ARG NEMOCLAW_BUILD_ID=default
ARG NEMOCLAW_DARWIN_VM_COMPAT=0
ARG NEMOCLAW_MESSAGING_PLAN_B64=
ARG MILIMO_SPEND_TEST_MODE=true
ARG MILIMO_DAILY_SPEND_CAP_CENTS=10000
ARG MILIMO_OPERATOR=

ENV NEMOCLAW_MODEL=${NEMOCLAW_MODEL} \
    NEMOCLAW_PROVIDER_KEY=${NEMOCLAW_PROVIDER_KEY} \
    NEMOCLAW_INFERENCE_BASE_URL=${NEMOCLAW_INFERENCE_BASE_URL} \
    CHAT_UI_URL=${CHAT_UI_URL} \
    NEMOCLAW_MESSAGING_CHANNELS_B64=${NEMOCLAW_MESSAGING_CHANNELS_B64} \
    NEMOCLAW_MESSAGING_ALLOWED_IDS_B64=${NEMOCLAW_MESSAGING_ALLOWED_IDS_B64} \
    NEMOCLAW_DISCORD_GUILDS_B64=${NEMOCLAW_DISCORD_GUILDS_B64} \
    NEMOCLAW_TELEGRAM_CONFIG_B64=${NEMOCLAW_TELEGRAM_CONFIG_B64} \
    NEMOCLAW_WECHAT_CONFIG_B64=${NEMOCLAW_WECHAT_CONFIG_B64} \
    NEMOCLAW_SLACK_CONFIG_B64=${NEMOCLAW_SLACK_CONFIG_B64} \
    NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER=${NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER} \
    NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64=${NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64} \
    NEMOCLAW_MESSAGING_PLAN_B64=${NEMOCLAW_MESSAGING_PLAN_B64} \
    MILIMO_SPEND_TEST_MODE=${MILIMO_SPEND_TEST_MODE} \
    MILIMO_DAILY_SPEND_CAP_CENTS=${MILIMO_DAILY_SPEND_CAP_CENTS} \
    MILIMO_OPERATOR=${MILIMO_OPERATOR}

WORKDIR /sandbox
USER root

# Generate Hermes config.yaml and .env from build args
# The generator uses os.homedir(), which returns /root when run as USER root.
# We need the files at /sandbox/.hermes/ for the rest of this Dockerfile,
# so we set HOME=/sandbox only for this step.
RUN HOME=/sandbox node --experimental-strip-types /opt/nemoclaw-hermes-config/generate-config.ts

# Install the link-cli Node.js binary globally so the spend handler can invoke it.
# Runs as root so the global node_modules destination is writable.
USER root
RUN npm install -g @stripe/link-cli@0.8.2

# Drop back to sandbox user for runtime.
USER sandbox

# Write default SOUL.md (Hermes identity with MilimoClaw context)
# hadolint ignore=SC1088
RUN mkdir -p /sandbox/.hermes/memories \
    && cat << 'SOULEOF' > /sandbox/.hermes/SOUL.md
You are Hermes Agent running inside a MilimoClaw Hermes profile sandbox.

## What is MilimoClaw?
MilimoClaw is a multi-agent autonomous business platform built on NVIDIA NemoClaw.
It runs a squad of six autonomous AI "claws" that work as a coordinated business mesh:

- Content Claw: Creative -- posts, copy, email campaigns, brand assets
- Ops Claw: Management -- relationship health, scope briefs, deadline risk
- Analytics Claw: Intelligence -- weekly reports, anomaly detection, opportunity scores
- Finance Claw: Treasury -- Stripe invoicing, pricing, tax categorization, agent spend requests via Stripe Link
- Build Claw: Engineering -- GitHub issues, code writing, deployments, dependency audits
- Assistant Claw (Lucy): Orchestrator -- stateful process supervisor, operator query router, mesh coordinator

## Registered Tools
The following tools are registered and available to you:
- milimo_status: Get status of all 6 claws
- milimo_warroom: Unified War Room queue across all claws. Call with action=hold_queue to see all REVIEW and HOLD items. The same data is visible at http://localhost:9090/warroom.html -- use the TUI to approve or veto any item by clicking buttons; the POST routes dispatch to the correct handler via the warroom_bridge action handler registry.
- milimo_approve / milimo_veto: Legacy Ops-only shortcuts. Prefer milimo_warroom action=approve or veto with item_id, which now routes all claw types.
- milimo_spend: Finance Claw agent-initiated spend flow via Stripe Link CLI (two-stage: Stage 1 REVIEW, Stage 2 HOLD then release). Actions: queue_review, approve_review, block_review, release_hold, cancel_hold, status. Always use --test flag in test mode.
- delegate_task: Run multiple claw tasks in parallel through Hermes delegation

## War Room -- Unified Interface
The War Room is the operator's single view of everything pending approval.
Two surfaces show the same canonical queue (mesh_dir/inbox/war_room/*.json):

1. TUI: Open http://localhost:9090/warroom.html in a browser. Click Approve or Veto buttons -- POST routes dispatch to the correct claw handler via the live action handler registry.
2. Agent tool: Call milimo_warroom action=hold_queue to see all REVIEW and HOLD items.

Action ID prefixes by claw type:
- Ops: UUID (for example abc123def456)
- Finance spends: spend-review-<spend_id> (REVIEW), spend-hold-<spend_id> (HOLD)
- Finance invoices: review-<invoice_id> (REVIEW), hold-<invoice_id> (HOLD, ready to send)
- Build: pr-review-<pr_id>, pr-merge-hold-<pr_id>, deploy-hold-<deploy_id>
- Content: draft_id in pending_review status

Approve or veto any item from either surface. The bridge routes by action ID prefix to the correct handler.

## Finance Claw Spend Flow
When the operator asks for a spend flow demo or agent-initiated purchase:
1. Call milimo_spend with action=queue_review, claw=finance, merchant_name, merchant_url, amount_cents, justification (>=100 chars), payment_method_id (from link-cli payment-methods list), credential_type=card, test=true
2. After queue_review succeeds, the spend appears in the War Room as spend-review-<spend_id>. Tell the operator the exact action ID and that they can approve/veto from the War Room.
3. HARD RULE: If _check_link_cli_auth or handle_milimo_spend returns an approval_url, you MUST include the full URL verbatim in your response to the operator. Output the exact approval_url text. Do NOT paraphrase, summarize, omit, or replace it with a generic phrase like "please approve in the Link app" or "I have started a background poll". The operator cannot approve without the URL. After surfacing it, STOP and WAIT for the operator to confirm approval before calling any further tools. Do not proceed to release_hold or any other spend step until the operator explicitly confirms they have approved the device code.
4. After operator confirms approval, proceed with the full flow through the registered tool (do not fall back to raw shell unless the tool is unavailable).
5. The spend flow runs in test mode by default (MILIMO_SPEND_TEST_MODE=true). No real money is charged.
6. Payment method ID is obtained via: link-cli payment-methods list --format json

## Environment
- NVIDIA OpenShell sandbox, inference routed through NemoClaw
- Config and memory: /sandbox/.hermes
- Plugin: /sandbox/.hermes/plugins/milimo-hermes/
- War Room files: /sandbox/.hermes/mesh/inbox/war_room/
- War Room TUI: http://localhost:9090/warroom.html
- API: 127.0.0.1:18642

## Your Task
You are the MilimoClaw gateway agent. Help the operator manage the claw mesh,
execute tasks via tools, and coordinate multi-agent workflows. Prefer the registered
milimo_spend and milimo_warroom tools over raw shell invocations.
SOULEOF

# Describe execution environment via Hermes environment-hint mechanism
ENV HERMES_ENVIRONMENT_HINT="MilimoClaw Hermes profile sandbox on NemoClaw. Six-agent business mesh: Content, Ops, Analytics, Finance, Build, Assistant (Lucy). Unified War Room: milimo_warroom action=hold_queue shows all pending items. Same data visible at http://localhost:9090/warroom.html -- use the TUI to approve or veto items across all claws. Registered tools: milimo_status, milimo_warroom, milimo_approve, milimo_veto, milimo_spend (Finance Claw Stripe Link spend flow with --test mode), delegate_task. Plugin: /sandbox/.hermes/plugins/milimo-hermes/. link-cli at /sandbox/.npm-global/bin/link-cli. API: 127.0.0.1:18642. CRITICAL: When milimo_spend or _check_link_cli_auth returns an approval_url, always output the full URL verbatim to the operator. Do not paraphrase, omit, or replace it with a generic statement. The operator cannot approve without the exact URL. Wait for operator confirmation before proceeding. Work within sandbox boundary."

# Set mutable-default permissions (Hermes standard)
USER root
RUN set -eu; \
    config_dir=/sandbox/.hermes; \
    data_dir=/sandbox/.hermes-data; \
    mkdir -p "$config_dir"; \
    if [ -L "$data_dir" ]; then \
        echo "ERROR: refusing legacy layout cleanup because $data_dir is a symlink" >&2; \
        exit 1; \
    fi; \
    if [ -d "$data_dir" ]; then \
        for entry in "$data_dir"/*; do \
            [ -e "$entry" ] || [ -L "$entry" ] || continue; \
            if [ -L "$entry" ]; then \
                echo "ERROR: refusing legacy layout cleanup because $entry is a symlink" >&2; \
                exit 1; \
            fi; \
            name="$(basename "$entry")"; \
            target="$config_dir/$name"; \
            if [ -L "$target" ]; then \
                rm -f "$target"; \
            fi; \
            if [ -d "$entry" ]; then \
                mkdir -p "$target"; \
                cp -a "$entry"/. "$target"/; \
            elif [ ! -e "$target" ]; then \
                cp -a "$entry" "$target"; \
            fi; \
        done; \
        data_real="$(readlink -f "$data_dir" 2>/dev/null || printf '%s' "$data_dir")"; \
        while :; do \
            replaced_marker="$(mktemp)"; \
            rm -f "$replaced_marker"; \
            find "$config_dir" -type l -print | while IFS= read -r link; do \
                raw_target="$(readlink "$link" 2>/dev/null || true)"; \
                resolved_target="$(readlink -f "$link" 2>/dev/null || true)"; \
                legacy_target=0; \
                case "$raw_target" in "$data_real"/* | "$data_dir"/*) legacy_target=1 ;; esac; \
                case "$resolved_target" in "$data_real"/* | "$data_dir"/*) legacy_target=1 ;; esac; \
                if [ "$legacy_target" -eq 1 ]; then \
                    copy_target="$resolved_target"; \
                    if [ -z "$copy_target" ] || { [ ! -e "$copy_target" ] && [ ! -L "$copy_target" ]; }; then \
                        copy_target="$raw_target"; \
                    fi; \
                    if [ -d "$copy_target" ] && [ ! -L "$copy_target" ]; then \
                            rm -f "$link"; \
                            mkdir -p "$link"; \
                            cp -a "$copy_target"/. "$link"/; \
                    elif [ -e "$copy_target" ] || [ -L "$copy_target" ]; then \
                            rm -f "$link"; \
                            cp -a "$copy_target" "$link"; \
                    else \
                        echo "ERROR: legacy symlink target missing: $link -> ${raw_target:-$resolved_target}" >&2; \
                        exit 1; \
                    fi; \
                    : > "$replaced_marker"; \
                fi; \
            done; \
            if [ ! -e "$replaced_marker" ]; then \
                rm -f "$replaced_marker"; \
                break; \
            fi; \
            rm -f "$replaced_marker"; \
        done; \
        rm -rf "$data_dir"; \
    fi; \
    mkdir -p "$config_dir/memories" \
        "$config_dir/sessions" \
        "$config_dir/skills" \
        "$config_dir/plugins" \
        "$config_dir/cron" \
        "$config_dir/logs" \
        "$config_dir/logs/curator" \
        "$config_dir/skins" \
        "$config_dir/plans" \
        "$config_dir/workspace" \
        "$config_dir/profiles" \
        "$config_dir/cache" \
        "$config_dir/hooks" \
        "$config_dir/image_cache" \
        "$config_dir/audio_cache" \
        "$config_dir/pairing" \
        "$config_dir/platforms" \
        "$config_dir/platforms/whatsapp" \
        "$config_dir/platforms/whatsapp/session" \
        "$config_dir/weixin" \
        "$config_dir/weixin/accounts" \
        "$config_dir/runtime"; \
    if [ -e "$data_dir" ] || [ -L "$data_dir" ]; then \
        echo "ERROR: legacy data dir still exists after cleanup: $data_dir" >&2; \
        exit 1; \
    fi; \
    data_real="$(readlink -f "$data_dir" 2>/dev/null || printf '%s' "$data_dir")"; \
    find "$config_dir" -type l -print | while IFS= read -r link; do \
        raw_target="$(readlink "$link" 2>/dev/null || true)"; \
        resolved_target="$(readlink -f "$link" 2>/dev/null || true)"; \
        case "$raw_target" in \
            "$data_real"/* | "$data_dir"/*) \
                echo "ERROR: legacy symlink remains after cleanup: $link -> $raw_target" >&2; \
                exit 1; \
                ;; \
        esac; \
        case "$resolved_target" in \
            "$data_real"/* | "$data_dir"/*) \
                echo "ERROR: legacy symlink remains after cleanup: $link -> $resolved_target" >&2; \
                exit 1; \
                ;; \
        esac; \
    done; \
    rm -rf /root/.cache/pip /sandbox/.cache \
    && chown -R sandbox:sandbox /sandbox/.hermes \
    && chown gateway:sandbox /sandbox/.hermes/runtime \
    && chmod 3770 /sandbox/.hermes \
    && chmod 770 \
        /sandbox/.hermes/memories \
        /sandbox/.hermes/sessions \
        /sandbox/.hermes/skills \
        /sandbox/.hermes/plugins \
        /sandbox/.hermes/cron \
        /sandbox/.hermes/logs \
        /sandbox/.hermes/logs/curator \
        /sandbox/.hermes/skins \
        /sandbox/.hermes/plans \
        /sandbox/.hermes/workspace \
        /sandbox/.hermes/profiles \
        /sandbox/.hermes/cache \
        /sandbox/.hermes/hooks \
        /sandbox/.hermes/image_cache \
        /sandbox/.hermes/audio_cache \
        /sandbox/.hermes/pairing \
        /sandbox/.hermes/platforms \
        /sandbox/.hermes/platforms/whatsapp \
        /sandbox/.hermes/platforms/whatsapp/session \
        /sandbox/.hermes/weixin \
        /sandbox/.hermes/weixin/accounts \
        /sandbox/.hermes/runtime \
    && chmod 2770 \
        /sandbox/.hermes/platforms \
        /sandbox/.hermes/platforms/whatsapp \
        /sandbox/.hermes/platforms/whatsapp/session \
    && chmod 2770 /sandbox/.hermes/runtime \
    && chmod 640 /sandbox/.hermes/config.yaml \
    && chmod 640 /sandbox/.hermes/.env \
    && for name in state.db state.db-wal state.db-shm gateway.lock gateway_state.json channel_directory.json; do \
        rm -f "/sandbox/.hermes/${name}"; \
        ln -s "runtime/${name}" "/sandbox/.hermes/${name}"; \
    done

# ── Gateway Control & Secret Boundary Scripts ────────────────────────────────
# These must match the original NemoClaw Hermes sandbox structure and hashes,
# allowing the host-side nemohermes / openshell supervisor to recover, status,
# and validate the sandbox safely.
RUN mkdir -p /usr/local/lib/nemoclaw

COPY scripts/lib/sandbox-init.sh /usr/local/lib/nemoclaw/sandbox-init.sh
COPY scripts/lib/gateway-supervisor.sh /usr/local/lib/nemoclaw/gateway-supervisor.sh
COPY scripts/lib/sandbox-rlimits.sh /usr/local/lib/nemoclaw/sandbox-rlimits.sh
COPY scripts/start.sh /usr/local/bin/nemoclaw-start
COPY scripts/gateway-control.sh /usr/local/bin/nemoclaw-gateway-control
COPY scripts/managed-gateway-control.py /usr/local/lib/nemoclaw/managed-gateway-control.py
COPY scripts/validate-env-secret-boundary.py /usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py
COPY scripts/seed-dashboard-config.py /usr/local/lib/nemoclaw/seed-hermes-dashboard-config.py
COPY scripts/runtime-config-guard.py /usr/local/lib/nemoclaw/hermes-runtime-config-guard.py
COPY scripts/state-dir-guard.py /usr/local/lib/nemoclaw/state-dir-guard.py
COPY scripts/preloads/*.js /usr/local/lib/nemoclaw/preloads/

RUN chmod 755 /usr/local/bin/nemoclaw-start /usr/local/lib/nemoclaw/sandbox-init.sh /usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py /usr/local/lib/nemoclaw/seed-hermes-dashboard-config.py /usr/local/lib/nemoclaw/hermes-runtime-config-guard.py \
    && chown root:root /usr/local/bin/nemoclaw-gateway-control /usr/local/lib/nemoclaw/gateway-supervisor.sh /usr/local/lib/nemoclaw/state-dir-guard.py /usr/local/lib/nemoclaw/managed-gateway-control.py \
    && chmod 700 /usr/local/bin/nemoclaw-gateway-control \
    && chmod 500 /usr/local/lib/nemoclaw/state-dir-guard.py /usr/local/lib/nemoclaw/managed-gateway-control.py \
    && chmod 444 /usr/local/lib/nemoclaw/gateway-supervisor.sh \
    && if [ -d /usr/local/lib/nemoclaw/preloads ]; then \
        chown -R 0:0 /usr/local/lib/nemoclaw/preloads \
        && find /usr/local/lib/nemoclaw/preloads -type f -exec chmod 444 {} + \
        && find /usr/local/lib/nemoclaw/preloads -type d -exec chmod 755 {} + \
        ; \
    fi \
    && chmod 444 /usr/local/lib/nemoclaw/sandbox-rlimits.sh \
    && mkdir -p /etc/profile.d \
    && printf '%s\n' \
        '# NemoClaw sandbox resource limits — see sandbox-rlimits.sh (#2173)' \
        '[ -f /usr/local/lib/nemoclaw/sandbox-rlimits.sh ] && . /usr/local/lib/nemoclaw/sandbox-rlimits.sh && harden_resource_limits --quiet && verify_resource_limits --quiet || true' \
        > /etc/profile.d/nemoclaw-rlimits.sh \
    && chmod 444 /etc/profile.d/nemoclaw-rlimits.sh \
    && (chmod 644 /etc/bash.bashrc 2>/dev/null || true) \
    && { printf '%s\n' \
          '# NemoClaw sandbox resource limits — see sandbox-rlimits.sh (#2173)' \
          '[ -f /usr/local/lib/nemoclaw/sandbox-rlimits.sh ] && . /usr/local/lib/nemoclaw/sandbox-rlimits.sh && harden_resource_limits --quiet && verify_resource_limits --quiet || true' \
          ''; \
        if [ -f /etc/bash.bashrc ]; then \
          grep -Ev 'NemoClaw sandbox resource limits|sandbox-rlimits[.]sh' /etc/bash.bashrc || true; \
        fi; \
      } > /etc/bash.bashrc.new \
      && mv /etc/bash.bashrc.new /etc/bash.bashrc \
      && chmod 444 /etc/bash.bashrc

# Assert validator exists and is executable
RUN test -x /usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py \
    || { echo "ERROR: validate-hermes-env-secret-boundary.py missing or not executable" >&2; exit 1; }

# Cryptographic integrity check for validator and wrapper
ARG NEMOCLAW_HERMES_WRAPPER_SHA256=03e0afbe00e352d0dfcf14b99ea1821f9fd29f87dad49ce19add2ec96d1941cc
ARG NEMOCLAW_HERMES_VALIDATOR_SHA256=236194dcd21d8beeb988f662979249dbf47f52a95b0786bfc0d80e1b56a169b6
RUN printf '%s  %s\n' \
        "$NEMOCLAW_HERMES_VALIDATOR_SHA256" /usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py \
    | sha256sum -c - \
    || { echo "ERROR: validate-hermes-env-secret-boundary.py hash mismatch (update NEMOCLAW_HERMES_VALIDATOR_SHA256)" >&2; exit 1; }

COPY scripts/hermes-wrapper.py /usr/local/lib/nemoclaw/hermes-wrapper.py
RUN test -x /usr/bin/python3 \
    || { echo "ERROR: /usr/bin/python3 missing or not executable; hermes-wrapper shebang would ENOEXEC" >&2; exit 1; }
RUN printf '%s  %s\n' \
        "$NEMOCLAW_HERMES_WRAPPER_SHA256" /usr/local/lib/nemoclaw/hermes-wrapper.py \
    | sha256sum -c - \
    || { echo "ERROR: hermes-wrapper.py hash mismatch (update NEMOCLAW_HERMES_WRAPPER_SHA256)" >&2; exit 1; }

RUN mv /usr/local/bin/hermes /usr/local/bin/hermes.real \
    && install -m 0755 /usr/local/lib/nemoclaw/hermes-wrapper.py /usr/local/bin/hermes \
    && chmod 755 /usr/local/bin/hermes.real \
    && /usr/local/bin/hermes --version

# ── File Sync Scripts ───────────────────────────────────────────────────────
# In-sandbox claw file inventory tool used by host-side hermes-sync.sh.
COPY scripts/hermes-inventory.py /opt/hermes/scripts/hermes-inventory.py
RUN chmod 755 /opt/hermes/scripts/hermes-inventory.py \
    && chown sandbox:sandbox /opt/hermes/scripts/hermes-inventory.py

# ── Gateway Daemon (supervision only) ──────────────────────────────────────
# Bake the gateway daemon + init script so the Hermes gateway survives
# sandbox restarts after a shell connects.
#
# openshell-sandbox is the container ENTRYPOINT (added by `openshell sandbox
# create --from` after our Dockerfile builds), so we CANNOT wrap or replace
# it at build time.  Instead, the gateway daemon is started by ~/.bashrc /
# ~/.profile on shell login.  The init script is provided for environments
# where openshell-sandbox honours rcS.d.
#
# The nemohermes CLI also auto-recovery script (start.sh) already starts
# `hermes gateway run` inside the sandbox at boot and on connect.
COPY scripts/gateway-daemon.sh /opt/hermes/scripts/gateway-daemon.sh
COPY scripts/hermes-gateway-init.sh /etc/init.d/hermes-gateway
RUN chmod 755 /opt/hermes/scripts/gateway-daemon.sh \
    && chmod 755 /etc/init.d/hermes-gateway \
    && mkdir -p /opt/hermes/scripts \
    && chown -R root:root /etc/init.d/hermes-gateway \
    && if command -v update-rc.d >/dev/null 2>&1; then \
          update-rc.d hermes-gateway defaults; \
        else \
          ln -s /etc/init.d/hermes-gateway /etc/rcS.d/S99hermes-gateway; \
        fi

# Install gh CLI for Build Claw (GitHub issue management)
# hadolint ignore=DL3008
RUN if command -v apt-get >/dev/null 2>&1; then \
        apt-get update -qq && apt-get install -y -qq --no-install-recommends gh 2>/dev/null || \
        (curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
          | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
        && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
          | tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
        && apt-get update -qq && apt-get install -y -qq --no-install-recommends gh); \
    fi && rm -rf /var/lib/apt/lists/*

# Pin config hash at build time for integrity verification
RUN mkdir -p /etc/nemoclaw \
    && sha256sum /sandbox/.hermes/config.yaml /sandbox/.hermes/.env \
    > /etc/nemoclaw/hermes.config-hash \
    && chown root:root /etc/nemoclaw/hermes.config-hash \
    && chmod 444 /etc/nemoclaw/hermes.config-hash

RUN sha256sum /sandbox/.hermes/config.yaml /sandbox/.hermes/.env \
    > /sandbox/.hermes/.config-hash \
    && chmod 600 /sandbox/.hermes/.config-hash \
    && chown sandbox:sandbox /sandbox/.hermes/.config-hash \
    && if [ "$NEMOCLAW_DARWIN_VM_COMPAT" = "1" ]; then \
        chmod -R a+rwX /sandbox/.hermes; \
        find /sandbox/.hermes -type d -exec chmod a+rwx {} +; \
        chmod a+rw /sandbox/.bashrc /sandbox/.profile; \
    fi

# Start the gateway daemon on shell login (defense-in-depth — nemohermes
# recovery script also starts the gateway at connect time, but this ensures
# it stays running across reconnects and after crashes).
RUN { echo; echo "# Auto-start Hermes gateway daemon if not already running"; \
    echo "if [ -x /opt/hermes/scripts/gateway-daemon.sh ] && ! pgrep -f 'gateway-daemon.sh' >/dev/null 2>&1; then"; \
    echo "  /opt/hermes/scripts/gateway-daemon.sh >/dev/null 2>&1 &"; \
    echo "fi"; } >> /sandbox/.bashrc \
    && { echo; echo "# Auto-start Hermes gateway daemon on login"; \
       echo "[ -x /opt/hermes/scripts/gateway-daemon.sh ] && [ -z \"\$(pgrep -f gateway-daemon.sh 2>/dev/null)\" ] && /opt/hermes/scripts/gateway-daemon.sh >/dev/null 2>&1 &"; \
     } >> /sandbox/.profile \
    && { echo; echo "# Multi-user Stripe Link credentials isolation"; \
         echo "if [ -n \"\${MILIMO_OPERATOR:-}\" ]; then"; \
         echo "  export XDG_CONFIG_HOME=\"/sandbox/.config/users/\${MILIMO_OPERATOR}\""; \
         echo "fi"; } >> /sandbox/.bashrc \
    && { echo; echo "# Multi-user Stripe Link credentials isolation"; \
         echo "if [ -n \"\${MILIMO_OPERATOR:-}\" ]; then"; \
         echo "  export XDG_CONFIG_HOME=\"/sandbox/.config/users/\${MILIMO_OPERATOR}\""; \
         echo "fi"; } >> /sandbox/.profile \
    && chown sandbox:sandbox /sandbox/.bashrc /sandbox/.profile \
    && chmod 644 /sandbox/.bashrc /sandbox/.profile

# ── Claw Data Directories ──────────────────────────────────────────────────
# Pre-create claw filesystem roots at build time so the directory layout is
# baked into the image (not created lazily at runtime).  Layouts are defined
# centrally in milimo-core/src/milimo_core/claw_layouts.py — keep in sync.
# These paths are served by the Hermes file sync system to the host.
RUN mkdir -p /sandbox/.hermes/claws/build \
               /sandbox/.hermes/claws/content \
               /sandbox/.hermes/claws/ops \
               /sandbox/.hermes/claws/analytics \
               /sandbox/.hermes/claws/finance \
               /sandbox/.hermes/claws/assistant \
    && chown sandbox:sandbox /sandbox/.hermes/claws \
    && chmod 770 /sandbox/.hermes/claws \
    && for d in /sandbox/.hermes/claws/*/; do \
         chmod 770 "$d"; \
         chown sandbox:sandbox "$d"; \
       done

# Runtime environment
ENV MILIMO_PROFILE=hermes \
    MILIMO_PLUGIN_DIR=/sandbox/.hermes/plugins/milimo-hermes \
    DELEGATION_MAX_CONCURRENT_CHILDREN=6 \
    NEMOCLAW_HERMES_DASHBOARD_TUI=1

# Drop privileges (Hermes standard).
# Note: NemoClaw overrides container user to 'sandbox' at runtime per
# sandbox policy, so this setting is advisory but follows convention.
USER sandbox

# Pass through build-time git SHA for hermes_build_sha
ARG HERMES_GIT_SHA=
