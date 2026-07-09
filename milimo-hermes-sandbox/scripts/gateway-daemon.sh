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

export HOME="/sandbox"
HERMES_HOME="${HERMES_HOME:-/sandbox/.hermes}"
ENV_FILE="${HERMES_HOME}/.env"
GATEWAY_LOG="${HERMES_HOME}/logs/gateway-daemon.log"
DAEMON_PIDFILE="/var/run/gateway-daemon.pid"
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
  pgrep -n -f 'hermes gateway run' 2>/dev/null || true
}

gateway_running() {
  [ -n "$(gateway_pid)" ]
}

daemon_pidfile_write() {
  echo "$$" >"${DAEMON_PIDFILE}"
}

daemon_pidfile_check() {
  if [ -f "${DAEMON_PIDFILE}" ]; then
    local existing_pid
    existing_pid="$(cat "${DAEMON_PIDFILE}" 2>/dev/null || true)"
    if [ -n "${existing_pid}" ] && kill -0 "${existing_pid}" 2>/dev/null; then
      return 0
    fi
    rm -f "${DAEMON_PIDFILE}"
  fi
  return 1
}

stop_gateway() {
  local pid
  pid="$(gateway_pid)"
  if [ -n "${pid}" ]; then
    log "Stopping running gateway (PID ${pid})..."
    kill "${pid}" 2>/dev/null || true
  fi
  while IFS= read -r pid; do
    [ -n "${pid}" ] || continue
    [ "${pid}" = "$(gateway_pid)" ] && continue
    log "Stopping additional gateway instance (PID ${pid})..."
    kill "${pid}" 2>/dev/null || true
  done < <(pgrep -f 'hermes gateway run' 2>/dev/null || true)
}

start_gateway() {
  log "Starting Hermes gateway..."
  # hermes gateway run is foreground; background it via nohup.
  # --replace kills any previous instance to avoid duplicates.
  nohup hermes gateway run --replace >>"${GATEWAY_LOG}" 2>&1 &
  local pid=$!
  log "Gateway started with PID ${pid}"
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
  rm -f "${DAEMON_PIDFILE}"
  stop_gateway
  stop_socat_forwarder
  log "Daemon shutting down"
  exit 0
}

trap cleanup SIGTERM SIGINT

log "=== Gateway daemon starting ==="
ensure_env

# Prevent concurrent daemon instances (.bashrc + /etc/init.d/ both fire this script)
if daemon_pidfile_check; then
  log "Another daemon instance is already running; exiting"
  exit 0
fi

# Start socat forwarder so the nemohermes health probe (:8642/health) works.
start_socat_forwarder

# only start if a gateway is not already running on the Hermes API port.
# nemoclaw-start (start.sh) is the canonical launcher; the daemon must not
# race it, otherwise two gateways collide on port 18642 and Telegram polling.
if ss -Htn 2>/dev/null | grep -qE "[:.]18642\b" \
  || (command -v netstat >/dev/null 2>&1 && netstat -Htn 2>/dev/null | grep -qE "[:.]18642\b"); then
  log "Port 18642 already bound — assuming start.sh manages the gateway; entering monitor-only mode"
  # shellcheck disable=SC2034  # informational flag; currently unused but kept for future use
  GATEWAY_STARTED_BY_DAEMON=0
elif gateway_running; then
  log "Gateway already running (PID $(gateway_pid)); monitoring only"
  # shellcheck disable=SC2034
  GATEWAY_STARTED_BY_DAEMON=0
else
  start_gateway
  # shellcheck disable=SC2034
  GATEWAY_STARTED_BY_DAEMON=1
fi
daemon_pidfile_write

# Monitor loop — ensures both gateway and socat stay alive, but never
# races nemoclaw-start by launching a second gateway while port 18642 is
# already bound.
while true; do
  sleep "${POLL_INTERVAL}"
  if ! gateway_running; then
    # nemoclaw-start may have replaced the gateway between our last check and
    # this one; confirm the port is free before launching.
    if ss -Htn 2>/dev/null | grep -qE "[:.]18642\b" \
      || (command -v netstat >/dev/null 2>&1 && netstat -Htn 2>/dev/null | grep -qE "[:.]18642\b"); then
      continue
    fi
    log "Gateway not running; restarting..."
    ensure_env
    start_gateway
  fi
  if ! socat_running; then
    log "socat forwarder not running; restarting..."
    start_socat_forwarder
  fi
done
