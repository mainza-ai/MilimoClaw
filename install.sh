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
GATEWAY_CONTAINER="${GATEWAY_CONTAINER:-openshell-cluster-nemoclaw}"

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
SOLO_MODE=true
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
    --gateway-container) GATEWAY_CONTAINER="$2"; shift 2 ;;
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
    *) error "Unknown option: $1"; exit 1 ;;
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
      local pid
      pid=$(find_sandbox_pid)
      if [ -n "$pid" ]; then
        docker exec "$gateway" nsenter -t "$pid" -a -- bash -c "
          rm -rf /sandbox/extensions/milimo
          rm -rf /sandbox/.milimo
          echo 'Milimo plugin removed'
        "
      fi
    fi
  fi

  info "Removing local MilimoClaw files..."
  rm -rf /opt/milimo
  rm -rf /opt/milimo-blueprint
  rm -rf "${HOME}/.milimo"

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
# Helper: Find sandbox PID
# ---------------------------------------------------------------------------
find_sandbox_pid() {
  local gateway="$1"
  # Find the PID of the sandbox process (sleep infinity running as sandbox user)
  # uid can be 998 or 999 depending on NemoClaw version
  docker exec "$gateway" ps aux 2>/dev/null | grep "sleep infinity" | grep -E "99[89]" | awk '{print $2}' | head -1
}

