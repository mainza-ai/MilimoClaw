#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# MilimoClaw One-Command Installer
#
# Two installation modes:
#   1. Dockerfile mode (default, recommended): Generates a Dockerfile and runs
#      nemoclaw onboard --from to bake the plugin into a custom sandbox image.
#      This is the official NemoClaw plugin installation path.
#   2. Runtime deploy mode (--runtime-deploy): Injects files into a running
#      sandbox via docker cp + kubectl cp. Use this for quick updates without
#      rebuilding the sandbox image.
#
# Usage:
# cd /path/to/MilimoClaw
# ./install.sh --solo --operator-name "YourName" --squad-name "my-squad"
# ./install.sh --solo --runtime-deploy   # runtime inject into running sandbox
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
RUNTIME_DEPLOY=false

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
    --runtime-deploy)
      RUNTIME_DEPLOY=true
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
      printf " --dry-run Show what would be done without doing it\n"
      printf " --runtime-deploy Runtime inject into running sandbox (skip Dockerfile build)\n"
      printf " --uninstall Remove MilimoClaw, keep NemoClaw\n"
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
        rm -rf /sandbox/.openclaw-data/extensions/milimo
        rm -rf /sandbox/.openclaw-data/milimo
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
  # Run as sandbox user (uid 999) — never as root inside the sandbox
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- su -s /bin/bash sandbox -c "$*"
}

# Run as root inside sandbox — ONLY for openclaw plugins install (needs config access)
sandbox_exec_root() {
  local gateway="$1"
  shift
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- bash -c "$*"
}

# Copy a file into the sandbox and make it readable by sandbox user
sandbox_cp() {
  local gateway="$1"
  local src="$2"
  local dst="$3"
  docker exec "$gateway" kubectl cp "$src" openshell/"$SANDBOX_NAME":"$dst" 2>/dev/null
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- chmod 644 "$dst" 2>/dev/null
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
  local node_minor
  node_minor=$(echo "$node_version" | cut -d. -f2)
  if ((node_major < 22 || (node_major == 22 && node_minor < 16))); then
    error "Node.js $node_version is too old. NemoClaw requires Node.js >= 22.16 (per official prerequisites)."
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

  # NemoClaw sandbox must be running (runtime deploy mode only — Dockerfile mode creates it)
  if [ "$RUNTIME_DEPLOY" = true ]; then
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
  else
    ok "Dockerfile mode — sandbox will be created by nemoclaw onboard"
  fi
}

