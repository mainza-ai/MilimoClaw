#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# MilimoClaw One-Command Installer
#
# Handles everything: prerequisites, NemoClaw bootstrap, MilimoClaw deployment,
# and onboarding. Single command, zero manual steps.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/mainza-ai/MilimoClaw/main/install.sh | bash
#   # or locally:
#   ./install.sh
#   ./install.sh --solo --operator-name "YourName" --squad-name "my-squad"
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MILIMO_VERSION="2.0.0"
NODE_MIN_VERSION="22"
PYTHON_MIN_VERSION="3.12"
SANDBOX_NAME="${MILIMO_SANDBOX_NAME:-my-assistant}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
BUNDLE_DIR="$ROOT_DIR/dist-bundle"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
if [[ -z "${NO_COLOR:-}" && -t 1 ]]; then
  C_GREEN=$'\033[38;5;148m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RED=$'\033[1;31m'
  C_YELLOW=$'\033[1;33m'
  C_CYAN=$'\033[1;36m'
  C_RESET=$'\033[0m'
else
  C_GREEN='' C_BOLD='' C_DIM='' C_RED='' C_YELLOW='' C_CYAN='' C_RESET=''
fi

info()    { printf "${C_CYAN}[INFO]${C_RESET}  %s\n" "$*"; }
warn()    { printf "${C_YELLOW}[WARN]${C_RESET}  %s\n" "$*"; }
error()   { printf "${C_RED}[ERROR]${C_RESET} %s\n" "$*" >&2; }
ok()      { printf "  ${C_GREEN}✓${C_RESET}  %s\n" "$*"; }
skip()    { printf "  ${C_DIM}⊘${C_RESET}  %s\n" "$*"; }
log_step() { printf "\n${C_GREEN}${C_BOLD}>>> %s${C_RESET}\n" "$*"; }

command_exists() { command -v "$1" &>/dev/null; }

version_gte() {
  local IFS=.
  local -a a=($1) b=($2)
  for i in 0 1 2; do
    local ai=${a[$i]:-0} bi=${b[$i]:-0}
    if ((ai > bi)); then return 0; fi
    if ((ai < bi)); then return 1; fi
  done
  return 0
}

# ---------------------------------------------------------------------------
# CLI Arguments
# ---------------------------------------------------------------------------
NON_INTERACTIVE=false
SOLO_MODE=true  # Default: solo mode (all 5 claws)
OPERATOR_NAME=""
SQUAD_NAME=""
WARROOM_MODE="minimal"
AUTO_INSTALL=false
UNINSTALL=false
DRY_RUN=false
SKIP_NEMOCLAW=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive) NON_INTERACTIVE=true; shift ;;
    --solo) SOLO_MODE=true; shift ;;
    --operator-name) OPERATOR_NAME="$2"; shift 2 ;;
    --squad-name) SQUAD_NAME="$2"; shift 2 ;;
    --warroom-mode) WARROOM_MODE="$2"; shift 2 ;;
    --auto) AUTO_INSTALL=true; shift ;;
    --uninstall) UNINSTALL=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --skip-nemoclaw) SKIP_NEMOCLAW=true; shift ;;
    --sandbox-name) SANDBOX_NAME="$2"; shift 2 ;;
    --version|-v)
      printf "milimo-claw-installer v%s\n" "$MILIMO_VERSION"
      exit 0
      ;;
    --help|-h)
      printf "\n  ${C_BOLD}MilimoClaw Installer${C_RESET}  ${C_DIM}v%s${C_RESET}\n\n" "$MILIMO_VERSION"
      printf "  ${C_DIM}Usage:${C_RESET}\n"
      printf "    curl -fsSL https://raw.githubusercontent.com/mainza-ai/MilimoClaw/main/install.sh | bash\n"
      printf "    ./install.sh [options]\n\n"
      printf "  ${C_DIM}Options:${C_RESET}\n"
      printf "    --solo                  Solo mode (all 5 claws active) [default]\n"
      printf "    --operator-name <name>  Operator name (default: \$USER)\n"
      printf "    --squad-name <name>     Squad name (default: milimo-squad)\n"
      printf "    --warroom-mode <mode>   War Room mode: full|minimal|disabled\n"
      printf "    --non-interactive       Skip all prompts, use defaults\n"
      printf "    --auto                  Auto-install missing dependencies\n"
      printf "    --skip-nemoclaw         Skip NemoClaw bootstrap\n"
      printf "    --dry-run               Show what would be done without doing it\n"
      printf "    --uninstall             Remove MilimoClaw, keep NemoClaw\n"
      printf "    --version, -v           Print version and exit\n"
      printf "    --help                  Show this help message\n\n"
      printf "  ${C_DIM}Environment:${C_RESET}\n"
      printf "    NVIDIA_API_KEY          API key for NVIDIA inference\n"
      printf "    MILIMO_SANDBOX_NAME     Sandbox pod name (default: my-assistant)\n"
      printf "\n"
      exit 0
      ;;
    *) error "Unknown option: $1" ;;
  esac