# ---------------------------------------------------------------------------
# Helper: Run command inside sandbox namespace via nsenter
# ---------------------------------------------------------------------------
sandbox_exec() {
  local gateway="$1"
  local pid="$2"
  shift 2
  docker exec -i "$gateway" nsenter -t "$pid" -a -- bash -c "$*"
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

  # Check if gateway container is running
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
# Phase 3: Build & Deploy via nsenter Pipe
# ---------------------------------------------------------------------------
deploy_to_sandbox() {
  log_step "Deploying MilimoClaw to sandbox"

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
  if [ -z "$gateway" ]; then
    error "No gateway container found. Is NemoClaw running?"
  fi
  ok "Gateway: $gateway"

  # Find sandbox PID
  local pid
  pid=$(find_sandbox_pid "$gateway")
  if [ -z "$pid" ]; then
    error "Could not find sandbox PID. Is the sandbox pod running?"
  fi
  ok "Sandbox PID: $pid"

  # ---- Step 1: Build plugin on host ----
  log_step "Building Milimo plugin"
  cd "$ROOT_DIR/milimo"
  info "Installing dependencies..."
  npm install 2>&1 | tail -5
  info "Building plugin (TypeScript)..."
  npm run build 2>&1 | tail -5
  cd "$ROOT_DIR"

  if [ ! -f "$ROOT_DIR/milimo/dist/index.js" ]; then
    error "Build failed — dist/index.js not found"
  fi
  ok "Plugin built (dist/index.js)"

  # ---- Step 2: Create plugin tar with correct flags ----
  local plugin_tar="/tmp/milimo-plugin-full.tar.gz"
  info "Creating plugin archive..."
  cd "$ROOT_DIR/milimo"
  COPYFILE_DISABLE=1 tar czf "$plugin_tar" \
    --no-mac-metadata \
    dist openclaw.plugin.json package.json node_modules
  cd "$ROOT_DIR"

  local tar_size
  tar_size=$(du -h "$plugin_tar" | cut -f1)
  ok "Plugin archive created ($tar_size)"

  # ---- Step 3: Pipe plugin into sandbox namespace ----
  info "Transferring plugin to sandbox (nsenter pipe)..."
  cat "$plugin_tar" | docker exec -i "$gateway" nsenter -t "$pid" -a -- bash -c 'cat > /tmp/milimo-plugin-full.tar.gz'

  # ---- Step 4: Extract plugin in sandbox ----
  info "Extracting plugin..."
  sandbox_exec "$gateway" "$pid" '
    mkdir -p /tmp/milimo-extract && cd /tmp/milimo-extract && \
    tar xzf /tmp/milimo-plugin-full.tar.gz --warning=no-unknown-keyword && \
    mkdir -p /sandbox/extensions/milimo && \
    rm -rf /sandbox/extensions/milimo/* && \
    cp -r dist openclaw.plugin.json package.json node_modules /sandbox/extensions/milimo/ && \
    chown -R sandbox:sandbox /sandbox/extensions/milimo && \
    find /sandbox/extensions/milimo -name "._*" -delete && \
    rm -rf /tmp/milimo-extract /tmp/milimo-plugin-full.tar.gz
  '

  if ! sandbox_exec "$gateway" "$pid" 'test -f /sandbox/extensions/milimo/dist/index.js'; then
    error "Plugin extraction failed — dist/index.js not found in sandbox"
  fi
  ok "Plugin extracted to /sandbox/extensions/milimo"

  # ---- Step 5: Deploy blueprint ----
  log_step "Deploying blueprint"
  local blueprint_tar="/tmp/milimo-blueprint.tar.gz"
  info "Creating blueprint archive..."
  cd "$ROOT_DIR"
  COPYFILE_DISABLE=1 tar czf "$blueprint_tar" \
    --no-mac-metadata \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    milimo-blueprint/
  info "Transferring blueprint to sandbox..."
  cat "$blueprint_tar" | docker exec -i "$gateway" nsenter -t "$pid" -a -- bash -c 'cat > /tmp/milimo-blueprint.tar.gz'

  sandbox_exec "$gateway" "$pid" '
    mkdir -p /sandbox/milimo-blueprint && \
    cd /tmp && \
    tar xzf /tmp/milimo-blueprint.tar.gz --warning=no-unknown-keyword && \
    cp -r milimo-blueprint/* /sandbox/milimo-blueprint/ && \
    chown -R sandbox:sandbox /sandbox/milimo-blueprint && \
    rm -rf /tmp/milimo-blueprint.tar.gz /tmp/milimo-blueprint
  '
  rm -f "$blueprint_tar"

  if ! sandbox_exec "$gateway" "$pid" 'test -d /sandbox/milimo-blueprint/orchestrator/build'; then
    error "Blueprint extraction failed — orchestrator/build/ not found"
  fi
  ok "Blueprint deployed to /sandbox/milimo-blueprint"

  # ---- Step 6: Deploy support files ----
  log_step "Deploying support files"

  # Assistant system prompt template
  local template_file="$ROOT_DIR/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"
  if [ -f "$template_file" ]; then
    info "Deploying assistant system prompt template..."
    cat "$template_file" | docker exec -i "$gateway" nsenter -t "$pid" -a -- bash -c '
      mkdir -p /sandbox/.milimo && \
      cat > /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md && \
      chown sandbox:sandbox /sandbox/.milimo/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
    '
    ok "Assistant template deployed"
  else
    warn "Assistant template not found at $template_file"
  fi

  # assistant_setup.py
  local setup_file="$ROOT_DIR/milimo-blueprint/orchestrator/assistant_setup.py"
  if [ -f "$setup_file" ]; then
    info "Deploying assistant_setup.py..."
    cat "$setup_file" | docker exec -i "$gateway" nsenter -t "$pid" -a -- bash -c '
      mkdir -p /sandbox/milimo-blueprint/orchestrator && \
      cat > /sandbox/milimo-blueprint/orchestrator/assistant_setup.py && \
      chown sandbox:sandbox /sandbox/milimo-blueprint/orchestrator/assistant_setup.py
    '
    ok "assistant_setup.py deployed"
  fi

  # ---- Step 7: Update /sandbox/.openclaw/openclaw.json ----
  log_step "Registering plugin in sandbox config"
  sandbox_exec "$gateway" "$pid" '
    python3 -c "
import json
with open(\"/sandbox/.openclaw/openclaw.json\") as f:
    config = json.load(f)

config[\"plugins\"] = {
    \"load\": {
        \"paths\": [\"/sandbox/extensions/milimo\"]
    },
    \"entries\": {
        \"milimo\": {
            \"enabled\": True
        }
    },
    \"installs\": {
        \"milimo\": {
            \"source\": \"path\",
            \"sourcePath\": \"/sandbox/extensions/milimo\",
            \"installPath\": \"/sandbox/extensions/milimo\",
            \"version\": \"${MILIMO_VERSION}\",
            \"installedAt\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\"
        }
    }
}

with open(\"/sandbox/.openclaw/openclaw.json\", \"w\") as f:
    json.dump(config, f, indent=2)
    f.write(\"\\n\")

print(\"Sandbox config updated successfully\")
"
  '
  ok "Plugin registered in /sandbox/.openclaw/openclaw.json"

  # ---- Step 8: Restart gateway to load plugin ----
  log_step "Restarting OpenClaw gateway"
  sandbox_exec "$gateway" "$pid" '
    # Kill openclaw process — it auto-restarts
    pkill -f "openclaw" 2>/dev/null || true
    echo "Gateway restart initiated"
  '
  info "Waiting for gateway to restart..."
  sleep 8
  ok "Gateway restarted"
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

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
  local pid
  pid=$(find_sandbox_pid "$gateway")

  # Write config directly to sandbox — BOTH paths:
  # /root/.milimo/config.json  — where the plugin reads (runs as root, HOME=/root)
  # /sandbox/.milimo/config.json — where Python orchestrator reads
  sandbox_exec "$gateway" "$pid" "
    mkdir -p /root/.milimo /sandbox/.milimo
    python3 -c \"
import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

# Plugin ConfigManager format (flat fields — what the TypeScript plugin reads)
plugin_config = {
    'squadName': '${squad}',
    'clawRole': '',
    'template': 'solo',
    'solo': True,
    'operatorName': '${operator}',
    'warRoomMode': '${WARROOM_MODE}',
    'onboardedAt': now,
    'activeClaws': ['content', 'ops', 'analytics', 'finance', 'build']
}

# Orchestrator format (nested — for Python code and human readability)
orchestrator_config = {
    'version': '${MILIMO_VERSION}',
    'squad': {
        'name': '${squad}',
        'template': 'solo',
        'mode': 'solo',
        'onboarded_at': now
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
        'vibe': 'sharp and unhurled',
        'emoji': '🦀'
    },
    'activeClaws': ['content', 'ops', 'analytics', 'finance', 'build']
}

# Write plugin config to /root/.milimo (where plugin reads as root)
with open('/root/.milimo/config.json', 'w') as f:
    json.dump(plugin_config, f, indent=2)

# Write orchestrator config to /sandbox/.milimo (for Python code)
with open('/sandbox/.milimo/config.json', 'w') as f:
    json.dump(orchestrator_config, f, indent=2)

print('Both configs written')
\"
    chown -R sandbox:sandbox /sandbox/.milimo
    chown -R root:root /root/.milimo
  "

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
  local pid
  pid=$(find_sandbox_pid "$gateway")

  # Check plugin loaded — run actual command
  local plugin_check
  plugin_check=$(sandbox_exec "$gateway" "$pid" '
    echo "=== Plugin List ==="
    openclaw plugins list 2>&1
    echo "=== Milimo Command Test ==="
    openclaw milimo --help 2>&1 || echo "MILIMO_COMMAND_NOT_FOUND"
  ') || true

  if echo "$plugin_check" | grep -qi "milimo.*loaded\|Milimo Claw\|registered"; then
    ok "Milimo Claw plugin is loaded"
  elif echo "$plugin_check" | grep -qi "MILIMO_COMMAND_NOT_FOUND\|unknown command"; then
    error "Milimo Claw plugin is NOT loaded. Debug output:
$plugin_check

To fix manually:
  1. nemoclaw $SANDBOX_NAME connect
  2. cd /sandbox/extensions/milimo && npm install && npx tsc
  3. openclaw plugins install /sandbox/extensions/milimo
  4. pkill -f openclaw (gateway auto-restarts)"
  else
    warn "Plugin status unclear. Full output:
$plugin_check"
  fi

  # Check Build Claw modules
  local build_check
  build_check=$(sandbox_exec "$gateway" "$pid" '
    ls /sandbox/milimo-blueprint/orchestrator/build/build_claw.py 2>/dev/null && echo "OK" || echo "MISSING"
  ')

  if [ "$build_check" = "OK" ]; then
    local module_count
    module_count=$(sandbox_exec "$gateway" "$pid" 'ls /sandbox/milimo-blueprint/orchestrator/build/*.py 2>/dev/null | grep -v __init__ | wc -l')
    ok "Build Claw present ($module_count modules)"
  else
    warn "Build Claw blueprint not found"
  fi

  # Check config
  local config_check
  config_check=$(sandbox_exec "$gateway" "$pid" '
    cat /sandbox/.milimo/config.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"squad\",{}).get(\"name\",\"?\"))" 2>/dev/null || echo "MISSING"
  ')

  if [ "$config_check" != "MISSING" ] && [ "$config_check" != "ERROR" ]; then
    ok "Milimo config: squad=$config_check"
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
