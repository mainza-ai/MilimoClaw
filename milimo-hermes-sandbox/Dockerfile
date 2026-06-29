# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# MilimoClaw Hermes Sandbox Dockerfile
#
# Builds on top of the NousResearch/hermes-agent upstream image by installing
# milimo-core and the milimo-hermes-plugin into the Hermes venv.
#
# Build:  docker build -t milimo-hermes-sandbox:latest -f milimo-hermes-sandbox/Dockerfile .
#         docker build --build-arg HERMES_BASE_IMAGE=ghcr.io/nousresearch/hermes-agent@sha256:... ...
# Onboard: nemohermes onboard --name milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile

# ── Upstream Hermes Agent Base (Nous Research) ──────────────────────────────
# Pin by SHA for reproducible builds. To bump: pull the new image, run
# `docker inspect ghcr.io/nousresearch/hermes-agent:<tag> --format '{{index .RepoDigests 0}}'`
# and update the digest in .hermes-base-digest or CI resolve step. Do NOT use
# floating tags in production.
ARG HERMES_BASE_IMAGE=ghcr.io/nousresearch/hermes-agent:latest
ARG HERMES_BASE_SHA=

FROM ${HERMES_BASE_IMAGE}${HERMES_BASE_SHA:+@${HERMES_BASE_SHA}} AS hermes-base

# ── MilimoClaw Hermes Plugin Layer ──────────────────────────────────────────
# Install milimo-core and the Hermes plugin into the existing Hermes venv.
# The venv at /opt/hermes/.venv is owned by root and sealed read-only for
# the hermes user — we install as root here, same as upstream.
# hadolint ignore=DL3002
USER root

# Copy milimo-core first (changes less often → better layer caching)
COPY --chmod=a+rX,go-w milimo-core/ /opt/milimo-core/
RUN /opt/hermes/.venv/bin/pip install --no-cache-dir -e /opt/milimo-core/

# Copy the Hermes plugin
COPY --chmod=a+rX,go-w milimo-hermes-plugin/ /opt/milimo-hermes-plugin/
RUN /opt/hermes/.venv/bin/pip install --no-cache-dir -r /opt/milimo-hermes-plugin/requirements.txt \
    && /opt/hermes/.venv/bin/pip install --no-cache-dir --no-deps -e /opt/milimo-hermes-plugin/

# Install plugin into Hermes plugin directory (under the data volume)
RUN mkdir -p /opt/data/.hermes/plugins/milimo-hermes \
    && cp -a /opt/milimo-hermes-plugin/. /opt/data/.hermes/plugins/milimo-hermes/ \
    && chown -R hermes:hermes /opt/data/.hermes/plugins/milimo-hermes \
    && chmod -R a+rX /opt/data/.hermes/plugins/milimo-hermes

# Copy War Room static assets
COPY --chmod=a+rX,go-w milimo-hermes-plugin/warroom/ /opt/hermes/warroom/

# Bake Milimo install stamp alongside the agent code-scoped (not in /opt/data volume)
RUN printf 'milimo-hermes\n' > /opt/hermes/.milimo_install

# ── Runtime ──────────────────────────────────────────────────────────────────
# Inherit upstream ENTRYPOINT, CMD, VOLUME, ENV — no changes needed.
# Upstream uses s6-overlay /init as PID 1 with main-wrapper.sh.
# Milimo env vars added here; operator-specific config goes in /opt/data.

ENV MILIMO_PROFILE=hermes
ENV MILIMO_PLUGIN_DIR=/opt/data/.hermes/plugins/milimo-hermes
ENV DELEGATION_MAX_CONCURRENT_CHILDREN=6
ENV NEMOCLAW_HERMES_DASHBOARD_TUI=1

# Note: /opt/data is already declared as VOLUME in upstream — inherited.
# HERMES_HOME=/opt/data, HERMES_WRITE_SAFE_ROOT=/opt/data — also inherited.

# Pass through build-time git SHA for hermes_build_sha (upstream ARG)
ARG HERMES_GIT_SHA=
