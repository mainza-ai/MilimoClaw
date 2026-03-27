#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Setup MilimoClaw with existing OpenShell cluster
# This script configures the existing openshell-cluster-nemoclaw gateway
# and sets up inference providers for the milimo sandbox.
#
# Usage:
#   export NVIDIA_API_KEY=nvapi-...
#   ./scripts/setup-existing-cluster.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}>>>${NC} $1"; }
warn() { echo -e "${YELLOW}>>>${NC} $1"; }
fail() { echo -e "${RED}>>>${NC} $1"; exit 1; }

CLUSTER_CONTAINER="${CLUSTER_CONTAINER:-openshell-cluster-nemoclaw}"
SANDBOX_NAME="${SANDBOX_NAME:-milimo}"
NAMESPACE="${NAMESPACE:-openshell}"

# Check prerequisites
command -v docker > /dev/null || fail "docker not found"
[ -n "${NVIDIA_API_KEY:-}" ] || fail "NVIDIA_API_KEY not set. Get one from build.nvidia.com"

# Verify cluster is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CLUSTER_CONTAINER}$"; then
    fail "OpenShell cluster container '${CLUSTER_CONTAINER}' not running. Start it first."
fi

info "Using existing OpenShell cluster: ${CLUSTER_CONTAINER}"

# Helper to run kubectl in cluster
kc() {
    docker exec "${CLUSTER_CONTAINER}" kubectl "$@"
}

# Check if openshell gateway is healthy
info "Checking OpenShell gateway health..."
if ! kc get pods -n "${NAMESPACE}" | grep -q "openshell-0.*Running"; then
    fail "OpenShell gateway pod not running"
fi
info "Gateway is running"

# Check if milimo sandbox exists
info "Checking sandbox '${SANDBOX_NAME}'..."
if ! kc get sandbox "${SANDBOX_NAME}" -n "${NAMESPACE}" > /dev/null 2>&1; then
    warn "Sandbox '${SANDBOX_NAME}' not found. Will need to create it."
    SANDBOX_EXISTS=false
else
    info "Sandbox '${SANDBOX_NAME}' exists"
    SANDBOX_EXISTS=true
fi

# Get current timestamp
ONBOARD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Configure inference for the sandbox
info "Configuring NVIDIA provider in sandbox..."

if [ "$SANDBOX_EXISTS" = true ]; then
    # Create nemoclaw config directory in sandbox
    kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- mkdir -p /sandbox/.nemoclaw 2>/dev/null || true
    
    # Write onboard config using printf and base64 to avoid heredoc issues
    NEMOCLAW_CONFIG=$(cat << EOF | base64
{"endpointType":"build","endpointUrl":"https://integrate.api.nvidia.com/v1","ncpPartner":null,"model":"nvidia/nemotron-3-super-120b-a12b","profile":"default","credentialEnv":"NVIDIA_API_KEY","onboardedAt":"${ONBOARD_DATE}"}
EOF
)
    kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- sh -c "echo '${NEMOCLAW_CONFIG}' | base64 -d > /sandbox/.nemoclaw/config.json"
    
    # Verify it was written
    if kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- cat /sandbox/.nemoclaw/config.json 2>/dev/null | grep -q "endpointType"; then
        info "NemoClaw config written to sandbox"
    else
        warn "Failed to write NemoClaw config, trying direct method..."
        kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- sh -c 'printf '"'"'%s'"'"' "{\"endpointType\":\"build\",\"endpointUrl\":\"https://integrate.api.nvidia.com/v1\",\"ncpPartner\":null,\"model\":\"nvidia/nemotron-3-super-120b-a12b\",\"profile\":\"default\",\"credentialEnv\":\"NVIDIA_API_KEY\",\"onboardedAt\":\"'"${ONBOARD_DATE}"'\"}" > /sandbox/.nemoclaw/config.json'
    fi
fi

