#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
set -e

# Resolve container ID dynamically or accept as command-line parameter
CONTAINER_ID="${1:-$(docker ps -q --filter "name=openshell-milimo-hermes" | head -n 1)}"

if [ -z "$CONTAINER_ID" ]; then
  echo "Error: No running openshell-milimo-hermes container found, and no container ID was provided."
  echo "Usage: $0 [container_id_or_name]"
  exit 1
fi

echo "======================================================================"
echo "          DEPLOYING COMPREHENSIVE MULTI-CLAW TEST WITH LUCY           "
echo "======================================================================"
echo "Deploying test_lucy_multi_claw.py into sandbox container ($CONTAINER_ID)..."

# Copy to sandbox container
docker cp test/integration_python/test_lucy_multi_claw.py "$CONTAINER_ID":/sandbox/.openclaw/milimo/milimo-blueprint/

# Mark as executable in sandbox
docker exec "$CONTAINER_ID" chmod +x /sandbox/.openclaw/milimo/milimo-blueprint/test_lucy_multi_claw.py

echo "Staging complete! Running integration test in container native environment..."
echo ""

# Execute the test
docker exec -t "$CONTAINER_ID" python3 /sandbox/.openclaw/milimo/milimo-blueprint/test_lucy_multi_claw.py
