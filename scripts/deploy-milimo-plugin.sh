#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Deploy Milimo Claw plugin and support files to sandbox
#
# Usage:
#   ./scripts/deploy-milimo-plugin.sh [--support-only]
#
# Options:
#   --support-only    Only deploy support files (template, blueprint), not plugin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
SUPPORT_ONLY=false
if [[ "${1:-}" == "--support-only" ]]; then
  SUPPORT_ONLY=true
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Milimo Claw Plugin Deployment Script               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check for required commands
command -v docker >/dev/null 2>&1 || {
  echo "Error: docker not found"
  exit 1
}

# Find sandbox PID
echo "▸ Finding sandbox namespace..."
PID=$(docker exec openshell-cluster-nemoclaw ps aux 2>/dev/null | grep "sleep infinity" | grep -v grep | awk '{print $1}' | head -1)

if [[ -z "$PID" ]]; then
  echo "Error: Could not find sandbox process. Is the sandbox running?"
  echo "Run: nemoclaw my-assistant connect"
  exit 1
fi

echo "  Sandbox PID: $PID"

# Build plugin if needed
if [[ "$SUPPORT_ONLY" == false ]]; then
  echo ""
  echo "▸ Building plugin..."
  cd "$PROJECT_ROOT/milimo"
  npm run build
  echo "  ✓ Build complete"
fi

# Create tarball with plugin files
if [[ "$SUPPORT_ONLY" == false ]]; then
  echo ""
  echo "▸ Creating plugin tarball..."
  cd "$PROJECT_ROOT/milimo"
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-full.tar.gz \
    --no-mac-metadata \
    dist openclaw.plugin.json package.json node_modules
  echo "  ✓ Tarball created: $(ls -lh /tmp/milimo-plugin-full.tar.gz | awk '{print $5}')"
fi

# Transfer and deploy plugin
if [[ "$SUPPORT_ONLY" == false ]]; then
  echo ""
  echo "▸ Deploying plugin to sandbox..."
  cat /tmp/milimo-plugin-full.tar.gz \
    | docker exec -i openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
      bash -c 'cat > /tmp/milimo-plugin-full.tar.gz'

  docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- bash -c '
        mkdir -p /tmp/milimo-extract && cd /tmp/milimo-extract
        tar xzf /tmp/milimo-plugin-full.tar.gz --warning=no-unknown-keyword
        mkdir -p /sandbox/extensions/milimo
        rm -rf /sandbox/extensions/milimo/*
        cp -r dist openclaw.plugin.json package.json node_modules /sandbox/extensions/milimo/
        chown -R sandbox:sandbox /sandbox/extensions/milimo
        find /sandbox/extensions/milimo -name "._*" -delete
    '
  echo "  ✓ Plugin files deployed"
fi

# Register plugin in sandbox openclaw.json
if [[ "$SUPPORT_ONLY" == false ]]; then
  echo ""
  echo "▸ Registering plugin in sandbox config..."
  docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- python3 -c "
import json

with open('/sandbox/.openclaw/openclaw.json') as f:
    config = json.load(f)

config['plugins'] = {
    'load': {
        'paths': ['/sandbox/extensions/milimo']
    },
    'entries': {
        'milimo': {
            'enabled': True
        }
    },
    'installs': {
        'milimo': {
            'source': 'path',
            'sourcePath': '/sandbox/extensions/milimo',
            'installPath': '/sandbox/extensions/milimo',
            'version': '0.1.0',
            'installedAt': '$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")'
        }
    }
}

with open('/sandbox/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print('Plugin registered in sandbox config')
"
  echo "  ✓ Plugin registered"
fi

# Deploy assistant template
echo ""
echo "▸ Deploying assistant system prompt template..."
docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
  bash -c 'mkdir -p /sandbox/.milimo'
cat "$PROJECT_ROOT/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md" \
  | docker exec -i openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
    bash -c 'cat > /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md'
docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
  chown sandbox:sandbox /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
echo "  ✓ Assistant template deployed"

# Deploy milimo-blueprint directory
echo ""
echo "▸ Deploying milimo-blueprint orchestrator scripts..."
docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
  bash -c 'mkdir -p /sandbox/milimo-blueprint/orchestrator'

# Deploy assistant_setup.py
cat "$PROJECT_ROOT/milimo-blueprint/orchestrator/assistant_setup.py" \
  | docker exec -i openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
    bash -c 'cat > /sandbox/milimo-blueprint/orchestrator/assistant_setup.py'

# Deploy solo_init.py if exists
if [[ -f "$PROJECT_ROOT/milimo-blueprint/orchestrator/solo_init.py" ]]; then
  cat "$PROJECT_ROOT/milimo-blueprint/orchestrator/solo_init.py" \
    | docker exec -i openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
      bash -c 'cat > /sandbox/milimo-blueprint/orchestrator/solo_init.py'
fi

docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
  chown -R sandbox:sandbox /sandbox/milimo-blueprint
echo "  ✓ Blueprint scripts deployed"

# Sync model config from NemoClaw to OpenClaw
echo ""
echo "▸ Syncing model config from NemoClaw to OpenClaw..."
docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- bash -c '
if [[ -f /sandbox/.nemoclaw/config.json ]]; then
    MODEL=$(python3 -c "import json; print(json.load(open(\"/sandbox/.nemoclaw/config.json\")).get(\"model\", \"nvidia/nemotron-3-super-120b-a12b\"))")
    chmod 644 /sandbox/.openclaw/openclaw.json 2>/dev/null
    sed -i "s|\"primary\": \"inference/[^\"]*\"|\"primary\": \"inference/$MODEL\"|" /sandbox/.openclaw/openclaw.json 2>/dev/null
    sed -i "s|\"id\": \"nvidia/nemotron-3-super-120b-a12b\"|\"id\": \"$MODEL\"|g" /sandbox/.openclaw/openclaw.json 2>/dev/null
    sed -i "s|\"name\": \"nvidia/nemotron-3-super-120b-a12b\"|\"name\": \"$MODEL\"|g" /sandbox/.openclaw/openclaw.json 2>/dev/null
    echo "  ✓ Model synced: $MODEL"
else
    echo "  ⚠ No NemoClaw config found, skipping model sync"
fi
'

# Verify deployment
echo ""
echo "▸ Verifying deployment..."
docker exec openshell-cluster-nemoclaw nsenter -t "$PID" -a -- \
  bash -c 'ls -la /sandbox/extensions/milimo/ 2>/dev/null | head -5' || true

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Deployment Complete                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Connect to sandbox:    nemoclaw my-assistant connect"
echo "  2. Run onboarding:        openclaw milimo onboard"
echo "  3. Start assistant:       openclaw milimo assistant start"
echo ""
echo "Note: Model config is synced from NemoClaw to OpenClaw automatically."
echo "      Gateway may need restart for model changes to take effect."
echo ""