done

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------
do_uninstall() {
  log_step "Uninstalling MilimoClaw"

  info "Removing MilimoClaw plugin from sandbox..."
  if command_exists docker; then
    local gateway
    gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
    if [ -n "$gateway" ]; then
      docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
        openclaw plugins uninstall milimo 2>/dev/null || true
        rm -rf /sandbox/extensions/milimo
        rm -rf /sandbox/.milimo
        echo 'Milimo plugin removed'
      " 2>/dev/null || warn "Could not remove plugin from sandbox"
    fi
  fi

  info "Removing local MilimoClaw files..."
  rm -rf /opt/milimo
  rm -rf /opt/milimo-blueprint
  rm -rf "${HOME}/.milimo"
  rm -rf "$BUNDLE_DIR"

  ok "MilimoClaw uninstalled. NemoClaw sandbox is preserved."
  exit 0
}

if [ "$UNINSTALL" = true ]; then
  do_uninstall
fi

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
print_banner() {
  printf "\n"
  printf "  ${C_GREEN}${C_BOLD} ███╗   ███╗███████╗███╗   ███╗ ██████╗  ██████╗${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD} ████╗ ████║██╔════╝████╗ ████║██╔═══██╗██╔════╝${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD} ██╔████╔██║█████╗  ██╔████╔██║██║   ██║██║     ${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD} ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║   ██║██║     ${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD} ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╗${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD} ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝${C_RESET}\n"
  printf "\n"
  printf "  ${C_DIM}Multi-agent autonomous hustle platform — v%s${C_RESET}\n" "$MILIMO_VERSION"
  printf "  ${C_DIM}Built on NVIDIA NemoClaw + OpenShell${C_RESET}\n"
  printf "\n"
}

