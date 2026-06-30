#!/bin/sh
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Custom entrypoint for Milimo Hermes sandbox.
#
# Starts the Hermes gateway daemon at boot using gosu (privilege-dropping
# tool installed by the base image), then chains to docker-entrypoint.sh
# which runs openshell-sandbox (PID 1).

set -eu

# Start the gateway daemon in background as the sandbox user.
# The daemon will be re-parented to PID 1 automatically.
if [ -x /opt/hermes/scripts/gateway-daemon.sh ]; then
  gosu sandbox:sandbox /opt/hermes/scripts/gateway-daemon.sh &
fi

# Give the daemon a moment to start the gateway before openshell-sandbox
# takes over.  The gateway log will be at /sandbox/.hermes/logs/gateway-daemon.log.
sleep 2

# Chain to the base image entrypoint.  The base image provides
# docker-entrypoint.sh which execs the CMD (openshell-sandbox).
exec /usr/local/bin/docker-entrypoint.sh "$@"