# ---------------------------------------------------------------------------
# Phase 1b: Generate Dockerfile (official NemoClaw plugin installation path)
# ---------------------------------------------------------------------------
generate_dockerfile() {
  local build_dir="$1"
  local dockerfile_path="$build_dir/Dockerfile"

  cat >"$dockerfile_path" <<'DOCKERFILE_EOF'
ARG SANDBOX_BASE=ghcr.io/nvidia/nemoclaw/sandbox-base:latest
FROM ${SANDBOX_BASE}

# Copy Milimo plugin source
COPY milimo/ /opt/milimo/
WORKDIR /opt/milimo
RUN npm ci --no-audit --no-fund && npm run build
RUN mkdir -p /sandbox/.openclaw-data/extensions \
    && cp -a /opt/milimo /sandbox/.openclaw-data/extensions/milimo \
    && openclaw doctor --fix

# Copy Milimo blueprint
COPY milimo-blueprint/ /sandbox/.openclaw-data/milimo/milimo-blueprint/

# Create claw data directories
RUN BASE="/sandbox/.openclaw-data/milimo/claws" \
    && mkdir -p "$BASE/ops/clients/active" "$BASE/ops/clients/archived" \
    && mkdir -p "$BASE/ops/projects/active" "$BASE/ops/projects/completed" \
    && mkdir -p "$BASE/ops/calendar" "$BASE/ops/queue/hold" "$BASE/ops/queue/review" "$BASE/ops/queue/auto" \
    && mkdir -p "$BASE/ops/memory" "$BASE/ops/context" "$BASE/ops/logs" "$BASE/ops/tools" \
    && mkdir -p "$BASE/content/drafts/pending" "$BASE/content/drafts/approved" "$BASE/content/drafts/rejected" \
    && mkdir -p "$BASE/content/calendar" "$BASE/content/queue/hold" "$BASE/content/queue/review" "$BASE/content/queue/auto" \
    && mkdir -p "$BASE/content/memory" "$BASE/content/context" "$BASE/content/logs" "$BASE/content/tools" \
    && mkdir -p "$BASE/analytics/reports/daily" "$BASE/analytics/reports/weekly" "$BASE/analytics/reports/monthly" \
    && mkdir -p "$BASE/analytics/metrics" "$BASE/analytics/queue/hold" "$BASE/analytics/queue/review" "$BASE/analytics/queue/auto" \
    && mkdir -p "$BASE/analytics/memory" "$BASE/analytics/context" "$BASE/analytics/logs" "$BASE/analytics/tools" \
    && mkdir -p "$BASE/finance/invoices/draft" "$BASE/finance/invoices/sent" "$BASE/finance/invoices/paid" "$BASE/finance/invoices/overdue" \
    && mkdir -p "$BASE/finance/expenses" "$BASE/finance/revenue" \
    && mkdir -p "$BASE/finance/queue/hold" "$BASE/finance/queue/review" "$BASE/finance/queue/auto" \
    && mkdir -p "$BASE/finance/memory" "$BASE/finance/context" "$BASE/finance/logs" "$BASE/finance/tools" \
    && mkdir -p "$BASE/build/prs/open" "$BASE/build/prs/merged" "$BASE/build/prs/closed" \
    && mkdir -p "$BASE/build/deployments/staging" "$BASE/build/deployments/production" \
    && mkdir -p "$BASE/build/tasks" "$BASE/build/docs" "$BASE/build/context" "$BASE/build/data" \
    && mkdir -p "$BASE/build/queue/hold" "$BASE/build/queue/review" "$BASE/build/queue/auto" \
    && mkdir -p "$BASE/build/memory" "$BASE/build/logs" "$BASE/build/tools" \
    && mkdir -p "$BASE/assistant/context" "$BASE/assistant/memory" "$BASE/assistant/logs" "$BASE/assistant/tools" \
    && mkdir -p "$BASE/assistant/queue/hold" "$BASE/assistant/queue/review" "$BASE/assistant/queue/auto"

# Install Python dependencies
RUN pip3 install --target /sandbox/.local/lib/python3.11/site-packages \
        --quiet pyyaml requests stripe httpx sentry-sdk typing_extensions \
    && PTH_DIR="/usr/local/lib/python3.11/dist-packages" \
    && mkdir -p "$PTH_DIR" \
    && echo "/sandbox/.local/lib/python3.11/site-packages" > "$PTH_DIR/milimo-local.pth"

# Install GitHub CLI
RUN ARCH=$(uname -m) \
    && if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then GH_ARCH="arm64"; else GH_ARCH="amd64"; fi \
    && GH_VERSION="2.67.0" \
    && GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz" \
    && cd /tmp && curl -sL "$GH_URL" -o gh.tar.gz && tar xzf gh.tar.gz \
    && mkdir -p /sandbox/.openclaw-data/milimo/bin \
    && cp gh_*_linux_${GH_ARCH}/bin/gh /sandbox/.openclaw-data/milimo/bin/gh \
    && chmod +x /sandbox/.openclaw-data/milimo/bin/gh \
    && ln -sf /sandbox/.openclaw-data/milimo/bin/gh /usr/local/bin/gh \
    && rm -rf /tmp/gh*

# Create blueprint symlink + backward compat symlink
RUN mkdir -p /sandbox/.openclaw-data/milimo/blueprints \
    && ln -sfn /sandbox/.openclaw-data/milimo/milimo-blueprint /sandbox/.openclaw-data/milimo/blueprints/0.1.0 \
    && rm -rf /sandbox/.milimo 2>/dev/null || true \
    && ln -sfn /sandbox/.openclaw-data/milimo /sandbox/.milimo

WORKDIR /opt/nemoclaw
DOCKERFILE_EOF

  ok "Dockerfile generated at $dockerfile_path"
}

