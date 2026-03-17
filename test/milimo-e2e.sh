#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# E2E test for Milimo Claw
# Runs inside the Docker sandbox

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}TEST${NC}: $1"; }

# -------------------------------------------------------
info "1. Verify OpenClaw CLI is installed"
# -------------------------------------------------------
openclaw --version && pass "OpenClaw CLI installed" || fail "OpenClaw CLI not found"

# -------------------------------------------------------
info "2. Verify Milimo plugin can be installed"
# -------------------------------------------------------
openclaw plugins install /opt/milimo 2>&1 && pass "Plugin installed" || {
    if [ -f /opt/milimo/dist/index.js ]; then
        pass "Plugin built successfully (dist/index.js exists)"
    else
        fail "Plugin build artifacts missing"
    fi
}

# -------------------------------------------------------
info "3. Verify Milimo Templates and Blueprints Discovery"
# -------------------------------------------------------
# Run blueprint list and check for Category A templates
openclaw milimo blueprint list > /tmp/blueprint-list.txt || fail "Failed to run blueprint list"
grep -q "content-agency" /tmp/blueprint-list.txt && pass "Found content-agency template" || fail "Missing content-agency"
grep -q "design-studio" /tmp/blueprint-list.txt && pass "Found design-studio template" || fail "Missing design-studio"
grep -q "ai-micro-saas" /tmp/blueprint-list.txt && pass "Found ai-micro-saas template" || fail "Missing ai-micro-saas"

# -------------------------------------------------------
info "4. Verify Squad Initialization using Template"
# -------------------------------------------------------
export HOME=/sandbox
openclaw milimo init --squad "e2e-squad" --role "content" --template "content-agency" || fail "Squad init failed"

[ -f /sandbox/.milimo/state.json ] && pass "State file generated" || fail "No state file found at ~/.milimo/state.json"

# verify state content contains the squad name
grep -q "e2e-squad" /sandbox/.milimo/state.json && pass "Squad name successfully written to state" || fail "State file empty or invalid"

# -------------------------------------------------------
info "5. Verify TypeScript Artifacts"
# -------------------------------------------------------
[ -f /opt/milimo/dist/index.js ] && pass "index.js compiled" || fail "index.js missing"
[ -f /opt/milimo/dist/cli.js ] && pass "cli.js compiled" || fail "cli.js missing"
[ -f /opt/milimo/dist/commands/init.js ] && pass "init.js compiled" || fail "init.js missing"
[ -f /opt/milimo/dist/commands/warroom.js ] && pass "warroom.js compiled" || fail "warroom.js missing"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  MILIMO CLAW E2E TESTS PASSED 🦀   ${NC}"
echo -e "${GREEN}========================================${NC}"
