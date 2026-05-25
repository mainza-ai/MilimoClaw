#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
set -e

CONTAINER_ID="76647cfa3698"

echo "======================================================================"
echo "          DEPLOYNIG COMPREHENSIVE MULTI-CLAW TEST WITH LUCY           "
echo "======================================================================"
echo "Deploying test_lucy_multi_claw.py into sandbox container ($CONTAINER_ID)..."

# Copy to sandbox container
docker cp test_lucy_multi_claw.py "$CONTAINER_ID":/sandbox/.openclaw/milimo/milimo-blueprint/

# Mark as executable in sandbox
docker exec "$CONTAINER_ID" chmod +x /sandbox/.openclaw/milimo/milimo-blueprint/test_lucy_multi_claw.py

echo "Staging complete! Running integration test in container native environment..."
echo ""

# Execute the test
docker exec -t "$CONTAINER_ID" python3 /sandbox/.openclaw/milimo/milimo-blueprint/test_lucy_multi_claw.py