# ---------------------------------------------------------------------------
# Phase 1: Prerequisites
# ---------------------------------------------------------------------------
check_prerequisites() {
  log_step "Checking prerequisites"

  # Docker
  if ! command_exists docker; then
    if [ "$AUTO_INSTALL" = true ]; then
      info "Installing Docker..."
      if [[ "$OSTYPE" == "darwin"* ]]; then
        warn "Docker Desktop for Mac must be installed manually."
        warn "Download from: https://docs.docker.com/desktop/install/mac-install/"
        return 1
      elif command_exists apt-get; then
        curl -fsSL https://get.docker.com | sh
      else
        warn "Cannot auto-install Docker on this system."
        return 1
      fi
    else
      error "Docker is not installed. Required for sandbox runtime.
  Install from: https://docs.docker.com/get-docker/"
    fi
  fi

  if ! docker info &>/dev/null; then
    error "Docker is not running. Please start Docker and try again."
  fi
  ok "Docker is running"

  # Node.js
  if ! command_exists node; then
    if [ "$AUTO_INSTALL" = true ]; then
      info "Installing Node.js..."
      if [[ "$OSTYPE" == "darwin"* ]] && command_exists brew; then
        brew install node
      elif command_exists apt-get; then
        curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
        apt-get install -y nodejs
      fi
    else
      error "Node.js >= ${NODE_MIN_VERSION} is not installed.
  Install from: https://nodejs.org/"
    fi
  fi

  local node_version
  node_version=$(node --version | sed 's/^v//')
  local node_major
  node_major=$(echo "$node_version" | cut -d. -f1)
  if ((node_major < NODE_MIN_VERSION)); then
    error "Node.js $node_version is too old. MilimoClaw requires Node.js >= ${NODE_MIN_VERSION}."
  fi
  ok "Node.js $node_version"

  # npm
  if ! command_exists npm; then
    error "npm is not installed."
  fi
  ok "npm $(npm --version)"

  # Python
  if ! command_exists python3; then
    warn "Python 3 is not installed. Required for blueprint orchestrator."
  else
    local py_version
    py_version=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $py_version"
  fi

  # NVIDIA API Key
  if [ -z "${NVIDIA_API_KEY:-}" ]; then
    warn "NVIDIA_API_KEY environment variable is not set."
    warn "Get one at: https://build.nvidia.com/"
    warn "Export it: export NVIDIA_API_KEY=nvapi-..."
    if [ "$NON_INTERACTIVE" = false ]; then
      read -rp "Continue anyway? (y/N) " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
      fi
    fi
  else
    ok "NVIDIA API key configured"
  fi
}

