#!/usr/bin/env bash
#
# deploy-to-sandbox.sh — Deploy MilimoClaw bundles into the NemoClaw sandbox
#
# Handles the entire sandbox deployment pipeline:
#   1. Detect gateway container and sandbox pod
#   2. Transfer bundles via docker cp + kubectl cp
#   3. Extract with correct ownership (already set in tar)
#   4. Register plugin via openclaw plugins install
#   5. Verify plugin loaded
#
# Usage:
#   ./scripts/deploy-to-sandbox.sh --plugin /path/to/milimo-plugin.tar.gz --blueprint /path/to/milimo-blueprint.tar.gz
#   ./scripts/deploy-to-sandbox.sh --plugin /path/to/milimo-plugin.tar.gz  # plugin only
#   ./scripts/deploy-to-sandbox.sh --blueprint /path/to/milimo-blueprint.tar.gz  # blueprint only
#   ./scripts/deploy-to-sandbox.sh --verify  # just verify current state
#
set -euo pipefail

PLUGIN_BUNDLE=""
BLUEPRINT_BUNDLE=""
VERIFY_ONLY=false
SANDBOX_NAME="my-assistant"
GATEWAY_CONTAINER=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()      { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
log_error()   { echo -e "${RED}[✗]${NC} $*"; }
log_step()    { echo -e "${BLUE}[...]${NC} $*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin) PLUGIN_BUNDLE="$2"; shift 2 ;;
    --blueprint) BLUEPRINT_BUNDLE="$2"; shift 2 ;;
    --verify) VERIFY_ONLY=true; shift ;;
    --sandbox) SANDBOX_NAME="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

detect_gateway() {
  log_step "Detecting gateway container..."
  GATEWAY_CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
  if [ -z "$GATEWAY_CONTAINER" ]; then
    log_error "No gateway container found. Is NemoClaw running?"
    log_info "Run: nemoclaw $SANDBOX_NAME status"
    return 1
  fi
  log_ok "Gateway container: $GATEWAY_CONTAINER"
}

verify_sandbox() {
  log_step "Verifying sandbox pod..."
  local pod_status
  pod_status=$(docker exec "$GATEWAY_CONTAINER" kubectl get pod "$SANDBOX_NAME" -n openshell --no-headers -o custom-columns=":status.phase" 2>/dev/null || echo "NotFound")
  if [ "$pod_status" != "Running" ]; then
    log_error "Sandbox pod '$SANDBOX_NAME' is not Running (status: $pod_status)"
    return 1
  fi
  log_ok "Sandbox pod is Running"
}

deploy_plugin() {
  local bundle="$1"
  if [ ! -f "$bundle" ]; then
    log_error "Plugin bundle not found: $bundle"
    return 1
  fi

  log_step "Deploying plugin bundle..."
  local basename
  basename=$(basename "$bundle")

  # Step 1: Copy to gateway container
  log_step "  Copying to gateway container..."
  docker cp "$bundle" "$GATEWAY_CONTAINER:/tmp/$basename" 2>/dev/null

  # Step 2: Copy to sandbox pod
  log_step "  Copying to sandbox pod..."
  docker exec "$GATEWAY_CONTAINER" kubectl cp "/tmp/$basename" "openshell/$SANDBOX_NAME:/tmp/$basename" 2>/dev/null

  # Step 3: Extract inside sandbox
  log_step "  Extracting plugin..."
  docker exec "$GATEWAY_CONTAINER" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    mkdir -p /sandbox/extensions/milimo
    tar xzf /tmp/$basename -C /sandbox/extensions/milimo --strip-components=1
    rm -f /tmp/$basename
    ls /sandbox/extensions/milimo/dist/index.js >/dev/null 2>&1 && echo 'OK' || echo 'FAIL'
  " 2>/dev/null

  # Step 4: Register plugin
  log_step "  Registering plugin..."
  docker exec "$GATEWAY_CONTAINER" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    cd /sandbox/extensions/milimo
    npm install --production 2>/dev/null || true
    openclaw plugins install /sandbox/extensions/milimo 2>&1
  " 2>/dev/null

  log_ok "Plugin deployed and registered"
}

deploy_blueprint() {
  local bundle="$1"
  if [ ! -f "$bundle" ]; then
    log_error "Blueprint bundle not found: $bundle"
    return 1
  fi

  log_step "Deploying blueprint bundle..."
  local basename
  basename=$(basename "$bundle")

  # Copy and extract
  docker cp "$bundle" "$GATEWAY_CONTAINER:/tmp/$basename" 2>/dev/null
  docker exec "$GATEWAY_CONTAINER" kubectl cp "/tmp/$basename" "openshell/$SANDBOX_NAME:/tmp/$basename" 2>/dev/null
  docker exec "$GATEWAY_CONTAINER" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    tar xzf /tmp/$basename -C /sandbox --strip-components=1
    rm -f /tmp/$basename
    echo 'OK'
  " 2>/dev/null

  log_ok "Blueprint deployed to /sandbox/milimo-blueprint"
}

verify_plugin_loaded() {
  log_step "Verifying plugin is loaded..."
  local result
  result=$(docker exec "$GATEWAY_CONTAINER" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    openclaw plugins list 2>&1 | grep -i 'milimo'
  " 2>/dev/null || true)

  if echo "$result" | grep -qi "milimo"; then
    log_ok "Milimo Claw plugin is loaded"
    return 0
  else
    log_warn "Plugin not showing as loaded yet"
    log_info "Try: nemoclaw $SANDBOX_NAME connect → openclaw plugins list"
    return 1
  fi
}

# --- Main ---

if [ "$VERIFY_ONLY" = true ]; then
  detect_gateway || exit 1
  verify_sandbox || exit 1
  verify_plugin_loaded
  exit 0
fi

if [ -z "$PLUGIN_BUNDLE" ] && [ -z "$BLUEPRINT_BUNDLE" ]; then
  echo "Usage: $0 --plugin <path> [--blueprint <path>]"
  echo "       $0 --verify"
  exit 1
fi

echo "============================================"
echo " MilimoClaw Sandbox Deployer"
echo "============================================"
echo ""

detect_gateway || exit 1
verify_sandbox || exit 1
echo ""

if [ -n "$PLUGIN_BUNDLE" ]; then
  deploy_plugin "$PLUGIN_BUNDLE"
  echo ""
fi

if [ -n "$BLUEPRINT_BUNDLE" ]; then
  deploy_blueprint "$BLUEPRINT_BUNDLE"
  echo ""
fi

verify_plugin_loaded
echo ""
echo "============================================"
echo " Deployment complete"
echo "============================================"
