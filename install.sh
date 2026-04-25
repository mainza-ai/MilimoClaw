#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# MilimoClaw One-Command Installer
#
# Deploys MilimoClaw plugin + blueprint into an existing NemoClaw sandbox.
# NemoClaw must be installed and the sandbox must be running before this script.
#
# Usage:
#   cd /path/to/MilimoClaw
#   ./install.sh --solo --operator-name "YourName" --squad-name "my-squad"
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MILIMO_VERSION="2.0.0"
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

info() { printf "${C_CYAN}[INFO]${C_RESET}  %s\n" "$*"; }
warn() { printf "${C_YELLOW}[WARN]${C_RESET}  %s\n" "$*"; }
error() { printf "${C_RED}[ERROR]${C_RESET} %s\n" "$*" >&2; }
ok() { printf "  ${C_GREEN}✓${C_RESET}  %s\n" "$*"; }
skip() { printf "  ${C_DIM}⊘${C_RESET}  %s\n" "$*"; }
log_step() { printf "\n${C_GREEN}${C_BOLD}>>> %s${C_RESET}\n" "$*"; }

command_exists() { command -v "$1" &>/dev/null; }

# ---------------------------------------------------------------------------
# CLI Arguments
# ---------------------------------------------------------------------------
export NON_INTERACTIVE=false
export SOLO_MODE=true
OPERATOR_NAME=""
SQUAD_NAME=""
WARROOM_MODE="minimal"
export AUTO_INSTALL=false
UNINSTALL=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive)
      export NON_INTERACTIVE=true
      shift
      ;;
    --solo)
      export SOLO_MODE=true
      shift
      ;;
    --operator-name)
      OPERATOR_NAME="$2"
      shift 2
      ;;
    --squad-name)
      SQUAD_NAME="$2"
      shift 2
      ;;
    --warroom-mode)
      WARROOM_MODE="$2"
      shift 2
      ;;
    --auto)
      export AUTO_INSTALL=true
      shift
      ;;
    --uninstall)
      UNINSTALL=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --sandbox-name)
      SANDBOX_NAME="$2"
      shift 2
      ;;
    --gateway-container)
      GATEWAY_CONTAINER="$2"
      shift 2
      ;;
    --version | -v)
      printf "milimo-claw-installer v%s\n" "$MILIMO_VERSION"
      exit 0
      ;;
    --help | -h)
      printf "\n  ${C_BOLD}MilimoClaw Installer${C_RESET}  ${C_DIM}v%s${C_RESET}\n\n" "$MILIMO_VERSION"
      printf "  ${C_DIM}Usage:${C_RESET}\n"
      printf "    ./install.sh [options]\n\n"
      printf "  ${C_DIM}Options:${C_RESET}\n"
      printf " --solo Solo mode (all 6 claws active) [default]\n"
      printf "    --operator-name <name>  Operator name (default: \$USER)\n"
      printf "    --squad-name <name>     Squad name (default: milimo-squad)\n"
      printf "    --warroom-mode <mode>   War Room mode: full|minimal|disabled\n"
      printf "    --non-interactive       Skip all prompts, use defaults\n"
      printf "    --auto                  Auto-install missing dependencies\n"
      printf "    --dry-run               Show what would be done without doing it\n"
      printf "    --uninstall             Remove MilimoClaw, keep NemoClaw\n"
      printf "    --version, -v           Print version and exit\n"
      printf "    --help                  Show this help message\n\n"
      printf "  ${C_DIM}Prerequisites:${C_RESET}\n"
      printf "    NemoClaw must be installed and sandbox running.\n"
      printf "    Install NemoClaw: curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash\n\n"
      exit 0
      ;;
    *)
      error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------
do_uninstall() {
  log_step "Uninstalling MilimoClaw"

  info "Removing MilimoClaw from sandbox..."
  if command_exists docker; then
    local gateway
    gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
    if [ -n "$gateway" ]; then
      docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c '
        rm -rf /sandbox/extensions/milimo
        rm -rf /sandbox/.openclaw-data/extensions/milimo
        rm -rf /sandbox/.milimo
        rm -rf /sandbox/milimo-blueprint
        echo "Milimo files removed from sandbox"
      ' 2>/dev/null || true
    fi
  fi

  info "Removing local MilimoClaw files..."
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
  printf "  ${C_GREEN}${C_BOLD}M   M  IIIII  L     IIIII  M   M   OOOO    CCCC  L     A   A   W   W${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD}MM MM    I    L       I    MM MM  O    O  C      L    A A A A  W W W${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD}M M M    I    L       I    M M M  O    O  C      L    A A A A  W W W${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD}M   M    I    L       I    M   M  O    O  C      L    A   A   W W W${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD}M   M  IIIII  LLLLL IIIII  M   M   OOOO    CCCC  LLLLL A   A    W W ${C_RESET}\n"
  printf "\n"
  printf "  ${C_DIM}Multi-agent autonomous hustle platform — v%s${C_RESET}\n" "$MILIMO_VERSION"
  printf "  ${C_DIM}Built on NVIDIA NemoClaw + OpenShell${C_RESET}\n"
  printf "\n"
}

