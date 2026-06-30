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

# ── MilimoClaw Hermes Plugin Layer ──────────────────────────────────────────
# Install milimo-core and the Hermes plugin into the existing Hermes venv.
# The base image provides uv globally; use it to install into the Hermes venv.
USER root

# Use uv to install into the Hermes venv (base image has uv at /usr/local/bin/uv)
ENV UV_PROJECT_ENVIRONMENT=/opt/hermes/.venv

# Copy milimo-core first (changes less often → better layer caching)
COPY milimo-core/ /opt/milimo-core/
RUN chmod -R a+rX,go-w /opt/milimo-core/
RUN uv pip install --no-cache-dir -e /opt/milimo-core/

# Copy the Hermes plugin
COPY milimo-hermes-plugin/ /opt/milimo-hermes-plugin/
RUN chmod -R a+rX,go-w /opt/milimo-hermes-plugin/
RUN uv pip install --no-cache-dir -r /opt/milimo-hermes-plugin/requirements.txt \
    && uv pip install --no-cache-dir --no-deps -e /opt/milimo-hermes-plugin/

# Install plugin into Hermes plugin directory (standard Hermes location)
RUN mkdir -p /sandbox/.hermes/plugins/milimo-hermes \
    && cp -a /opt/milimo-hermes-plugin/. /sandbox/.hermes/plugins/milimo-hermes/ \
    && chown -R sandbox:sandbox /sandbox/.hermes/plugins/milimo-hermes \
    && chmod -R a+rX /sandbox/.hermes/plugins/milimo-hermes

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
COPY milimo-hermes-sandbox/generate-config.ts /opt/nemoclaw-hermes-config/generate-config.ts
COPY milimo-hermes-sandbox/config/ /opt/nemoclaw-hermes-config/config/
RUN chmod -R a+rX /opt/nemoclaw-hermes-config/generate-config.ts \
    && find /opt/nemoclaw-hermes-config -type d -exec chmod 755 {} + \
    && find /opt/nemoclaw-hermes-config -type f -exec chmod 444 {} +

# Build args for config that varies per deployment
ARG NEMOCLAW_MODEL=nvidia/nemotron-3-super-120b-a12b
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
    NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64=${NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64}

WORKDIR /sandbox
USER sandbox

# Generate Hermes config.yaml and .env from build args
RUN node --experimental-strip-types /opt/nemoclaw-hermes-config/generate-config.ts

# Write default SOUL.md (Hermes identity)
RUN mkdir -p /sandbox/.hermes/memories \
    && printf '%s' \
    'You are Hermes Agent, an intelligent AI assistant created by Nous Research. You are helpful, knowledgeable, and direct. You assist users with a wide range of tasks including answering questions, writing and editing code, analyzing information, creative work, and executing actions via your tools. You communicate clearly, admit uncertainty when appropriate, and prioritize being genuinely useful over being verbose unless otherwise directed below. Be targeted and efficient in your exploration and investigations.' \
    > /sandbox/.hermes/SOUL.md

# Describe execution environment via Hermes environment-hint mechanism
ENV HERMES_ENVIRONMENT_HINT="You are running inside an NVIDIA OpenShell sandbox with MilimoClaw Hermes profile, with inference routed through NemoClaw. Your terminal, file, and web tools execute against the sandbox filesystem and egress through the OpenShell L7 proxy, which enforces network policy and rewrites credentials at the boundary, so you never see raw secrets. Your config and memory live under /sandbox/.hermes and are mutable unless shields are up. Work within the sandbox boundary."

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

# Pin config hash at build time for integrity verification
RUN mkdir -p /etc/nemoclaw \
    && sha256sum /sandbox/.hermes/config.yaml /sandbox/.hermes/.env \
    > /etc/nemoclaw/hermes.config-hash \
    && chown root:root /etc/nemoclaw/hermes.config-hash \
    && chmod 444 /etc/nemoclaw/hermes.config-hash

RUN sha256sum /sandbox/.hermes/config.yaml /sandbox/.hermes/.env \
    > /sandbox/.hermes/.config-hash \
    && chmod 600 /sandbox/.hermes/.config-hash \
    && chown sandbox:sandbox /sandbox/.hermes/.config-hash

RUN if [ "$NEMOCLAW_DARWIN_VM_COMPAT" = "1" ]; then \
        chmod -R a+rwX /sandbox/.hermes; \
        find /sandbox/.hermes -type d -exec chmod a+rwx {} +; \
        chmod a+rw /sandbox/.bashrc /sandbox/.profile; \
    fi

# Runtime environment
ENV MILIMO_PROFILE=hermes \
    MILIMO_PLUGIN_DIR=/sandbox/.hermes/plugins/milimo-hermes \
    DELEGATION_MAX_CONCURRENT_CHILDREN=6 \
    NEMOCLAW_HERMES_DASHBOARD_TUI=1

# Upstream ENTRYPOINT handles privilege separation via nemoclaw-start (s6 supervision)
# We inherit it from the base image - no changes needed.

# Pass through build-time git SHA for hermes_build_sha
ARG HERMES_GIT_SHA=
