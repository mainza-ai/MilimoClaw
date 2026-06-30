#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Wrapper for openshell-sandbox that starts the Hermes gateway daemon before
# handing control to the real openshell-sandbox binary.
#
# nemohermes overrides the container ENTRYPOINT to openshell-sandbox directly,
# so we replace the binary at /opt/openshell/bin/openshell-sandbox with this
# wrapper.  The real binary lives at openshell-sandbox.real.

set -eu

if [ -x /opt/hermes/scripts/gateway-daemon.sh ]; then
  /opt/hermes/scripts/gateway-daemon.sh &
fi

sleep 2

exec /opt/openshell/bin/openshell-sandbox.real "$@"
