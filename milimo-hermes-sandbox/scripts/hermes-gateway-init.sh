#!/bin/sh
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# /etc/init.d/hermes-gateway  -  SysV init script for Hermes gateway daemon
#
# Starts the gateway daemon under the sandbox user at boot (rcS.d).
# Also provides manual stop/restart/status via:
#   /etc/init.d/hermes-gateway {start|stop|restart|status}

### BEGIN INIT INFO
# Provides:          hermes-gateway
# Required-Start:    $local_fs $syslog
# Required-Stop:     $local_fs $syslog
# Default-Start:     S
# Default-Stop:      0 1 6
# Short-Description: Hermes gateway daemon
# Description:       Ensures the Hermes gateway stays running for agent connectivity
### END INIT INFO

DAEMON="/opt/hermes/scripts/gateway-daemon.sh"
DAEMON_PIDFILE="/var/run/hermes-gateway-daemon.pid"
SANDOX_USER="sandbox"

daemon_pid() {
  pgrep -f "gateway-daemon.sh" 2>/dev/null | head -1 || echo ""
}

gateway_pid() {
  pgrep -f "/usr/local/bin/hermes gateway run" 2>/dev/null | head -1 || echo ""
}

start() {
  pid="$(daemon_pid)"
  if [ -n "${pid}" ]; then
    echo "hermes-gateway is already running (daemon PID ${pid})"
    return 0
  fi

  printf "Starting hermes-gateway: "
  su -s /bin/sh "${SANDOX_USER}" -c "nohup ${DAEMON} >/dev/null 2>&1 &"
  sleep 1
  pid="$(daemon_pid)"
  if [ -n "${pid}" ]; then
    echo "${pid}" >"${DAEMON_PIDFILE}"
    echo "OK (daemon PID ${pid})"
  else
    echo "FAILED"
    return 1
  fi
}

stop() {
  printf "Stopping hermes-gateway: "
  pid="$(daemon_pid)"
  if [ -n "${pid}" ]; then
    kill "${pid}" 2>/dev/null
    sleep 1
    pid="$(daemon_pid)"
    if [ -n "${pid}" ]; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  fi
  # Also stop any orphan gateway processes
  pid="$(gateway_pid)"
  if [ -n "${pid}" ]; then
    kill "${pid}" 2>/dev/null || true
  fi
  rm -f "${DAEMON_PIDFILE}"
  echo "OK"
}

restart() {
  stop
  sleep 1
  start
}

status() {
  dpid="$(daemon_pid)"
  gpid="$(gateway_pid)"
  if [ -n "${dpid}" ]; then
    if [ -n "${gpid}" ]; then
      echo "hermes-gateway is running (daemon PID ${dpid}, gateway PID ${gpid})"
    else
      echo "hermes-gateway daemon is running (PID ${dpid}) but gateway is down (daemon will restart it)"
    fi
    return 0
  fi
  if [ -n "${gpid}" ]; then
    echo "hermes-gateway process is running (orphan PID ${gpid}) but daemon is not"
    return 0
  fi
  echo "hermes-gateway is not running"
  return 1
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