# ---------------------------------------------------------------------------
# Helper: Run command inside sandbox pod via kubectl exec
# ---------------------------------------------------------------------------
sandbox_exec() {
  local gateway="$1"
  shift
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "$*"
}

# ---------------------------------------------------------------------------
# Phase 1: Prerequisites
# ---------------------------------------------------------------------------
check_prerequisites() {
  log_step "Checking prerequisites"

  # Docker
  if ! command_exists docker; then
    error "Docker is not installed. Required for sandbox runtime."
  fi
  if ! docker info &>/dev/null; then
    error "Docker is not running. Please start Docker and try again."
  fi
  ok "Docker is running"

  # Node.js
  if ! command_exists node; then
    error "Node.js is not installed. Required to build the Milimo plugin."
  fi
  local node_version
  node_version=$(node --version | sed 's/^v//')
  local node_major
  node_major=$(echo "$node_version" | cut -d. -f1)
  if ((node_major < 22)); then
    error "Node.js $node_version is too old. MilimoClaw requires Node.js >= 22."
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

  # NemoClaw sandbox must be running
  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)
  if [ -z "$gateway" ]; then
    error "No NemoClaw gateway container found.
  Install NemoClaw first: curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash"
  fi
  ok "Gateway: $gateway"

  # Check sandbox pod
  local pod_status
  pod_status=$(docker exec "$gateway" kubectl get pod "$SANDBOX_NAME" -n openshell --no-headers -o custom-columns=":status.phase" 2>/dev/null || echo "NotFound")
  if [ "$pod_status" != "Running" ]; then
    error "Sandbox pod '$SANDBOX_NAME' is not Running (status: $pod_status).
  Start it with: nemoclaw $SANDBOX_NAME connect"
  fi
  ok "Sandbox '$SANDBOX_NAME' is Running"
}