# Update the sandbox's OpenClaw config to use proper inference
info "Updating OpenClaw config in sandbox..."

if [ "$SANDBOX_EXISTS" = true ]; then
    # Backup existing config
    kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- sh -c "cp /sandbox/.openclaw/openclaw.json /sandbox/.openclaw/openclaw.json.bak.$(date +%s) 2>/dev/null || true"
    
    # Write updated config with NVIDIA provider
    OPENCLAW_CONFIG=$(cat << 'OPENCLAW_JSON' | base64
{
  "meta": {
    "lastTouchedVersion": "2026.3.11",
    "lastTouchedAt": "2026-03-19T20:30:00.000Z"
  },
  "models": {
    "mode": "merge",
    "providers": {
      "nvidia": {
        "baseUrl": "https://inference.local/v1",
        "apiKey": "openshell-managed",
        "api": "openai-completions",
        "models": [
          {
            "id": "nemotron-3-super-120b-a12b",
            "name": "NVIDIA Nemotron 3 Super 120B",
            "reasoning": false,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 131072,
            "maxTokens": 4096
          }
        ]
      }
    },
    "modelAlias": {
      "nvidia/nemotron-3-super-120b-a12b": "nvidia/nemotron-3-super-120b-a12b"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "nvidia/nemotron-3-super-120b-a12b"
      },
      "compaction": {"mode": "safeguard"}
    }
  },
  "commands": {
    "native": "auto",
    "nativeSkills": "auto",
    "restart": true,
    "ownerDisplay": "raw"
  },
  "gateway": {
    "mode": "local",
    "controlUi": {
      "allowedOrigins": ["http://127.0.0.1:18789"],
      "allowInsecureAuth": true,
      "dangerouslyDisableDeviceAuth": true
    },
    "trustedProxies": ["127.0.0.1", "::1"]
  },
  "plugins": {
    "entries": {
      "nemoclaw": {"enabled": true},
      "milimo": {"enabled": true}
    },
    "installs": {
      "nemoclaw": {
        "source": "path",
        "sourcePath": "/opt/nemoclaw",
        "installPath": "/sandbox/.openclaw/extensions/nemoclaw",
        "version": "0.1.0",
        "installedAt": "2026-03-16T23:45:32.358Z"
      }
    }
  }
}
OPENCLAW_JSON
)
    kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- sh -c "echo '${OPENCLAW_CONFIG}' | base64 -d > /sandbox/.openclaw/openclaw.json"
    
    # Verify
    if kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- cat /sandbox/.openclaw/openclaw.json 2>/dev/null | grep -q "nvidia"; then
        info "OpenClaw config updated"
    else
        warn "Config write may have failed, checking..."
        kc exec "${SANDBOX_NAME}" -n "${NAMESPACE}" -- ls -la /sandbox/.openclaw/openclaw.json
    fi
fi

# Save onboarding config on host for MilimoClaw
info "Saving onboarding config on host..."
mkdir -p ~/.nemoclaw
cat > ~/.nemoclaw/config.json << HOST_CONFIG
{
  "endpointType": "build",
  "endpointUrl": "https://integrate.api.nvidia.com/v1",
  "ncpPartner": null,
  "model": "nvidia/nemotron-3-super-120b-a12b",
  "profile": "default",
  "credentialEnv": "NVIDIA_API_KEY",
  "onboardedAt": "${ONBOARD_DATE}"
}
HOST_CONFIG

info "Setup complete!"
echo ""
echo "OpenShell cluster: ${CLUSTER_CONTAINER}"
echo "Sandbox: ${SANDBOX_NAME}"
echo ""
echo "To connect to the sandbox:"
echo "  docker exec ${CLUSTER_CONTAINER} kubectl exec -it ${SANDBOX_NAME} -n ${NAMESPACE} -- bash"
echo ""
echo "To test inference from inside the sandbox:"
echo "  openclaw agent --agent main --local -m 'hello' --session-id test"
echo ""