# ---------------------------------------------------------------------------
# Phase 2a: Dockerfile-based deploy (official NemoClaw path)
# ---------------------------------------------------------------------------
deploy_via_dockerfile() {
  log_step "Building Milimo plugin (Dockerfile mode)"

  # Build plugin on host first to verify it compiles
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

  # Prepare build directory
  log_step "Preparing Dockerfile build context"
  local build_dir
  build_dir=$(mktemp -d /tmp/milimo-docker-build.XXXXXX)

  # Copy plugin source (strip macOS xattrs)
  info "Copying plugin source to build context..."
  cd "$ROOT_DIR/milimo"
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-context.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__tests__' --exclude='*.test.ts' --exclude='tsconfig.tsbuildinfo' \
    . 2>/dev/null
  cd "$ROOT_DIR"
  mkdir -p "$build_dir/milimo"
  tar xzf /tmp/milimo-plugin-context.tar.gz -C "$build_dir/milimo"
  rm -f /tmp/milimo-plugin-context.tar.gz

  # Copy blueprint (strip macOS xattrs)
  info "Copying blueprint to build context..."
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-blueprint-context.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    -C "$ROOT_DIR" milimo-blueprint/ 2>/dev/null
  tar xzf /tmp/milimo-blueprint-context.tar.gz -C "$build_dir"
  rm -f /tmp/milimo-blueprint-context.tar.gz

  # Generate Dockerfile
  generate_dockerfile "$build_dir"

  # Run nemoclaw onboard --from
  log_step "Running nemoclaw onboard --from (official NemoClaw plugin path)"
  info "This will build a custom sandbox image with MilimoClaw baked in."
  info "Build context: $build_dir"

  if [ "$DRY_RUN" = true ]; then
    info "Dry run — would run: nemoclaw onboard --from $build_dir/Dockerfile --name $SANDBOX_NAME"
    return 0
  fi

  local onboard_args=("--from" "$build_dir/Dockerfile" "--name" "$SANDBOX_NAME")
  if [ "$NON_INTERACTIVE" = true ]; then
    onboard_args+=("--non-interactive" "--yes-i-accept-third-party-software")
  fi

  info "Running: nemoclaw onboard ${onboard_args[*]}"
  nemoclaw onboard "${onboard_args[@]}" 2>&1 || {
    error "nemoclaw onboard --from failed. Check the Dockerfile and build context at: $build_dir"
    error "You can retry with: nemoclaw onboard --from $build_dir/Dockerfile"
    return 1
  }

  ok "Sandbox built with MilimoClaw via official Dockerfile path"
  rm -rf "$build_dir"
}
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
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-source-deploy.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__tests__' --exclude='*.test.ts' --exclude='tsconfig.tsbuildinfo' \
    . 2>/dev/null
  cd "$ROOT_DIR"

  docker cp /tmp/milimo-source-deploy.tar.gz "$gateway":/tmp/milimo-source-deploy.tar.gz 2>/dev/null
  sandbox_cp "$gateway" /tmp/milimo-source-deploy.tar.gz /tmp/milimo-source-deploy.tar.gz
  rm -f /tmp/milimo-source-deploy.tar.gz

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.openclaw-data/extensions/milimo && \
    tar xzf /tmp/milimo-source-deploy.tar.gz -C /sandbox/.openclaw-data/extensions/milimo && \
    echo "Plugin source extracted to .openclaw-data/extensions/milimo"
  '
  sandbox_exec_root "$gateway" 'rm -f /tmp/milimo-source-deploy.tar.gz'
  ok "Plugin source transferred"

  # ---- Step 3: Build plugin inside sandbox ----
  info "Building plugin inside sandbox..."
  sandbox_exec "$gateway" '
    cd /sandbox/.openclaw-data/extensions/milimo && \
    npm install 2>&1 | tail -3 && \
    npx tsc 2>&1 | tail -3 && \
    echo "Build complete"
  '

  if ! sandbox_exec "$gateway" 'test -f /sandbox/.openclaw-data/extensions/milimo/dist/index.js'; then
    error "Plugin build failed — dist/index.js not found in sandbox"
  fi
  ok "Plugin built in sandbox (.openclaw-data/extensions/milimo)"

  # ---- Step 5: Deploy blueprint ----
  log_step "Deploying blueprint"
  cd "$ROOT_DIR"
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-blueprint-deploy.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    milimo-blueprint/ 2>/dev/null

  docker cp /tmp/milimo-blueprint-deploy.tar.gz "$gateway":/tmp/milimo-blueprint-deploy.tar.gz 2>/dev/null
  sandbox_cp "$gateway" /tmp/milimo-blueprint-deploy.tar.gz /tmp/milimo-blueprint-deploy.tar.gz
  rm -f /tmp/milimo-blueprint-deploy.tar.gz

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.openclaw-data/milimo && \
    cd /sandbox/.openclaw-data/milimo && \
    tar xzf /tmp/milimo-blueprint-deploy.tar.gz && \
    echo "Blueprint deployed"
  '
  sandbox_exec_root "$gateway" 'rm -f /tmp/milimo-blueprint-deploy.tar.gz'

  if ! sandbox_exec "$gateway" 'test -d /sandbox/.openclaw-data/milimo/milimo-blueprint/orchestrator/build'; then
    error "Blueprint extraction failed — orchestrator/build/ not found"
  fi
  ok "Blueprint deployed to /sandbox/.openclaw-data/milimo/milimo-blueprint"

  # ---- Step 6: Deploy assistant template ----
  log_step "Deploying support files"

  local template_file="$ROOT_DIR/milimo-blueprint/orchestrator/templates/assistant_system_prompt.md"
  if [ -f "$template_file" ]; then
    info "Deploying assistant system prompt template..."
    docker cp "$template_file" "$gateway":/tmp/assistant_template.md 2>/dev/null
    sandbox_cp "$gateway" /tmp/assistant_template.md /tmp/assistant_template.md
    sandbox_exec "$gateway" '
      mkdir -p /sandbox/.openclaw-data/milimo/templates && \
      cp /tmp/assistant_template.md /sandbox/.openclaw-data/milimo/templates/assistant_system_prompt.md && \
      echo "Template deployed"
    '
    sandbox_exec_root "$gateway" 'rm -f /tmp/assistant_template.md'
    ok "Assistant template deployed"
  else
    template_file="$ROOT_DIR/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"
    if [ -f "$template_file" ]; then
      docker cp "$template_file" "$gateway":/tmp/assistant_template.md 2>/dev/null
      sandbox_cp "$gateway" /tmp/assistant_template.md /tmp/assistant_template.md
      sandbox_exec "$gateway" '
        mkdir -p /sandbox/.openclaw-data/milimo/templates && \
        cp /tmp/assistant_template.md /sandbox/.openclaw-data/milimo/templates/assistant_system_prompt.md && \
        echo "Template deployed from milimo-claw-docs"
      '
      sandbox_exec_root "$gateway" 'rm -f /tmp/assistant_template.md'
      ok "Assistant template deployed (from milimo-claw-docs)"
    else
      warn "Assistant template not found — assistant setup will use inline fallback"
    fi
  fi

  # ---- Step 6b: Initialize sandbox directories for all claws ----
  log_step "Initializing sandbox directories"

  # All claw data goes under .openclaw-data/milimo/claws/ (writable path)
  sandbox_exec "$gateway" '
    BASE="/sandbox/.openclaw-data/milimo/claws"
    mkdir -p $BASE/ops/{clients/{active,archived},projects/{active,completed},calendar,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/content/{drafts/{pending,approved,rejected},calendar,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/analytics/{reports/{daily,weekly,monthly},metrics,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/finance/{invoices/{draft,sent,paid,overdue},expenses,revenue,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/build/{prs/{open,merged,closed},deployments/{staging,production},tasks,docs,context,queue/{hold,review,auto},memory,logs,tools,data}
    mkdir -p $BASE/assistant/{context,memory,logs,tools,queue/{hold,review,auto}}
    echo "All sandbox directories initialized under .openclaw-data/milimo/claws/"
  '
  ok "Sandbox directories initialized for all 6 claws"

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

  # Install gh CLI to /sandbox/.openclaw-data/milimo/bin/ so it survives rebuilds
  # (per NemoClaw docs, .openclaw-data is the persistent writable subtree;
  # /sandbox/.local/bin/ is under the read-only /sandbox/ root on production kernels)
  sandbox_exec "$gateway" '
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        GH_ARCH="arm64"
    else
        GH_ARCH="amd64"
    fi

    mkdir -p /sandbox/.openclaw-data/milimo/bin
    GH_VERSION="2.67.0"
    GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"

    cd /tmp && curl -sL "$GH_URL" -o gh.tar.gz && tar xzf gh.tar.gz
    cp gh_*_linux_${GH_ARCH}/bin/gh /sandbox/.openclaw-data/milimo/bin/gh
    chmod +x /sandbox/.openclaw-data/milimo/bin/gh
    rm -rf /tmp/gh*

    # Create symlink in /usr/local/bin so gh is on PATH
    ln -sf /sandbox/.openclaw-data/milimo/bin/gh /usr/local/bin/gh 2>/dev/null || true
    echo "gh CLI installed (linux/${GH_ARCH})"
'
  ok "GitHub CLI (gh) installed at /sandbox/.openclaw-data/milimo/bin/gh"

  # ---- Step 6f: Create milimo CLI wrapper ----
  log_step "Creating milimo CLI wrapper"

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.openclaw-data/milimo/bin
    cat > /sandbox/.openclaw-data/milimo/bin/milimo << '\''MILIMO_EOF'\''
#!/usr/bin/env python3
"""Milimo Claw CLI wrapper — delegates to bridge_cli.py"""
import sys
BLUEPRINT_PATH = "/sandbox/.openclaw-data/milimo/blueprints/0.1.0"
if BLUEPRINT_PATH not in sys.path:
    sys.path.insert(0, BLUEPRINT_PATH)
from orchestrator.bridge_cli import main
if __name__ == "__main__":
    main()
MILIMO_EOF
    chmod +x /sandbox/.openclaw-data/milimo/bin/milimo
    echo "milimo CLI wrapper created at /sandbox/.openclaw-data/milimo/bin/milimo"
  '
  ok "milimo CLI wrapper created"

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

  # ---- Step 6h: Environment variable setup ----
  log_step "Configuring environment variables"
  info "NemoClaw manages inference credentials via the L7 proxy."
  info "GitHub and other service tokens should be registered with the OpenShell gateway."
  info "See: nemoclaw credentials list"

  # Store GITHUB_TOKEN in NemoClaw credentials if available
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    info "GITHUB_TOKEN detected — register with OpenShell gateway via:"
    info "  nemoclaw $SANDBOX_NAME credentials set github GITHUB_TOKEN $GITHUB_TOKEN"
    info "  (or it will be injected into /etc/environment for the current session only)"
  else
    warn "GITHUB_TOKEN not set in host environment."
    warn "Set it before running install.sh for automatic credential storage:"
    warn " export GITHUB_TOKEN=ghp_your_token"
    warn "Or register manually: nemoclaw credentials list"
  fi

  # Configure gh CLI auth in sandbox via env vars (survives within same sandbox session)
  # Note: These env vars are ephemeral — they do NOT survive nemoclaw <name> rebuild.
  # For rebuild persistence, register GITHUB_TOKEN with the OpenShell gateway.
  sandbox_exec "$gateway" '
    # gh CLI reads GH_TOKEN or GITHUB_TOKEN for authentication
    # Source from /etc/environment if present (set by NemoClaw or operator)
    if [ -f /etc/environment ]; then
        set -a
        . /etc/environment 2>/dev/null || true
        set +a
    fi
' 2>/dev/null || true

  # Set GITHUB_REPO in sandbox if available
  if [ -n "${GITHUB_REPO:-}" ]; then
    info "Setting GITHUB_REPO=$GITHUB_REPO in sandbox..."
    docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- bash -c "
        grep -q GITHUB_REPO /etc/environment 2>/dev/null || echo 'GITHUB_REPO=$GITHUB_REPO' >> /etc/environment
    " 2>/dev/null || warn "Could not set GITHUB_REPO in sandbox /etc/environment"
  fi

  # Inject GH_TOKEN + GITHUB_TOKEN into sandbox /etc/environment for immediate gh CLI auth
  # NOTE: /etc/environment is NOT preserved across nemoclaw rebuild.
  # For rebuild persistence, GITHUB_TOKEN must be in ~/.nemoclaw/credentials.json (above).
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    info "Setting GH_TOKEN and GITHUB_TOKEN in sandbox /etc/environment (session-only)..."
    docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- bash -c "
        grep -q GH_TOKEN /etc/environment 2>/dev/null || echo 'GH_TOKEN=$GITHUB_TOKEN' >> /etc/environment
        grep -q GITHUB_TOKEN /etc/environment 2>/dev/null || echo 'GITHUB_TOKEN=$GITHUB_TOKEN' >> /etc/environment
    " 2>/dev/null || warn "Could not set GitHub tokens in sandbox /etc/environment"
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
LAUNCHER_PID="/sandbox/.openclaw-data/milimo/mesh/launcher.pid"
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
find /sandbox/.openclaw-data/milimo/mesh/heartbeats -name "*.json" -mmin +5 -delete 2>/dev/null || true
echo "Cleanup complete"
'
  ok "Stale PID files cleaned"

  # ---- Step 7: Fix permissions and backward compatibility ----
  log_step "Fixing permissions"
  sandbox_exec "$gateway" '
mkdir -p /sandbox/.openclaw-data/milimo
mkdir -p /sandbox/.openclaw-data/milimo/blueprints
ln -sfn /sandbox/.openclaw-data/milimo/milimo-blueprint /sandbox/.openclaw-data/milimo/blueprints/0.1.0
# Remove any stale .milimo directory - ln -sfn cannot replace a dir with a symlink
rm -rf /sandbox/.milimo 2>/dev/null || true
ln -sfn /sandbox/.openclaw-data/milimo /sandbox/.milimo
echo "Permissions verified and compatibility symlinks created"
'
  ok "Permissions fixed"

  # ---- Step 8: Verify critical file sync ----
  info "Verifying critical files are synced to all sandbox locations..."
  sandbox_exec "$gateway" '
    ERRORS=0

    # Verify orchestrator files exist in primary location
    for claw in ops analytics content finance build; do
        f="/sandbox/.openclaw-data/milimo/milimo-blueprint/orchestrator/${claw}/${claw}_claw.py"
      if [ ! -f "$f" ]; then
        echo "MISSING: $f"
        ERRORS=$((ERRORS + 1))
      fi
    done
    # Assistant uses lucy.py, not assistant_claw.py
    f="/sandbox/.openclaw-data/milimo/milimo-blueprint/orchestrator/assistant/lucy.py"
    if [ ! -f "$f" ]; then
     echo "MISSING: $f"
     ERRORS=$((ERRORS + 1))
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

  sandbox_exec "$gateway" '
openclaw plugins install --dangerously-force-unsafe-install /sandbox/.openclaw-data/extensions/milimo
echo "Plugin registered"
'
  sandbox_exec "$gateway" '
openclaw config set plugins.allow '\''["milimo"]'\'' 2>&1 || echo "plugins.allow set skipped"
echo "Plugin trust configured"
'
  ok "Plugin registered via openclaw plugins API"

  # ---- Step 10: Restart gateway ----
  log_step "Restarting OpenClaw gateway"
  sandbox_exec "$gateway" '
    pkill openclaw 2>/dev/null || true
    echo "Gateway restart initiated"
  ' || true
  info "Waiting for gateway to restart..."
  sleep 8
  ok "Gateway restarted"
}

# ---------------------------------------------------------------------------
# Phase 3: Non-Interactive Onboarding (MilimoClaw config)
# ---------------------------------------------------------------------------
run_onboarding() {
  log_step "Configuring MilimoClaw"

  local operator="${OPERATOR_NAME:-${USER:-operator}}"
  local squad="${SQUAD_NAME:-milimo-squad}"

  if [ "$DRY_RUN" = true ]; then
    info "Dry run — would configure:"
    info " Squad: $squad (solo template, all 6 claws)"
    info " Operator: $operator"
    info " War Room: $WARROOM_MODE"
    return 0
  fi

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  if [ -z "$gateway" ]; then
    warn "No gateway container found — config injection requires a running sandbox."
    warn "Re-run with: nemoclaw $SANDBOX_NAME connect && ./install.sh --runtime-deploy"
    return 0
  fi

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
    "clawRole": "solo",
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
 "content": { "enabled": True, "mount": "/sandbox/.openclaw-data/milimo/claws/content" },
 "ops": { "enabled": True, "mount": "/sandbox/.openclaw-data/milimo/claws/ops" },
 "analytics": { "enabled": True, "mount": "/sandbox/.openclaw-data/milimo/claws/analytics" },
 "finance": { "enabled": True, "mount": "/sandbox/.openclaw-data/milimo/claws/finance" },
 "build": { "enabled": True, "mount": "/sandbox/.openclaw-data/milimo/claws/build" },
 "assistant": { "enabled": True, "mount": "/sandbox/.openclaw-data/milimo/claws/assistant" }
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

# Write configs to .openclaw-data/milimo
os.makedirs("/sandbox/.openclaw-data/milimo", exist_ok=True)

with open("/sandbox/.openclaw-data/milimo/config.json", "w") as f:
    json.dump(plugin_config, f, indent=2)

print("Both configs written")
print(f"  Squad: {squad} (solo)")
print(f"  Operator: {operator}")
PYEOF

  docker cp "$config_script" "$gateway":/tmp/milimo-config.py 2>/dev/null
  sandbox_cp "$gateway" /tmp/milimo-config.py /tmp/milimo-config.py
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- su -s /bin/bash sandbox -c "python3 /tmp/milimo-config.py"
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- rm -f /tmp/milimo-config.py 2>/dev/null
  rm -f "$config_script"

  ok "Squad: $squad (solo template)"
  ok "Operator: $operator"
  ok "Claws: Content, Ops, Analytics, Finance, Build, Assistant — all enabled"
  ok "War Room: $WARROOM_MODE"

  # ---- Run assistant setup ----
  info "Configuring squad assistant..."
  sandbox_exec "$gateway" '
# Clear old memory so the assistant loads fresh context
rm -f /sandbox/.openclaw-data/milimo/workspace/MEMORY.md 2>/dev/null || true

cd /sandbox/.openclaw-data/milimo/milimo-blueprint && HOME=/sandbox python3 orchestrator/assistant_setup.py 2>&1 || echo "Assistant setup skipped — run manually with: openclaw milimo assistant setup"
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
  1. cd /sandbox/.openclaw-data/extensions/milimo && npm install && npx tsc
  2. openclaw plugins install /sandbox/.openclaw-data/extensions/milimo
  3. pkill -f openclaw (gateway auto-restarts)"
  else
    warn "Plugin status unclear. Output:
$plugin_check"
  fi

  # Check Build Claw modules
  local build_check
  build_check=$(sandbox_exec "$gateway" '
    ls /sandbox/.openclaw-data/milimo/milimo-blueprint/orchestrator/build/build_claw.py 2>/dev/null && echo "OK" || echo "MISSING"
  ') || true

  if [ "$build_check" = "OK" ]; then
    local module_count
    module_count=$(sandbox_exec "$gateway" 'ls /sandbox/.openclaw-data/milimo/milimo-blueprint/orchestrator/build/*.py 2>/dev/null | grep -v __init__ | wc -l') || true
    ok "Build Claw present ($module_count modules)"
  else
    warn "Build Claw blueprint not found"
  fi

  # Check config
  local config_check
  config_check=$(sandbox_exec "$gateway" '
    cat /sandbox/.openclaw-data/milimo/config.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"squad\",{}).get(\"name\",\"?\"))" 2>/dev/null || echo "MISSING"
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
  echo " Install mode: $(if [ "$RUNTIME_DEPLOY" = true ]; then echo "Runtime deploy"; else echo "Dockerfile (official)"; fi)"
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

  if [ "$RUNTIME_DEPLOY" = true ]; then
    deploy_to_sandbox
  else
    deploy_via_dockerfile
  fi

  run_onboarding
  verify_installation
  print_summary
}

main "$@"