# ---------------------------------------------------------------------------
# Phase 2: NemoClaw Bootstrap
# ---------------------------------------------------------------------------
bootstrap_nemoclaw() {
  if [ "$SKIP_NEMOCLAW" = true ]; then
    skip "NemoClaw bootstrap (skipped)"
    return 0
  fi

  log_step "Checking NemoClaw"

  # Check if sandbox is already running
  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  if [ -n "$gateway" ]; then
    local pod_status
    pod_status=$(docker exec "$gateway" kubectl get pod "$SANDBOX_NAME" -n openshell --no-headers -o custom-columns=":status.phase" 2>/dev/null || echo "NotFound")
    if [ "$pod_status" = "Running" ]; then
      skip "NemoClaw sandbox '$SANDBOX_NAME' already running"
      return 0
    fi
  fi

  # Check if nemoclaw CLI exists
  if command_exists nemoclaw; then
    ok "NemoClaw CLI found ($(nemoclaw --version 2>/dev/null || echo 'installed'))"
    info "Starting sandbox..."
    nemoclaw "$SANDBOX_NAME" start 2>/dev/null || true
    # Wait for sandbox
    local retries=30
    while ((retries > 0)); do
      pod_status=$(docker exec "$gateway" kubectl get pod "$SANDBOX_NAME" -n openshell --no-headers -o custom-columns=":status.phase" 2>/dev/null || echo "NotFound")
      if [ "$pod_status" = "Running" ]; then
        ok "Sandbox '$SANDBOX_NAME' is Running"
        return 0
      fi
      retries=$((retries - 1))
      sleep 2
    done
    warn "Sandbox did not reach Running state in 60s. Continuing anyway..."
    return 0
  fi

  # NemoClaw not installed — clone and install
  warn "NemoClaw is not installed."
  if [ "$AUTO_INSTALL" = true ] || [ "$NON_INTERACTIVE" = true ]; then
    info "Cloning NemoClaw..."
    local tmp_dir
    tmp_dir=$(mktemp -d)
    git clone --depth 1 https://github.com/NVIDIA/NemoClaw.git "$tmp_dir/NemoClaw" 2>/dev/null
    cd "$tmp_dir/NemoClaw"
    info "Running NemoClaw installer..."
    NEMOCLAW_NON_INTERACTIVE=1 NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1 bash install.sh --non-interactive --yes-i-accept-third-party-software 2>&1 | tail -20
    cd "$ROOT_DIR"
    rm -rf "$tmp_dir"
    ok "NemoClaw installed"
  else
    warn "Install NemoClaw first:"
    warn "  curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash"
    warn "Then re-run this installer."
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# Phase 3: Build & Deploy Bundles
# ---------------------------------------------------------------------------
deploy_to_sandbox() {
  log_step "Deploying MilimoClaw to sandbox"

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
  if [ -z "$gateway" ]; then
    error "No gateway container found. Is NemoClaw running?"
  fi

  # Build bundles if they don't exist
  if [ ! -f "$BUNDLE_DIR/milimo-plugin-v${MILIMO_VERSION}.tar.gz" ]; then
    info "Building plugin bundle..."
    if [ -x "$SCRIPT_DIR/scripts/build-bundle.sh" ]; then
      bash "$SCRIPT_DIR/scripts/build-bundle.sh" --version "$MILIMO_VERSION"
    else
      # Fallback: build inline
      cd "$ROOT_DIR/milimo"
      npm install --production --ignore-scripts 2>&1 | tail -3
      npm run build 2>&1 | tail -3
      cd "$ROOT_DIR"

      mkdir -p "$BUNDLE_DIR/milimo"
      cp -r "$ROOT_DIR/milimo/dist" "$BUNDLE_DIR/milimo/"
      cp -r "$ROOT_DIR/milimo/node_modules" "$BUNDLE_DIR/milimo/"
      cp "$ROOT_DIR/milimo/openclaw.plugin.json" "$BUNDLE_DIR/milimo/"
      cp "$ROOT_DIR/milimo/package.json" "$BUNDLE_DIR/milimo/"
      echo "$MILIMO_VERSION" > "$BUNDLE_DIR/milimo/VERSION"

      cd "$BUNDLE_DIR"
      tar --owner=sandbox --group=sandbox -czf "milimo-plugin-v${MILIMO_VERSION}.tar.gz" milimo/
      cd "$ROOT_DIR"
    fi
  fi
  ok "Plugin bundle ready"

  if [ ! -f "$BUNDLE_DIR/milimo-blueprint-v${MILIMO_VERSION}.tar.gz" ]; then
    info "Building blueprint bundle..."
    if [ -x "$SCRIPT_DIR/scripts/build-blueprint-bundle.sh" ]; then
      bash "$SCRIPT_DIR/scripts/build-blueprint-bundle.sh" --version "$MILIMO_VERSION"
    else
      mkdir -p "$BUNDLE_DIR"
      cd "$ROOT_DIR"
      tar --owner=sandbox --group=sandbox \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
        --exclude='tests/' --exclude='test_*.py' \
        -czf "$BUNDLE_DIR/milimo-blueprint-v${MILIMO_VERSION}.tar.gz" \
        milimo-blueprint/
    fi
  fi
  ok "Blueprint bundle ready"

  # Deploy via docker cp + kubectl cp
  local plugin_bundle="$BUNDLE_DIR/milimo-plugin-v${MILIMO_VERSION}.tar.gz"
  local blueprint_bundle="$BUNDLE_DIR/milimo-blueprint-v${MILIMO_VERSION}.tar.gz"

  # Deploy plugin
  info "Transferring plugin to sandbox..."
  if ! docker cp "$plugin_bundle" "$gateway:/tmp/milimo-plugin.tar.gz"; then
    error "Failed to copy plugin bundle to gateway container"
  fi
  if ! docker exec "$gateway" kubectl cp "/tmp/milimo-plugin.tar.gz" "openshell/$SANDBOX_NAME:/tmp/milimo-plugin.tar.gz"; then
    error "Failed to copy plugin bundle to sandbox pod"
  fi

  info "Extracting and registering plugin..."
  local extract_output
  extract_output=$(docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    # Remove any previous installation
    rm -rf /root/.openclaw/extensions/milimo
    rm -rf /sandbox/extensions/milimo

    # Extract to sandbox extensions dir
    mkdir -p /sandbox/extensions/milimo
    tar xzf /tmp/milimo-plugin.tar.gz -C /sandbox/extensions/milimo --strip-components=1
    rm -f /tmp/milimo-plugin.tar.gz

    # Verify dist/index.js exists
    if [ ! -f /sandbox/extensions/milimo/dist/index.js ]; then
      echo 'ERROR: dist/index.js not found after extraction'
      ls -la /sandbox/extensions/milimo/ 2>/dev/null || echo 'Directory empty'
      exit 1
    fi
    echo 'OK: dist/index.js present'

    # Install production dependencies
    cd /sandbox/extensions/milimo
    npm install --production 2>&1 | tail -5

    # Register the plugin
    echo '---PLUGIN_INSTALL_OUTPUT---'
    openclaw plugins install /sandbox/extensions/milimo 2>&1
    echo '---END_PLUGIN_INSTALL---'

    # Verify plugin is registered
    openclaw plugins list 2>&1
  " 2>&1) || {
    error "Plugin extraction/registration failed:
$extract_output"
  }

  # Check for errors in output
  if echo "$extract_output" | grep -q "ERROR:"; then
    error "Plugin deployment error:
$(echo "$extract_output" | grep 'ERROR:')"
  fi

  ok "Plugin deployed"

  # Deploy blueprint
  info "Transferring blueprint to sandbox..."
  if ! docker cp "$blueprint_bundle" "$gateway:/tmp/milimo-blueprint.tar.gz"; then
    error "Failed to copy blueprint bundle to gateway container"
  fi
  if ! docker exec "$gateway" kubectl cp "/tmp/milimo-blueprint.tar.gz" "openshell/$SANDBOX_NAME:/tmp/milimo-blueprint.tar.gz"; then
    error "Failed to copy blueprint bundle to sandbox pod"
  fi

  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    tar xzf /tmp/milimo-blueprint.tar.gz -C /sandbox --strip-components=1
    rm -f /tmp/milimo-blueprint.tar.gz
    echo 'Blueprint extracted'
  " 2>&1 || warn "Blueprint extraction had warnings (continuing)"
  ok "Blueprint deployed"
}

# ---------------------------------------------------------------------------
# Phase 4: Non-Interactive Onboarding
# ---------------------------------------------------------------------------
run_onboarding() {
  log_step "Configuring MilimoClaw"

  local operator="${OPERATOR_NAME:-${USER:-operator}}"
  local squad="${SQUAD_NAME:-milimo-squad}"

  if [ "$DRY_RUN" = true ]; then
    info "Dry run — would configure:"
    info "  Squad: $squad (solo template, all 5 claws)"
    info "  Operator: $operator"
    info "  War Room: $WARROOM_MODE"
    return 0
  fi

  # Write config directly to sandbox
  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    mkdir -p /sandbox/.milimo
    python3 -c \"
import json
from datetime import datetime, timezone

config = {
    'version': '${MILIMO_VERSION}',
    'squad': {
        'name': '${squad}',
        'template': 'solo',
        'mode': 'solo',
        'onboarded_at': datetime.now(timezone.utc).isoformat()
    },
    'operator': {
        'name': '${operator}'
    },
    'claws': {
        'content': { 'enabled': True, 'mount': '/sandbox/content' },
        'ops': { 'enabled': True, 'mount': '/sandbox/clients' },
        'analytics': { 'enabled': True, 'mount': '/sandbox/analytics' },
        'finance': { 'enabled': True, 'mount': '/sandbox/finance' },
        'build': { 'enabled': True, 'mount': '/sandbox/build' }
    },
    'war_room': {
        'mode': '${WARROOM_MODE}'
    },
    'mesh': {
        'enabled': False,
        'secret': None
    },
    'inference': {
        'provider': 'nvidia-prod',
        'model': 'nvidia/nemotron-3-super-120b-a12b',
        'baseUrl': 'https://integrate.api.nvidia.com/v1',
        'api': 'openai-responses'
    },
    'blueprint_dir': '/sandbox/milimo-blueprint',
    'assistant': {
        'name': 'Nova',
        'creature': 'a claw',
        'vibe': 'sharp and unhurried',
        'emoji': '🦀'
    },
    'activeClaws': ['content', 'ops', 'analytics', 'finance', 'build']
}

with open('/sandbox/.milimo/config.json', 'w') as f:
    json.dump(config, f, indent=2)
print('Config written')
\"
    chown -R sandbox:sandbox /sandbox/.milimo
  " 2>&1 || warn "Config write had warnings"

  ok "Squad: $squad (solo template)"
  ok "Operator: $operator"
  ok "Claws: Content, Ops, Analytics, Finance, Build — all enabled"
  ok "War Room: $WARROOM_MODE"
}

# ---------------------------------------------------------------------------
# Phase 5: Verification
# ---------------------------------------------------------------------------
verify_installation() {
  log_step "Verifying installation"

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  # Check plugin loaded — run actual command, not just grep
  local plugin_check
  plugin_check=$(docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    echo '=== Plugin List ==='
    openclaw plugins list 2>&1
    echo '=== Milimo Command Test ==='
    openclaw milimo --help 2>&1 || echo 'MILIMO_COMMAND_NOT_FOUND'
  " 2>&1) || true

  if echo "$plugin_check" | grep -qi "milimo.*loaded\|milimo.*plugin"; then
    ok "Milimo Claw plugin is loaded"
  elif echo "$plugin_check" | grep -qi "MILIMO_COMMAND_NOT_FOUND\|unknown command"; then
    error "Milimo Claw plugin is NOT loaded. Debug output:
$plugin_check

To fix manually:
  1. nemoclaw $SANDBOX_NAME connect
  2. openclaw plugins install /sandbox/extensions/milimo
  3. Check for errors in the output"
  else
    warn "Plugin status unclear. Full output:
$plugin_check"
  fi

  # Check blueprint
  local blueprint_check
  blueprint_check=$(docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    ls /sandbox/milimo-blueprint/orchestrator/build/build_claw.py 2>/dev/null && echo 'OK' || echo 'MISSING'
  " 2>&1)

  if [ "$blueprint_check" = "OK" ]; then
    ok "Build Claw blueprint present"
  else
    warn "Build Claw blueprint not found"
  fi

  # Check config
  local config_check
  config_check=$(docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    cat /sandbox/.milimo/config.json 2>/dev/null | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('squad',{}).get('name','?'))\" 2>/dev/null || echo 'MISSING'
  " 2>&1)

  if [ "$config_check" != "MISSING" ] && [ "$config_check" != "ERROR" ]; then
    ok "Milimo config: $config_check"
  else
    warn "Milimo config not found"
  fi
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_summary() {
  local operator="${OPERATOR_NAME:-${USER:-operator}}"
  local squad="${SQUAD_NAME:-milimo-squad}"
  local elapsed=$((SECONDS - _INSTALL_START))

  echo ""
  printf "  ${C_GREEN}${C_BOLD}──────────────────────────────────────────────────────${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD}  MilimoClaw v%s — Installation Complete${C_RESET}\n" "$MILIMO_VERSION"
  printf "  ${C_GREEN}${C_BOLD}──────────────────────────────────────────────────────${C_RESET}\n"
  echo ""
  echo "  Squad:      $squad (solo — all 5 claws active)"
  echo "  Operator:   $operator"
  echo "  Claws:      Content · Ops · Analytics · Finance · Build"
  echo "  War Room:   $WARROOM_MODE"
  echo "  Elapsed:    ${elapsed}s"
  echo ""
  echo "  Next steps:"
  echo "    Launch War Room:  nemoclaw $SANDBOX_NAME connect → openclaw milimo warroom"
  echo "    Check status:     openclaw milimo health"
  echo "    Talk to assistant: openclaw tui"
  echo ""
  printf "  ${C_GREEN}${C_BOLD}──────────────────────────────────────────────────────${C_RESET}\n"
  echo ""
  ok "The milimo never stops. Work. Without working."
  echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  _INSTALL_START=$SECONDS
  print_banner
  check_prerequisites
  bootstrap_nemoclaw
  deploy_to_sandbox
  run_onboarding
  verify_installation
  print_summary
}

main "$@"
