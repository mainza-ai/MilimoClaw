#!/bin/sh
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Custom entrypoint for Milimo Hermes sandbox.
#
# Starts the Hermes gateway daemon at boot, then chains to the base image's
# entrypoint (docker-entrypoint.sh) which runs openshell-sandbox (PID 1).
#
# NOTE: NemoClaw overrides the container user to 'sandbox' at runtime
# (per sandbox policy), so gosu/su privilege dropping is unnecessary.
# We run the daemon directly as the current (sandbox) user.

set -eu

# Start the gateway daemon in background.
# The daemon will be re-parented to PID 1 (openshell-sandbox) automatically.
# Commented out: start daemon only within the sandboxed namespace on login/connect.
# if [ -x /opt/hermes/scripts/gateway-daemon.sh ]; then
#   /opt/hermes/scripts/gateway-daemon.sh &
# fi

# Give the daemon a moment to start the gateway before openshell-sandbox
# takes over.  The gateway log will be at /sandbox/.hermes/logs/gateway-daemon.log.
sleep 2

# Chain to the base image entrypoint.  The base image provides
# docker-entrypoint.sh which execs the CMD (openshell-sandbox).
exec /usr/local/bin/docker-entrypoint.sh "$@"
