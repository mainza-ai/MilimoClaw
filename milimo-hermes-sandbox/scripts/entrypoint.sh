#!/bin/sh
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Custom entrypoint for Milimo Hermes sandbox.
#
# Starts the Hermes gateway daemon at boot, then chains to the base image's
# entrypoint (docker-entrypoint.sh) which runs openshell-sandbox.

set -eu

# Start the gateway daemon in background as the sandbox user.
# It will be re-parented to PID 1 (openshell-sandbox) automatically.
if [ -x /opt/hermes/scripts/gateway-daemon.sh ]; then
  # Must run as sandbox user; at this point we're still root (the base
  # entrypoint drops privileges later).
  su -s /bin/sh sandbox -c "nohup /opt/hermes/scripts/gateway-daemon.sh >/dev/null 2>&1 &"
fi

# Chain to the base image entrypoint.  The base image provides
# docker-entrypoint.sh which execs the CMD (openshell-sandbox).
exec /usr/local/bin/docker-entrypoint.sh "$@"
