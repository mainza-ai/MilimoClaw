#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# gateway-daemon.sh - Hermes gateway supervisor for Milimo sandbox
#
# Ensures the Hermes gateway stays running inside the sandbox.  Launched by
# /etc/init.d/hermes-gateway at boot (SysV rcS.d).  Checks every 30 s and
# re-spawns the gateway if it has exited.

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-/sandbox/.hermes}"
ENV_FILE="${HERMES_HOME}/.env"
GATEWAY_LOG="${HERMES_HOME}/logs/gateway-daemon.log"
POLL_INTERVAL=30

# socat forwarder: Hermes API server binds to 127.0.0.1:18642.
# OpenShell port forwarding (--forward 8642) expects a listener on 0.0.0.0:8642.
SOCAT_PUBLIC_PORT=8642
SOCAT_INTERNAL_PORT=18642

log() {
  local ts
  ts="$(date -Iseconds 2>/dev/null || date)"
  echo "[${ts}] $*" >>"${GATEWAY_LOG}"
}

ensure_env() {
  if [ -f "${ENV_FILE}" ]; then
    set -a
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    set +a
  else
    log "WARN: .env not found at ${ENV_FILE}"
  fi

  if [ -z "${API_SERVER_KEY:-}" ]; then
    log "WARN: API_SERVER_KEY is empty or unset; gateway may fail to authenticate"
  fi
}

gateway_pid() {
  pgrep -f 'hermes gateway run' 2>/dev/null || true
}

gateway_running() {
  [ -n "$(gateway_pid)" ]
}

start_gateway() {
  log "Starting Hermes gateway..."
  # hermes gateway run is foreground; background it via nohup.
  # --replace kills any previous instance to avoid duplicates.
  nohup hermes gateway run --replace >>"${GATEWAY_LOG}" 2>&1 &
  local pid=$!
  log "Gateway started with PID ${pid}"
}

stop_gateway() {
  local pid
  pid="$(gateway_pid)"
  if [ -n "${pid}" ]; then
    log "Stopping running gateway (PID ${pid})..."
    kill "${pid}" 2>/dev/null || true
  fi
}

# socat forwarder: Hermes API server binds to 127.0.0.1:18642.
# OpenShell expects a listener on 0.0.0.0:8642 for port forwarding.
socat_running() {
  pgrep -f "socat.*TCP-LISTEN:${SOCAT_PUBLIC_PORT}" >/dev/null 2>&1 || return 1
}

start_socat_forwarder() {
  socat_running && return 0
  if ! command -v socat >/dev/null 2>&1; then
    log "socat not available; port forwarding from host may not work"
    return 0
  fi
  nohup socat \
    TCP-LISTEN:"${SOCAT_PUBLIC_PORT}",bind=0.0.0.0,fork,reuseaddr \
    TCP:127.0.0.1:"${SOCAT_INTERNAL_PORT}" \
    >/dev/null 2>&1 &
  local pid=$!
  log "socat forwarder started (0.0.0.0:${SOCAT_PUBLIC_PORT} → 127.0.0.1:${SOCAT_INTERNAL_PORT}, PID ${pid})"
}

stop_socat_forwarder() {
  local pid
  pid="$(pgrep -f "socat.*TCP-LISTEN:${SOCAT_PUBLIC_PORT}" 2>/dev/null || true)"
  if [ -n "${pid}" ]; then
    log "Stopping socat forwarder (PID ${pid})..."
    kill "${pid}" 2>/dev/null || true
  fi
}

cleanup() {
  stop_gateway
  stop_socat_forwarder
  log "Daemon shutting down"
  exit 0
}

trap cleanup SIGTERM SIGINT SIGHUP

log "=== Gateway daemon starting ==="
ensure_env

# Start socat forwarder so the nemohermes health probe (:8642/health) works.
start_socat_forwarder

# Only start if not already running (e.g., nemoclaw CLI already recovered it)
if gateway_running; then
  log "Gateway already running (PID $(gateway_pid)); monitoring only"
else
  start_gateway
fi

# Monitor loop — ensures both gateway and socat stay alive.
while true; do
  sleep "${POLL_INTERVAL}"
  if ! gateway_running; then
    log "Gateway not running; restarting..."
    ensure_env
    start_gateway
  fi
  if ! socat_running; then
    log "socat forwarder not running; restarting..."
    start_socat_forwarder
  fi
done
