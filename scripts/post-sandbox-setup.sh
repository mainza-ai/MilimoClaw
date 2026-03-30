#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Post-sandbox hook for NemoCllaw
# This script runs automatically after sandbox creation to deploy Milimo
#
# Usage: Add to .nemoclaw/hooks/post-create.sh or run manually

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Milimo Claw Post-Sandbox Setup                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Run the main deploy script
exec "$SCRIPT_DIR/deploy-milimo-plugin.sh"