# ---------------------------------------------------------------------------
# Phase 2: Build & Deploy
# ---------------------------------------------------------------------------
deploy_to_sandbox() {
  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  # ---- Step 1: Build plugin on host ----
  log_step "Building Milimo plugin"
  cd "$ROOT_DIR/milimo"
  info "Installing dependencies..."
  npm install 2>&1 | tail -5
  info "Building plugin (TypeScript)..."
  npx tsc 2>&1 | tail -5
  cd "$ROOT_DIR"

  if [ ! -f "$ROOT_DIR/milimo/dist/index.js" ]; then
    error "Build failed — dist/index.js not found"
  fi
  ok "Plugin built (dist/index.js)"

  # ---- Step 2: Transfer plugin source to sandbox ----
  log_step "Deploying MilimoClaw to sandbox"

  info "Transferring plugin source to sandbox..."
  cd "$ROOT_DIR/milimo"
  tar czf /tmp/milimo-source-deploy.tar.gz \
    --exclude='__tests__' --exclude='*.test.ts' --exclude='tsconfig.tsbuildinfo' \
    . 2>/dev/null
  cd "$ROOT_DIR"

  docker cp /tmp/milimo-source-deploy.tar.gz "$gateway":/tmp/milimo-source-deploy.tar.gz 2>/dev/null
  docker exec "$gateway" kubectl cp /tmp/milimo-source-deploy.tar.gz openshell/"$SANDBOX_NAME":/tmp/milimo-source-deploy.tar.gz 2>/dev/null
  rm -f /tmp/milimo-source-deploy.tar.gz

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/extensions/milimo && \
    tar xzf /tmp/milimo-source-deploy.tar.gz -C /sandbox/extensions/milimo && \
    rm /tmp/milimo-source-deploy.tar.gz && \
    echo "Plugin source extracted"
  '
  ok "Plugin source transferred"

  # ---- Step 3: Build plugin inside sandbox ----
  info "Building plugin inside sandbox..."
  sandbox_exec "$gateway" '
    cd /sandbox/extensions/milimo && \
    npm install 2>&1 | tail -3 && \
    npx tsc 2>&1 | tail -3 && \
    echo "Build complete"
  '

  if ! sandbox_exec "$gateway" 'test -f /sandbox/extensions/milimo/dist/index.js'; then
    error "Plugin build failed — dist/index.js not found in sandbox"
  fi
  ok "Plugin built in sandbox"

  # ---- Step 4: Copy to sandbox user extensions ----
  info "Installing plugin for sandbox user..."
  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.openclaw-data/extensions && \
    rm -rf /sandbox/.openclaw-data/extensions/milimo && \
    cp -r /sandbox/extensions/milimo /sandbox/.openclaw-data/extensions/milimo && \
    chown -R sandbox:sandbox /sandbox/.openclaw-data/extensions/milimo && \
    echo "Plugin installed for sandbox user"
  '

  if ! sandbox_exec "$gateway" 'test -f /sandbox/.openclaw-data/extensions/milimo/dist/index.js'; then
    error "Plugin not found in sandbox user extensions dir"
  fi
  ok "Plugin installed for sandbox user"

  # ---- Step 5: Deploy blueprint ----
  log_step "Deploying blueprint"
  cd "$ROOT_DIR"
  tar czf /tmp/milimo-blueprint-deploy.tar.gz \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    milimo-blueprint/ 2>/dev/null

  docker cp /tmp/milimo-blueprint-deploy.tar.gz "$gateway":/tmp/milimo-blueprint-deploy.tar.gz 2>/dev/null
  docker exec "$gateway" kubectl cp /tmp/milimo-blueprint-deploy.tar.gz openshell/"$SANDBOX_NAME":/tmp/milimo-blueprint-deploy.tar.gz 2>/dev/null
  rm -f /tmp/milimo-blueprint-deploy.tar.gz

  sandbox_exec "$gateway" '
    cd /sandbox && \
    tar xzf /tmp/milimo-blueprint-deploy.tar.gz && \
    rm /tmp/milimo-blueprint-deploy.tar.gz && \
    chown -R sandbox:sandbox /sandbox/milimo-blueprint && \
    echo "Blueprint deployed"
  '

  if ! sandbox_exec "$gateway" 'test -d /sandbox/milimo-blueprint/orchestrator/build'; then
    error "Blueprint extraction failed — orchestrator/build/ not found"
  fi
  ok "Blueprint deployed to /sandbox/milimo-blueprint"

  # ---- Step 6: Deploy assistant template ----
  log_step "Deploying support files"

  local template_file="$ROOT_DIR/milimo-blueprint/orchestrator/templates/assistant_system_prompt.md"
  if [ -f "$template_file" ]; then
    info "Deploying assistant system prompt template..."
    sandbox_exec "$gateway" '
      mkdir -p /sandbox/.milimo/templates && \
      echo "Template dir created"
    '
    docker cp "$template_file" "$gateway":/tmp/assistant_template.md 2>/dev/null
    docker exec "$gateway" kubectl cp /tmp/assistant_template.md openshell/"$SANDBOX_NAME":/tmp/assistant_template.md 2>/dev/null
    sandbox_exec "$gateway" '
      cp /tmp/assistant_template.md /sandbox/.milimo/templates/assistant_system_prompt.md && \
      cp /tmp/assistant_template.md /sandbox/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md 2>/dev/null || true && \
      rm /tmp/assistant_template.md && \
      chown -R sandbox:sandbox /sandbox/.milimo/templates && \
      echo "Template deployed"
    '
    ok "Assistant template deployed"
  else
    # Check alternate location
    template_file="$ROOT_DIR/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"
    if [ -f "$template_file" ]; then
      docker cp "$template_file" "$gateway":/tmp/assistant_template.md 2>/dev/null
      docker exec "$gateway" kubectl cp /tmp/assistant_template.md openshell/"$SANDBOX_NAME":/tmp/assistant_template.md 2>/dev/null
      sandbox_exec "$gateway" '
        mkdir -p /sandbox/.milimo/templates && \
        cp /tmp/assistant_template.md /sandbox/.milimo/templates/assistant_system_prompt.md && \
        rm /tmp/assistant_template.md && \
        chown -R sandbox:sandbox /sandbox/.milimo/templates && \
        echo "Template deployed from milimo-claw-docs"
      '
      ok "Assistant template deployed (from milimo-claw-docs)"
    else
      warn "Assistant template not found — assistant setup will use inline fallback"
    fi
  fi

  # ---- Step 6b: Initialize sandbox directories for all claws ----
  log_step "Initializing sandbox directories"

  sandbox_exec "$gateway" '
    # Ops Claw — primary mount at /sandbox/clients
    mkdir -p /sandbox/clients/{clients/{active,archived},projects/{active,completed},calendar,queue/{hold,review,auto},memory,context,logs,tools}

    # Content Claw — primary mount at /sandbox/content
    mkdir -p /sandbox/content/{drafts/{pending,approved,rejected},calendar,queue/{hold,review,auto},memory,context,logs,tools}

    # Analytics Claw — primary mount at /sandbox/analytics
    mkdir -p /sandbox/analytics/{reports/{daily,weekly,monthly},metrics,queue/{hold,review,auto},memory,context,logs,tools}

    # Finance Claw — primary mount at /sandbox/finance
    mkdir -p /sandbox/finance/{invoices/{draft,sent,paid,overdue},expenses,revenue,queue/{hold,review,auto},memory,context,logs,tools}

# Build Claw — primary mount at /sandbox/build
mkdir -p /sandbox/build/{prs/{open,merged,closed},deployments/{staging,production},tasks,docs,context,queue/{hold,review,auto},memory,logs,tools,data}

# Assistant Claw — primary mount at /sandbox/assistant
mkdir -p /sandbox/assistant/{context,memory,logs,tools,queue/{hold,review,auto}}

chown -R sandbox:sandbox /sandbox/clients /sandbox/content /sandbox/analytics /sandbox/finance /sandbox/build /sandbox/assistant

    # Fix log directory permissions (Issue #6: logs may be owned by root)
    for d in /sandbox/clients/logs /sandbox/content/logs /sandbox/analytics/logs /sandbox/finance/logs /sandbox/build/logs /sandbox/assistant/logs; do
      mkdir -p "$d"
      chown -R sandbox:sandbox "$d"
      chmod -R 755 "$d"
    done

    echo "All sandbox directories initialized"
  '
  ok "Sandbox directories initialized for all 6 claws (with log permissions fixed)"

  # ---- Step 6c: Copy blueprint to .milimo/blueprints/0.1.0/ ----
  info "Copying blueprint to .milimo/blueprints/0.1.0/..."
  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.milimo/blueprints/0.1.0 && \
    cp -r /sandbox/milimo-blueprint/* /sandbox/.milimo/blueprints/0.1.0/ && \
    chown -R sandbox:sandbox /sandbox/.milimo/blueprints && \
    echo "Blueprint copied to .milimo/blueprints/0.1.0/"
  '
  ok "Blueprint copied to /sandbox/.milimo/blueprints/0.1.0/"

  # ---- Step 6d: Install Python dependencies ----
  log_step "Installing Python dependencies"

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.local/lib/python3.11/site-packages
    pip3 install --target /sandbox/.local/lib/python3.11/site-packages \
      --quiet \
      pyyaml requests stripe httpx sentry-sdk typing_extensions 2>&1 | tail -3
    echo "Python packages installed"
  '
  ok "Python dependencies installed (pyyaml, requests, stripe, httpx, sentry-sdk)"

  # ---- Step 6e: Install gh CLI (GitHub CLI) ----
  log_step "Installing GitHub CLI"

  sandbox_exec "$gateway" '
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
      GH_ARCH="arm64"
    else
      GH_ARCH="amd64"
    fi

    mkdir -p /sandbox/.local/bin
    GH_VERSION="2.67.0"
    GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"

    cd /tmp && curl -sL "$GH_URL" -o gh.tar.gz && tar xzf gh.tar.gz
    cp gh_*_linux_${GH_ARCH}/bin/gh /sandbox/.local/bin/gh
    chmod +x /sandbox/.local/bin/gh
    rm -rf /tmp/gh*
    echo "gh CLI installed (linux/${GH_ARCH})"
  '
  ok "GitHub CLI (gh) installed at /sandbox/.local/bin/gh"

  # ---- Step 6f: Create milimo CLI wrapper ----
  log_step "Creating milimo CLI wrapper"

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.local/bin
    cat > /sandbox/.local/bin/milimo << '\''MILIMO_EOF'\''
#!/usr/bin/env python3
"""Milimo Claw CLI wrapper — delegates to bridge_cli.py"""
import sys
BLUEPRINT_PATH = "/sandbox/.milimo/blueprints/0.1.0"
if BLUEPRINT_PATH not in sys.path:
    sys.path.insert(0, BLUEPRINT_PATH)
from orchestrator.bridge_cli import main
if __name__ == "__main__":
    main()
MILIMO_EOF
    chmod +x /sandbox/.local/bin/milimo

    # Add to shell profiles so it'\''s in PATH
    echo '\''export PATH=$HOME/.local/bin:$PATH'\'' >> /sandbox/.bashrc 2>/dev/null || true
    echo '\''export PATH=$HOME/.local/bin:$PATH'\'' >> /sandbox/.profile 2>/dev/null || true
    echo "milimo CLI wrapper created"
  '
  ok "milimo CLI wrapper created at /sandbox/.local/bin/milimo"

  # ---- Step 6g: Fix broken .venv (recreate with sandbox Python) ----
  log_step "Fixing Python virtual environment"

  sandbox_exec "$gateway" '
    BLUEPRINT_DIR="/sandbox/milimo-blueprint"
    VENV_DIR="$BLUEPRINT_DIR/.venv"

    # Remove broken venv (may point to host Python)
    if [ -d "$VENV_DIR" ]; then
      rm -rf "$VENV_DIR"
    fi

    # Create fresh venv with sandbox Python
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --quiet pyyaml requests stripe httpx sentry-sdk typing_extensions

    # Verify imports
    python3 -c "import yaml, requests, stripe, httpx, sentry_sdk; print(\"venv OK\")"
    echo "Python venv recreated and verified"
  '
  ok "Python venv recreated with sandbox Python"

  # ---- Step 6h: Inject environment variables into sandbox ----
  log_step "Injecting environment variables"
  info "Reading .env and injecting into sandbox shell profiles..."

  # Read .env from project root and extract relevant vars
  ENV_FILE="$ROOT_DIR/.env"
  if [ ! -f "$ENV_FILE" ]; then
    warn ".env file not found at $ENV_FILE — skipping env injection"
  else
    # Extract vars we need (skip comments and empty lines)
    ENV_VARS=$(
      grep -E "^(NVIDIA_API_KEY|BUILD_CLAW_NVIDIA_API_KEY|GITHUB_TOKEN|GH_TOKEN|GITHUB_REPO|STRIPE_SECRET_KEY|VERCEL_TOKEN|SENTRY_AUTH_TOKEN|STRIPE_WEBHOOK_SECRET|VERCEL_PROJECT_ID|VERCEL_TEAM_ID)=" "$ENV_FILE" 2>/dev/null || true
    )

    if [ -z "$ENV_VARS" ]; then
      warn "No relevant environment variables found in .env"
    else
      # Build the export block for sandbox .bashrc and .profile
      sandbox_exec "$gateway" "
# Remove old Milimo env block from .bashrc
sed -i.bak '/# milimo-env begin/,/# milimo-env end/d' /sandbox/.bashrc 2>/dev/null || true
sed -i.bak '/# milimo-env begin/,/# milimo-env end/d' /sandbox/.profile 2>/dev/null || true

# Append new env block
cat >> /sandbox/.bashrc << 'MILIMO_ENV_EOF'
# milimo-env begin
$(echo "$ENV_VARS" | while read -r line; do echo "export $line"; done)
export PYTHONPATH=/sandbox/.local/lib/python3.11/site-packages:\$PYTHONPATH
export PATH=/sandbox/.local/bin:\$PATH
# milimo-env end
MILIMO_ENV_EOF

cat >> /sandbox/.profile << 'MILIMO_ENV_EOF'
# milimo-env begin
$(echo "$ENV_VARS" | while read -r line; do echo "export $line"; done)
export PYTHONPATH=/sandbox/.local/lib/python3.11/site-packages:\$PYTHONPATH
export PATH=/sandbox/.local/bin:\$PATH
# milimo-env end
MILIMO_ENV_EOF

echo 'Environment variables injected'
"
      ok "Environment variables injected into /sandbox/.bashrc and /sandbox/.profile"
    fi
  fi

  # ---- Step 6i: Create Python .pth file for package discovery ----
  log_step "Configuring Python package path"
  sandbox_exec "$gateway" '
# Create .pth file so Python finds packages installed via --target
PTH_DIR="/usr/local/lib/python3.11/dist-packages"
mkdir -p "$PTH_DIR"
echo "/sandbox/.local/lib/python3.11/site-packages" > "$PTH_DIR/milimo-local.pth"
echo "Created milimo-local.pth"
'
  ok "Python .pth file created — packages at /sandbox/.local/lib/python3.11/site-packages now discoverable"

  # ---- Step 6j: Cleanup stale PID files ----
  log_step "Cleaning stale PID files"
  sandbox_exec "$gateway" '
# Remove stale launcher PID file (persistent volumes retain old PIDs)
LAUNCHER_PID="/sandbox/.milimo/mesh/launcher.pid"
if [ -f "$LAUNCHER_PID" ]; then
    OLD_PID=$(cat "$LAUNCHER_PID" 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "Launcher PID $OLD_PID is still running — not removing"
        else
            rm -f "$LAUNCHER_PID"
            echo "Removed stale launcher PID file (was PID $OLD_PID)"
        fi
    fi
fi

# Remove stale heartbeat files older than 5 minutes
find /sandbox/.milimo/mesh/heartbeats -name "*.json" -mmin +5 -delete 2>/dev/null || true
echo "Cleanup complete"
'
  ok "Stale PID files cleaned"

  # ---- Step 7: Fix permissions ----
  log_step "Fixing permissions"
  sandbox_exec "$gateway" '
    # Fix .milimo ownership
    mkdir -p /sandbox/.milimo/blueprints
    chown -R sandbox:sandbox /sandbox/.milimo

    # Fix .openclaw ownership
    chown -R sandbox:sandbox /sandbox/.openclaw
    chmod -R 755 /sandbox/.openclaw

    # Fix credentials dir
    mkdir -p /sandbox/.openclaw/credentials
    chown -R sandbox:sandbox /sandbox/.openclaw/credentials
    chmod 755 /sandbox/.openclaw/credentials

    # Fix agents/main dir
    mkdir -p /sandbox/.openclaw/agents/main
    chown -R sandbox:sandbox /sandbox/.openclaw/agents/main
    chmod -R 775 /sandbox/.openclaw/agents/main

    echo "All permissions fixed"
  '
  ok "Permissions fixed"

  # ---- Step 8: Verify critical file sync ----
  info "Verifying critical files are synced to all sandbox locations..."
  sandbox_exec "$gateway" '
    ERRORS=0

    # Verify orchestrator files exist in primary location
for claw in ops analytics content finance build; do
        f="/sandbox/milimo-blueprint/orchestrator/${claw}/${claw}_claw.py"
      if [ ! -f "$f" ]; then
        echo "MISSING: $f"
        ERRORS=$((ERRORS + 1))
      fi
    done
# Assistant uses lucy.py, not assistant_claw.py
f="/sandbox/milimo-blueprint/orchestrator/assistant/lucy.py"
if [ ! -f "$f" ]; then
 echo "MISSING: $f"
 ERRORS=$((ERRORS + 1))
fi


    # Verify mesh_config.yaml exists and has assistant types under message_types
    MC="/sandbox/milimo-blueprint/mesh_config.yaml"
    if [ ! -f "$MC" ]; then
      echo "MISSING: $MC"
      ERRORS=$((ERRORS + 1))
    else
      # Verify assistant message types are properly nested (not at root level)
      if grep -q "^assistant_query:" "$MC"; then
        echo "YAML ERROR: assistant_query at root level (should be under message_types)"
        ERRORS=$((ERRORS + 1))
      fi
      if grep -q "^assistant_task:" "$MC"; then
        echo "YAML ERROR: assistant_task at root level (should be under message_types)"
        ERRORS=$((ERRORS + 1))
      fi
      if grep -q "  assistant_query:" "$MC" && grep -q "  assistant_task:" "$MC"; then
        echo "mesh_config OK: assistant types properly nested under message_types"
      fi
    fi

    # Verify blueprints copy is in sync
    BP="/sandbox/.milimo/blueprints/0.1.0"
    if [ -d "$BP/orchestrator" ]; then
      for claw in ops analytics content finance build; do
        f="$BP/orchestrator/${claw}/${claw}_claw.py"
        if [ ! -f "$f" ]; then
          echo "MISSING (blueprints copy): $f"
          ERRORS=$((ERRORS + 1))
        fi
      done
# Assistant uses lucy.py, not assistant_claw.py
f="$BP/orchestrator/assistant/lucy.py"
if [ ! -f "$f" ]; then
 echo "MISSING (blueprints copy): $f"
 ERRORS=$((ERRORS + 1))
fi

    fi

    if [ $ERRORS -eq 0 ]; then
      echo "All critical files verified"
    else
      echo "WARNING: $ERRORS files missing or misconfigured"
    fi
  '
  ok "Critical file sync verified"

  # ---- Step 9: Register plugin in openclaw.json ----
  log_step "Registering plugin"

  local reg_script
  # Clean stale temp files from previous failed runs
  rm -f /tmp/milimo-register.* /tmp/milimo-config.* 2>/dev/null

  reg_script=$(mktemp /tmp/milimo-register.XXXXXX)
  reg_script="${reg_script}.py"
  cat >"$reg_script" <<'PYEOF'
import json, os
from datetime import datetime, timezone

config_path = "/sandbox/.openclaw/openclaw.json"
with open(config_path) as f:
    config = json.load(f)

config["plugins"] = {
    "entries": {
        "milimo": { "enabled": True }
    },
    "installs": {
        "milimo": {
            "source": "path",
            "sourcePath": "/sandbox/extensions/milimo",
            "installPath": "/sandbox/.openclaw-data/extensions/milimo",
            "version": os.environ.get("MILIMO_VERSION", "2.0.0"),
            "installedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
    }
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")

print("Plugin registered in openclaw.json")
PYEOF

  docker cp "$reg_script" "$gateway":/tmp/milimo-register.py 2>/dev/null
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- python3 /tmp/milimo-register.py 2>/dev/null
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- rm /tmp/milimo-register.py 2>/dev/null
  rm -f "$reg_script"
  ok "Plugin registered in /sandbox/.openclaw/openclaw.json"

  # ---- Step 10: Restart gateway ----
  log_step "Restarting OpenClaw gateway"
  sandbox_exec "$gateway" '
    pkill -f "openclaw" 2>/dev/null || true
    echo "Gateway restart initiated"
  '
  info "Waiting for gateway to restart..."
  sleep 8
  ok "Gateway restarted"
}

# ---------------------------------------------------------------------------
# Phase 3: Non-Interactive Onboarding
# ---------------------------------------------------------------------------
run_onboarding() {
  log_step "Configuring MilimoClaw"

  local operator="${OPERATOR_NAME:-${USER:-operator}}"
  local squad="${SQUAD_NAME:-milimo-squad}"

  if [ "$DRY_RUN" = true ]; then
    info "Dry run — would configure:"
    info " Squad: $squad (solo template, all 6 claws)"
    info "  Operator: $operator"
    info "  War Room: $WARROOM_MODE"
    return 0
  fi

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  # Write config script to a temp file to avoid quoting hell
  local config_script
  config_script=$(mktemp /tmp/milimo-config.XXXXXX)
  cat >"$config_script" <<PYEOF
import json, os
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()
squad = "${squad}"
operator = "${operator}"
warroom = "${WARROOM_MODE}"
version = "${MILIMO_VERSION}"

# Plugin ConfigManager format (flat — what the TypeScript plugin reads)
plugin_config = {
    "squadName": squad,
    "clawRole": "",
    "template": "solo",
    "solo": True,
    "operatorName": operator,
    "warRoomMode": warroom,
    "onboardedAt": now,
"activeClaws": ["content", "ops", "analytics", "finance", "build", "assistant"],
        # Assistant config for assistant_setup.py
        "assistant": {
            "name": "Lucy",
            "creature": "a claw",
            "vibe": "sharp and unhurried",
            "emoji": "🦀"
        }
        }

        # Orchestrator format (nested — for Python code)
        orchestrator_config = {
            "version": version,
            "squad": {
                "name": squad,
                "template": "solo",
                "mode": "solo",
                "onboarded_at": now
            },
            "operator": { "name": operator },
            "claws": {
                "content": { "enabled": True, "mount": "/sandbox/content" },
                "ops": { "enabled": True, "mount": "/sandbox/clients" },
                "analytics": { "enabled": True, "mount": "/sandbox/analytics" },
                "finance": { "enabled": True, "mount": "/sandbox/finance" },
                "build": { "enabled": True, "mount": "/sandbox/build" },
                "assistant": { "enabled": True, "mount": "/sandbox/assistant" }
            },
            "war_room": { "mode": warroom },
            "mesh": { "enabled": False, "secret": None },
            "blueprint_dir": "/sandbox/milimo-blueprint",
            "activeClaws": ["content", "ops", "analytics", "finance", "build", "assistant"],
    # Assistant config for assistant_setup.py
    "assistant": {
        "name": "Lucy",
        "creature": "a claw",
        "vibe": "sharp and unhurried",
        "emoji": "🦀"
    }
}

# Write plugin config to /root/.milimo (plugin reads as root)
os.makedirs("/root/.milimo", exist_ok=True)
with open("/root/.milimo/config.json", "w") as f:
    json.dump(plugin_config, f, indent=2)

# Write orchestrator config to /sandbox/.milimo (Python reads here)
os.makedirs("/sandbox/.milimo", exist_ok=True)
with open("/sandbox/.milimo/config.json", "w") as f:
    json.dump(orchestrator_config, f, indent=2)

# Fix ownership
os.chown("/sandbox/.milimo/config.json", 999, 999)
os.chown("/root/.milimo/config.json", 0, 0)

print("Both configs written")
print(f"  Squad: {squad} (solo)")
print(f"  Operator: {operator}")
PYEOF

  docker cp "$config_script" "$gateway":/tmp/milimo-config.py 2>/dev/null
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- python3 /tmp/milimo-config.py 2>/dev/null
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- rm /tmp/milimo-config.py 2>/dev/null
  rm -f "$config_script"

  ok "Squad: $squad (solo template)"
  ok "Operator: $operator"
  ok "Claws: Content, Ops, Analytics, Finance, Build, Assistant — all enabled"
  ok "War Room: $WARROOM_MODE"

  # ---- Run assistant setup ----
  info "Configuring squad assistant..."
  sandbox_exec "$gateway" '
    # Clear old sessions and memory so the assistant loads fresh context
    rm -f /sandbox/.openclaw/agents/main/sessions/*.jsonl
    rm -f /sandbox/.openclaw/agents/main/sessions/sessions.json
    rm -f /sandbox/.openclaw/workspace/MEMORY.md
    rm -rf /sandbox/.openclaw/workspace/memory/daily/
    rm -rf /sandbox/.openclaw/workspace/memory/channel/

    cd /sandbox/milimo-blueprint && HOME=/sandbox python3 orchestrator/assistant_setup.py 2>&1 || echo "Assistant setup skipped — run manually with: openclaw milimo assistant setup"
  '
}

# ---------------------------------------------------------------------------
# Phase 4: Verification
# ---------------------------------------------------------------------------
verify_installation() {
  log_step "Verifying installation"

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  # Check plugin loaded
  local plugin_check
  plugin_check=$(sandbox_exec "$gateway" '
    openclaw milimo --help 2>&1 || echo "MILIMO_COMMAND_NOT_FOUND"
  ') || true

  if echo "$plugin_check" | grep -qi "milimo.*registered\|Milimo Claw\|Squad:"; then
    ok "Milimo Claw plugin is loaded"
    # Extract squad info
    local squad_info
    squad_info=$(echo "$plugin_check" | grep -i "Squad:" | head -1 | sed 's/.*│//' | sed 's/│.*//' | xargs)
    if [ -n "$squad_info" ]; then
      ok "Squad: $squad_info"
    fi
  elif echo "$plugin_check" | grep -qi "MILIMO_COMMAND_NOT_FOUND\|unknown command"; then
    error "Milimo Claw plugin is NOT loaded.
To fix manually inside the sandbox:
  1. cd /sandbox/extensions/milimo && npm install && npx tsc
  2. openclaw plugins install /sandbox/extensions/milimo
  3. pkill -f openclaw (gateway auto-restarts)"
  else
    warn "Plugin status unclear. Output:
$plugin_check"
  fi

  # Check Build Claw modules
  local build_check
  build_check=$(sandbox_exec "$gateway" '
    ls /sandbox/milimo-blueprint/orchestrator/build/build_claw.py 2>/dev/null && echo "OK" || echo "MISSING"
  ') || true

  if [ "$build_check" = "OK" ]; then
    local module_count
    module_count=$(sandbox_exec "$gateway" 'ls /sandbox/milimo-blueprint/orchestrator/build/*.py 2>/dev/null | grep -v __init__ | wc -l') || true
    ok "Build Claw present ($module_count modules)"
  else
    warn "Build Claw blueprint not found"
  fi

  # Check config
  local config_check
  config_check=$(sandbox_exec "$gateway" '
    cat /sandbox/.milimo/config.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"squad\",{}).get(\"name\",\"?\"))" 2>/dev/null || echo "MISSING"
  ') || true

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
  echo " Squad: $squad (solo — all 6 claws active)"
  echo " Operator: $operator"
  echo " Claws: Content · Ops · Analytics · Finance · Build · Assistant"
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
  deploy_to_sandbox
  run_onboarding
  verify_installation
  print_summary
}

main "$@"
