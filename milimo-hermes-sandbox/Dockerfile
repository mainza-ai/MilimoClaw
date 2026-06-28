# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# MilimoClaw Hermes Sandbox Dockerfile
#
# This Dockerfile extends the NemoClaw Hermes sandbox base image to include
# the Milimo Hermes plugin with all 6 claw handlers.
#
# Build: docker build -t milimo-hermes-sandbox:latest -f milimo-hermes-sandbox/Dockerfile .
# Onboard: nemohermes onboard --name milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile

# --- NemoClaw Hermes Base Image ---
# This base image includes:
# - Ubuntu 22.04 with Python 3.11
# - Hermes agent runtime
# - NemoClaw Hermes plugin at /sandbox/.hermes/plugins/nemoclaw
# - OpenShell L7 proxy for credential injection
# - Default network policies (Restricted tier)
# - Dashboard assets at /opt/hermes/ui-tui
FROM ghcr.io/nvidia/nemoclaw/hermes-sandbox-base:v0.3.0

# --- Build-time Configuration ---
# These ARGs can be overridden at build time
ARG NEMOCLAW_HERMES_DASHBOARD_TUI=1
ARG SLACK_ALLOWED_CHANNELS=""
ARG CHAT_UI_URL=""

# Set build-time environment variables for NemoClaw Hermes
ENV NEMOCLAW_HERMES_DASHBOARD_TUI=${NEMOCLAW_HERMES_DASHBOARD_TUI}
ENV SLACK_ALLOWED_CHANNELS=${SLACK_ALLOWED_CHANNELS}
ENV CHAT_UI_URL=${CHAT_UI_URL}

# --- Install Milimo Hermes Plugin ---
# Copy plugin source to sandbox
COPY ../milimo-hermes-plugin/ /opt/milimo-hermes-plugin/

# Install plugin into Hermes venv
RUN mkdir -p /sandbox/.hermes/plugins/milimo-hermes \
    && cp -a /opt/milimo-hermes-plugin/. /sandbox/.hermes/plugins/milimo-hermes/ \
    && /opt/hermes/.venv/bin/python -m pip install --no-cache-dir -r /opt/milimo-hermes-plugin/requirements.txt \
    && chown -R sandbox:sandbox /sandbox/.hermes/plugins/milimo-hermes \
    && chmod -R a+rX /sandbox/.hermes/plugins/milimo-hermes

# --- Preserve NemoClaw Hermes Image Contract ---
# CRITICAL: Do NOT remove /sandbox/.hermes/plugins/nemoclaw
# This plugin provides core NemoClaw functionality for Hermes profile

# --- Install Milimo Core as Local Package ---
# Alternative to PyPI install - copy and install milimo-core locally
COPY ../milimo-core/ /opt/milimo-core/
RUN /opt/hermes/.venv/bin/python -m pip install --no-cache-dir /opt/milimo-core/

# --- Install War Room HTML ---
# Serve standalone War Room at /warroom endpoint
COPY ../milimo-hermes-plugin/warroom/ /opt/hermes/warroom/

# --- Set Default Sandbox Name ---
# Prevents collision with default 'hermes' sandbox
ENV NEMOCLAW_SANDBOX_NAME=milimo-hermes

# --- Default Policy Presets ---
# Apply github preset (not in any baseline tier) for Build Claw
ENV NEMOCLAW_POLICY_PRESETS=restricted,github

# --- Entrypoint ---
# Use NemoClaw Hermes entrypoint (preserves nemoclaw-start)
ENTRYPOINT ["/opt/nemoclaw/nemoclaw-start"]

# --- Labels ---
LABEL org.opencontainers.image.title="MilimoClaw Hermes Sandbox"
LABEL org.opencontainers.image.description="Hermes sandbox with Milimo 6-claw plugin"
LABEL org.opencontainers.image.vendor="Mainza Kangombe"
LABEL org.opencontainers.image.licenses="Apache-2.0"
