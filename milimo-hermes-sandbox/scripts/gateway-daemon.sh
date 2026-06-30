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
  pgrep -f 'hermes.*gateway.*run' 2>/dev/null || true
}

gateway_running() {
  [ -n "$(gateway_pid)" ]
}

start_gateway() {
  log "Starting Hermes gateway..."
  # hermes gateway run is foreground; background it via nohup
  nohup hermes gateway run >>"${GATEWAY_LOG}" 2>&1 &
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

cleanup() {
  stop_gateway
  log "Daemon shutting down"
  exit 0
}

trap cleanup SIGTERM SIGINT SIGHUP

log "=== Gateway daemon starting ==="
ensure_env

# Only start if not already running (e.g., nemoclaw CLI already recovered it)
if gateway_running; then
  log "Gateway already running (PID $(gateway_pid)); monitoring only"
else
  start_gateway
fi

# Monitor loop
while true; do
  sleep "${POLL_INTERVAL}"
  if ! gateway_running; then
    log "Gateway not running; restarting..."
    ensure_env
    start_gateway
  fi
done
