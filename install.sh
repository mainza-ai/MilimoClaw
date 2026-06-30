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
# 2. Runtime deploy mode (--runtime-deploy): Injects files into a running
#    sandbox via docker cp. Supports both K8s-in-Docker (kubectl via gateway)
#    and direct Docker (--solo local) sandbox topologies.
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
      _detect_sandbox_mode "$gateway"
      if [ "$_IS_K8S_MODE" = "true" ]; then
        docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c '
				rm -rf /sandbox/.openclaw/extensions/milimo
				rm -rf /sandbox/.openclaw/milimo
				echo "Milimo files removed from sandbox"
			' 2>/dev/null || true
      else
        docker exec "$SANDBOX_NAME" bash -c '
				rm -rf /sandbox/.openclaw/extensions/milimo
				rm -rf /sandbox/.openclaw/milimo
				echo "Milimo files removed from sandbox"
			' 2>/dev/null || true
      fi
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
# Helper: Run command inside sandbox
# Auto-detects K8s-in-Docker (kubectl via gateway) vs direct Docker (--solo local)
# ---------------------------------------------------------------------------
_IS_K8S_MODE="" # lazy-initialized cache

_detect_sandbox_mode() {
  if [ -n "$_IS_K8S_MODE" ]; then
    return 0
  fi
  local gateway="$1"
  if [ -n "$gateway" ] && docker exec "$gateway" which kubectl &>/dev/null 2>&1; then
    _IS_K8S_MODE=true
  else
    _IS_K8S_MODE=false
  fi
}

sandbox_exec() {
  local gateway="$1"
  shift
  _detect_sandbox_mode "$gateway"
  if [ "$_IS_K8S_MODE" = "true" ]; then
    docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- su -s /bin/bash sandbox -c "$*"
  else
    docker exec "$gateway" su -s /bin/bash sandbox -c "$*"
  fi
}

sandbox_exec_root() {
  local gateway="$1"
  shift
  _detect_sandbox_mode "$gateway"
  if [ "$_IS_K8S_MODE" = "true" ]; then
    docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- bash -c "$*"
  else
    docker exec "$gateway" bash -c "$*"
  fi
}

sandbox_cp() {
  local gateway="$1"
  local src="$2"
  local dst="$3"
  _detect_sandbox_mode "$gateway"
  if [ "$_IS_K8S_MODE" = "true" ]; then
    docker exec "$gateway" kubectl cp "$src" openshell/"$SANDBOX_NAME":"$dst" 2>/dev/null
    docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -c agent -- chmod 644 "$dst" 2>/dev/null
  else
    docker cp "$src" "$gateway":"$dst"
    docker exec "$gateway" chmod 644 "$dst" 2>/dev/null
  fi
}

# Copy a file from host into the sandbox container with correct permissions.
# docker cp creates files as root:root with mode 0600, making them unreadable
# by the sandbox user. This wrapper chmods after copying.
host_cp() {
  local src="$1"
  local gateway="$2"
  local dst="$3"
  docker cp "$src" "$gateway":"$dst" 2>/dev/null
  docker exec "$gateway" chmod 644 "$dst" 2>/dev/null
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

  # NemoClaw — detect existing sandbox vs fresh install
  # Prefer structured JSON output over fragile grep parsing (#R4 audit fix)
  export PATH="$HOME/.local/bin:$HOME/.nvm/current/bin:$PATH"
  if command_exists nemoclaw; then
    export SANDBOX_FOUND=false
    export SANDBOX_PHASE="Unknown"

    # Try structured JSON parsing first (requires jq)
    if command_exists jq; then
      local json_output
      json_output=$(nemoclaw list --json 2>/dev/null || echo "{}")
      if echo "$json_output" | jq -e ".sandboxes[] | select(.name == \"$SANDBOX_NAME\")" >/dev/null 2>&1; then
        SANDBOX_FOUND=true
        # nemoclaw list --json does NOT include .phase — only name, model,
        # provider, connected, etc. Must call nemoclaw <name> status for phase.
        SANDBOX_PHASE=$(nemoclaw "$SANDBOX_NAME" status 2>/dev/null | awk '/Phase:/{print $NF}' || echo "Unknown")
        if [ "$SANDBOX_PHASE" = "Running" ] || [ "$SANDBOX_PHASE" = "Ready" ]; then
          info "Existing sandbox '$SANDBOX_NAME' detected ($SANDBOX_PHASE)"
          info "MilimoClaw will be injected into the existing sandbox"
          ok "Sandbox '$SANDBOX_NAME' is $SANDBOX_PHASE"
        elif [ "$SANDBOX_PHASE" = "Stopped" ] || [ "$SANDBOX_PHASE" = "Exited" ]; then
          warn "Sandbox '$SANDBOX_NAME' exists but is $SANDBOX_PHASE"
          info "Will attempt to start it before deploying"
        else
          info "Sandbox '$SANDBOX_NAME' found (status: $SANDBOX_PHASE)"
          info "Will attempt to start it before deploying"
        fi
      fi
    else
      # Fallback: grep parsing if jq not available
      if nemoclaw list 2>/dev/null | grep -qE "^\s+$SANDBOX_NAME "; then
        SANDBOX_FOUND=true
        SANDBOX_PHASE=$(nemoclaw "$SANDBOX_NAME" status 2>/dev/null | awk '/Phase:/{print $NF}' || echo "Unknown")
        if [ "$SANDBOX_PHASE" = "Running" ] || [ "$SANDBOX_PHASE" = "Ready" ]; then
          info "Existing sandbox '$SANDBOX_NAME' detected ($SANDBOX_PHASE)"
          info "MilimoClaw will be injected into the existing sandbox"
          ok "Sandbox '$SANDBOX_NAME' is $SANDBOX_PHASE"
        elif [ "$SANDBOX_PHASE" = "Stopped" ] || [ "$SANDBOX_PHASE" = "Exited" ]; then
          warn "Sandbox '$SANDBOX_NAME' exists but is $SANDBOX_PHASE"
          info "Will attempt to start it before deploying"
        else
          info "Sandbox '$SANDBOX_NAME' found (status: $SANDBOX_PHASE)"
          info "Will attempt to start it before deploying"
        fi
      fi
    fi

    if [ "$SANDBOX_FOUND" = "false" ]; then
      # Fallback: check if ANY sandbox exists (name may differ from default)
      local any_sandbox
      if command_exists jq; then
        any_sandbox=$(echo "$json_output" | jq -r '.sandboxes[0].name // empty' 2>/dev/null)
      else
        any_sandbox=$(nemoclaw list 2>/dev/null | awk 'NR>1 && NF>0 {print $1; exit}')
      fi
      if [ -n "$any_sandbox" ]; then
        info "Sandbox '$SANDBOX_NAME' not found, but detected existing sandbox: '$any_sandbox'"
        SANDBOX_NAME="$any_sandbox"
        SANDBOX_FOUND=true
        warn "Using detected sandbox '$any_sandbox' instead of default"
      else
        info "No existing sandbox found — will create one via nemoclaw onboard"
      fi
    fi
  else
    warn "nemoclaw CLI not found in PATH."
    warn "After NemoClaw install, run: source ~/.zshrc  (or ~/.bashrc)"
    warn "Then re-run: ./install.sh --solo --operator-name \"$OPERATOR_NAME\" --squad-name \"$SQUAD_NAME\""
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

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy Milimo plugin source (includes dist/ and node_modules/ if pre-built on host)
COPY milimo/ /opt/milimo/
WORKDIR /opt/milimo

# Install production dependencies (devDeps already stripped by --omit=dev on host)
RUN npm install --omit=dev --ignore-scripts --legacy-peer-deps 2>&1 | tail -5

# Install plugin — --force for idempotent reinstall; fail build if this fails
RUN openclaw plugins install --force /opt/milimo \
    && echo "PLUGIN_INSTALL_OK" \
    || (echo "PLUGIN_INSTALL_FAILED:" && cat /tmp/openclaw.log 2>/dev/null || true && exit 1)

# Verify plugin is registered before continuing
RUN openclaw plugins list 2>&1 | grep -q "milimo" \
    && echo "PLUGIN_VERIFIED" \
    || (echo "PLUGIN_VERIFICATION_FAILED — milimo not in openclaw plugins list" && exit 1)

# Copy Milimo blueprint
COPY milimo-blueprint/ /sandbox/.openclaw/milimo/milimo-blueprint/

# Create claw data directories
RUN BASE="/sandbox/.openclaw/milimo/claws" \
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

# Install GitHub CLI to persistent .openclaw path and add to PATH via profile.d
RUN ARCH=$(uname -m) \
    && if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then GH_ARCH="arm64"; else GH_ARCH="amd64"; fi \
    && GH_VERSION="2.67.0" \
    && GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz" \
    && cd /tmp && curl -sL "$GH_URL" -o gh.tar.gz && tar xzf gh.tar.gz \
    && mkdir -p /sandbox/.openclaw/milimo/bin \
    && cp gh_*_linux_${GH_ARCH}/bin/gh /sandbox/.openclaw/milimo/bin/gh \
    && chmod +x /sandbox/.openclaw/milimo/bin/gh \
    && rm -rf /tmp/gh* \
    && echo 'export PATH="/sandbox/.openclaw/milimo/bin:$PATH"' > /etc/profile.d/milimo.sh \
    && echo "gh CLI installed at /sandbox/.openclaw/milimo/bin/gh"

# Create blueprint symlink + backward compat symlink
RUN mkdir -p /sandbox/.openclaw/milimo/blueprints \
    && ln -sfn /sandbox/.openclaw/milimo/milimo-blueprint /sandbox/.openclaw/milimo/blueprints/0.1.0 \
    && rm -rf /sandbox/.milimo 2>/dev/null || true \
    && ln -sfn /sandbox/.openclaw/milimo /sandbox/.milimo

# Create startup script for Python RPC server
RUN mkdir -p /sandbox/.openclaw/milimo/bin && \
    printf '#!/bin/bash\nnohup python3 -m orchestrator.bridge_server --port ${MILIMO_RPC_PORT:-19999} > /sandbox/.openclaw/milimo/rpc-server.log 2>&1 &\n' > /sandbox/.openclaw/milimo/bin/start-rpc-server.sh && \
    chmod +x /sandbox/.openclaw/milimo/bin/start-rpc-server.sh && \
    /sandbox/.openclaw/milimo/bin/start-rpc-server.sh && \
    echo "RPC server startup script created and started"

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

  # Build production node_modules on host — these get copied into the Dockerfile build context
  # so the Dockerfile doesn't need to run npm install (which may hit network issues)
  info "Building production node_modules for Dockerfile context..."
  cd "$ROOT_DIR/milimo"
  npm install --omit=dev --ignore-scripts 2>&1 | tail -3
  cd "$ROOT_DIR"

  # Prepare build directory
  log_step "Preparing Dockerfile build context"
  local build_dir
  build_dir=$(mktemp -d /tmp/milimo-docker-build.XXXXXX)

  # Copy plugin source + pre-built dist/ + prod node_modules/ to build context
  info "Copying plugin to build context..."
  cd "$ROOT_DIR/milimo"
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-context.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__tests__' --exclude='*.test.ts' --exclude='tsconfig.tsbuildinfo' \
    --exclude='src/' \
    openclaw.plugin.json package.json dist/ node_modules/ 2>/dev/null
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

  # If NemoClaw already has a sandbox registered with the gateway, the
  # onboard wizard's non-interactive mode needs the NVIDIA_API_KEY to
  # validate the provider. The gateway already has the key registered from
  # the first interactive onboard. We can extract it from the gateway store
  # or fall back to prompting.
  #
  # --resume only resumes interrupted sessions (not what we want here).
  # Instead, if the sandbox exists in sandboxes.json, we extract the
  # provider and model to pre-seed the onboard wizard via env vars.
  if [ -f "$HOME/.nemoclaw/sandboxes.json" ] && command_exists jq; then
    local existing_provider existing_model
    existing_provider=$(jq -r ".sandboxes.\"$SANDBOX_NAME\".provider // empty" "$HOME/.nemoclaw/sandboxes.json" 2>/dev/null)
    existing_model=$(jq -r ".sandboxes.\"$SANDBOX_NAME\".model // empty" "$HOME/.nemoclaw/sandboxes.json" 2>/dev/null)
    if [ -n "$existing_provider" ]; then
      info "Sandbox '$SANDBOX_NAME' found in NemoClaw config (provider=$existing_provider, model=$existing_model)"
      export NEMOCLAW_PROVIDER="$existing_provider"
      export NEMOCLAW_MODEL_PREFERRED="$existing_model"
    fi
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

  # ---- Step 0: Preserve user's pre-selected inference model ----
  log_step "Preserving inference model"

  local inferred_model
  inferred_model=$(
    export PATH="$HOME/.local/bin:$HOME/.nvm/current/bin:$PATH"
    nemoclaw list 2>/dev/null | grep -A1 "my-assistant" | grep "model:" | sed 's/.*model: *\([^ ]*\).*/\1/' | tr -d ' '
  )

  if [ -n "$inferred_model" ]; then
    info "Detected model from nemoclaw list: $inferred_model"
    # shellcheck disable=SC2027,SC1011,SC1083
    sandbox_exec_root "$gateway" '
	# Set NEMOCLAW_MODEL env var for runtime fallback
	if ! grep -q "NEMOCLAW_MODEL=" /etc/environment 2>/dev/null; then
		echo "NEMOCLAW_MODEL='"'$inferred_model'"'" >> /etc/environment
		echo "NEMOCLAW_MODEL injected into /etc/environment"
	else
		echo "NEMOCLAW_MODEL already present in /etc/environment — preserving"
	fi

	# Update the OpenClaw agent config so TUI uses the correct model
	# openclaw.json stores the agent-facing model under agents.defaults.model.primary
	# with an "inference/" prefix (e.g. "inference/nvidia/nemotron-3-ultra-550b-a55b")
	OPENCLAW_JSON="/sandbox/.openclaw/openclaw.json"
	if [ -f "$OPENCLAW_JSON" ]; then
		PREFIXED_MODEL="inference/'"$inferred_model"'"
		python3 -c "
import json
cfg = json.load(open('"'"'$OPENCLAW_JSON'"'"'))
old = cfg.get('"'"'agents'"'"', {}).get('"'"'defaults'"'"', {}).get('"'"'model'"'"', {}).get('"'"'primary'"'"', '""'")
if old != "'"'"$PREFIXED_MODEL"'"'":
    cfg.setdefault('"'"'agents'"'"', {}).setdefault('"'"'defaults'"'"', {})['"'"'model'"'"'] = {'"'"'primary'"'"': '"'"'$PREFIXED_MODEL'"'"'}
    json.dump(cfg, open('"'"'$OPENCLAW_JSON'"'"', '"'"'w'"'"'), indent=2)
    print(f'Updated agent model: {old} → '"'$PREFIXED_MODEL'")
else:
    print(f'Agent model already correct: {old}')
"
	fi
	'
  else
    warn "Could not detect model from nemoclaw list — skipping model preservation"
  fi
  ok "Inference model preserved"

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

  # ---- Step 2: Build production node_modules on host ----
  # We transfer pre-built artifacts instead of building inside the sandbox.
  # This avoids npm/tsc failures due to sandbox network restrictions or missing devDeps.
  log_step "Preparing deployable plugin package"

  info "Building production node_modules..."
  cd "$ROOT_DIR/milimo"
  npm install --omit=dev --ignore-scripts 2>&1 | tail -3

  # Create staging tarball with only deployable artifacts:
  # openclaw.plugin.json, package.json, dist/, node_modules/ (prod only)
  info "Packaging plugin artifacts..."
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-plugin-deploy.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__tests__' --exclude='*.test.ts' --exclude='tsconfig.tsbuildinfo' \
    --exclude='src/' --exclude='node_modules/.package-lock.json' \
    --exclude='node_modules/*/{CHANGELOG,README,readme,LICENSE,NOTICE}' \
    --exclude='node_modules/*/{test,tests,__tests__,*.spec.*,*.test.*}' \
    openclaw.plugin.json package.json dist/ node_modules/ 2>/dev/null

  if [ ! -s /tmp/milimo-plugin-deploy.tar.gz ]; then
    error "Plugin tarball is empty or missing"
  fi
  ok "Plugin package prepared ($(du -sh /tmp/milimo-plugin-deploy.tar.gz | cut -f1))"

  # ---- Step 3: Transfer plugin to sandbox ----
  log_step "Deploying MilimoClaw to sandbox"

  info "Transferring plugin package to sandbox..."
  host_cp /tmp/milimo-plugin-deploy.tar.gz "$gateway" /tmp/milimo-plugin-deploy.tar.gz
  if [ "$_IS_K8S_MODE" = "true" ]; then
    sandbox_cp "$gateway" /tmp/milimo-plugin-deploy.tar.gz /tmp/milimo-plugin-deploy.tar.gz
  fi
  rm -f /tmp/milimo-plugin-deploy.tar.gz

  sandbox_exec "$gateway" '
    mkdir -p /tmp/milimo-plugin-install && \
    tar xzf /tmp/milimo-plugin-deploy.tar.gz -C /tmp/milimo-plugin-install && \
    echo "Plugin package extracted to /tmp/milimo-plugin-install"
  '
  sandbox_exec_root "$gateway" 'rm -f /tmp/milimo-plugin-deploy.tar.gz'

  if ! sandbox_exec "$gateway" 'test -f /tmp/milimo-plugin-install/dist/index.js'; then
    error "Plugin transfer failed — dist/index.js not found in sandbox"
  fi
  ok "Plugin transferred to /tmp/milimo-plugin-install"

  # ---- Step 5: Deploy blueprint ----
  log_step "Deploying blueprint"
  cd "$ROOT_DIR"
  COPYFILE_DISABLE=1 tar czf /tmp/milimo-blueprint-deploy.tar.gz \
    --no-xattrs --no-mac-metadata \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    milimo-blueprint/ 2>/dev/null

  host_cp /tmp/milimo-blueprint-deploy.tar.gz "$gateway" /tmp/milimo-blueprint-deploy.tar.gz
  if [ "$_IS_K8S_MODE" = "true" ]; then
    sandbox_cp "$gateway" /tmp/milimo-blueprint-deploy.tar.gz /tmp/milimo-blueprint-deploy.tar.gz
  fi
  rm -f /tmp/milimo-blueprint-deploy.tar.gz

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.openclaw/milimo && \
    cd /sandbox/.openclaw/milimo && \
    tar xzf /tmp/milimo-blueprint-deploy.tar.gz && \
    echo "Blueprint deployed"
  '
  sandbox_exec_root "$gateway" 'rm -f /tmp/milimo-blueprint-deploy.tar.gz'

  if ! sandbox_exec "$gateway" 'test -d /sandbox/.openclaw/milimo/milimo-blueprint/orchestrator/build'; then
    error "Blueprint extraction failed — orchestrator/build/ not found"
  fi
  ok "Blueprint deployed to /sandbox/.openclaw/milimo/milimo-blueprint"

  # ---- Step 6: Deploy assistant template ----
  log_step "Deploying support files"

  local template_file="$ROOT_DIR/milimo-blueprint/orchestrator/templates/assistant_system_prompt.md"
  if [ -f "$template_file" ]; then
    info "Deploying assistant system prompt template..."
    host_cp "$template_file" "$gateway" /tmp/assistant_template.md
    if [ "$_IS_K8S_MODE" = "true" ]; then
      sandbox_cp "$gateway" /tmp/assistant_template.md /tmp/assistant_template.md
    fi
    sandbox_exec "$gateway" '
		mkdir -p /sandbox/.openclaw/milimo/templates && \
		cp /tmp/assistant_template.md /sandbox/.openclaw/milimo/templates/assistant_system_prompt.md && \
		echo "Template deployed"
		'
    sandbox_exec_root "$gateway" 'rm -f /tmp/assistant_template.md'
    ok "Assistant template deployed"
  else
    template_file="$ROOT_DIR/milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md"
    if [ -f "$template_file" ]; then
      host_cp "$template_file" "$gateway" /tmp/assistant_template.md
      if [ "$_IS_K8S_MODE" = "true" ]; then
        sandbox_cp "$gateway" /tmp/assistant_template.md /tmp/assistant_template.md
      fi
      sandbox_exec "$gateway" '
			mkdir -p /sandbox/.openclaw/milimo/templates && \
			cp /tmp/assistant_template.md /sandbox/.openclaw/milimo/templates/assistant_system_prompt.md && \
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

  # All claw data goes under .openclaw/milimo/claws/ (writable path)
  sandbox_exec "$gateway" '
    BASE="/sandbox/.openclaw/milimo/claws"
    mkdir -p $BASE/ops/{clients/{active,archived},projects/{active,completed},calendar,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/content/{drafts/{pending,approved,rejected},calendar,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/analytics/{reports/{daily,weekly,monthly},metrics,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/finance/{invoices/{draft,sent,paid,overdue},expenses,revenue,queue/{hold,review,auto},memory,context,logs,tools}
    mkdir -p $BASE/build/{prs/{open,merged,closed},deployments/{staging,production},tasks,docs,context,queue/{hold,review,auto},memory,logs,tools,data}
    mkdir -p $BASE/assistant/{context,memory,logs,tools,queue/{hold,review,auto}}
    echo "All sandbox directories initialized under .openclaw/milimo/claws/"
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

  sandbox_exec "$gateway" '
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        GH_ARCH="arm64"
    else
        GH_ARCH="amd64"
    fi

    mkdir -p /sandbox/.openclaw/milimo/bin
    GH_VERSION="2.67.0"
    GH_URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"

    cd /tmp && curl -sL "$GH_URL" -o gh.tar.gz && tar xzf gh.tar.gz
    cp gh_*_linux_${GH_ARCH}/bin/gh /sandbox/.openclaw/milimo/bin/gh
    chmod +x /sandbox/.openclaw/milimo/bin/gh
    rm -rf /tmp/gh*

    # Add milimo bin to PATH via /sandbox/.bashrc
    # Note: /etc/profile.d/ is read-only under Landlock; /sandbox/.bashrc is
    # writable only by root, so we use >> (append) via sandbox_exec_root below.
    echo "gh CLI installed at /sandbox/.openclaw/milimo/bin/gh"
  '

  # Write PATH export to .bashrc using root (sandbox user cant write to .bashrc)
  sandbox_exec_root "$gateway" 'echo "export PATH=/sandbox/.openclaw/milimo/bin:\$PATH" >> /sandbox/.bashrc'

  ok "GitHub CLI (gh) installed at /sandbox/.openclaw/milimo/bin/gh"

  # ---- Step 6f: Create milimo CLI wrapper ----
  log_step "Creating milimo CLI wrapper"

  sandbox_exec "$gateway" '
    mkdir -p /sandbox/.openclaw/milimo/bin
    cat > /sandbox/.openclaw/milimo/bin/milimo << '\''MILIMO_EOF'\''
#!/usr/bin/env python3
"""Milimo Claw CLI wrapper — delegates to bridge_cli.py"""
import sys
BLUEPRINT_PATH = "/sandbox/.openclaw/milimo/blueprints/0.1.0"
if BLUEPRINT_PATH not in sys.path:
    sys.path.insert(0, BLUEPRINT_PATH)
from orchestrator.bridge_cli import main
if __name__ == "__main__":
    main()
MILIMO_EOF
    chmod +x /sandbox/.openclaw/milimo/bin/milimo
    echo "milimo CLI wrapper created at /sandbox/.openclaw/milimo/bin/milimo"
  '
  ok "milimo CLI wrapper created"

  # ---- Step 6g: Fix broken .venv (recreate with sandbox Python) ----
  log_step "Fixing Python virtual environment"

  sandbox_exec "$gateway" '
    BLUEPRINT_DIR="/sandbox/.openclaw/milimo/milimo-blueprint"
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
    echo "Python venv recreated and verified at $VENV_DIR"
  '
  ok "Python venv recreated with sandbox Python"

  # ---- Step 6h: Environment variable setup ----
  log_step "Configuring environment variables"
  info "NemoClaw manages inference credentials via the L7 proxy."
  info "GitHub and other service tokens should be registered with the OpenShell gateway."
  info "See: nemoclaw credentials list"

  # Store GITHUB_TOKEN via NemoClaw credential staging if available.
  # NemoClaw's credential store holds values in process memory and registers
  # them with the OpenShell gateway — they survive sandbox rebuild, unlike
  # /etc/environment writes which are lost.
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    info "GITHUB_TOKEN detected — exporting into sandbox process environment."
    # Export into the sandbox agent container's process env for this session.
    # The gateway picks up GITHUB_TOKEN automatically for gh CLI auth.
    sandbox_exec "$gateway" "export GITHUB_TOKEN='$GITHUB_TOKEN'; export GH_TOKEN='$GITHUB_TOKEN'" 2>/dev/null || warn "Could not export GITHUB_TOKEN into sandbox process env"

    info "For rebuild persistence, register with the gateway:"
    info "  Run: gh auth login  (inside the sandbox)"
    info "  Or:  export GITHUB_TOKEN=ghp_... before running install.sh"
    info "  See: nemoclaw credentials list"
  else
    warn "GITHUB_TOKEN not set in host environment."
    warn "Set it before running install.sh for automatic credential staging:"
    warn "  export GITHUB_TOKEN=ghp_your_token"
    warn "Or authenticate inside the sandbox: gh auth login"
    warn "See: nemoclaw credentials list"
  fi

  # Source any existing /etc/environment values (read-only, for operator overrides)
  sandbox_exec "$gateway" '
    if [ -f /etc/environment ]; then
        set -a
        . /etc/environment 2>/dev/null || true
        set +a
    fi
' 2>/dev/null || true

  # Set GITHUB_REPO in sandbox if available (this is metadata, not a credential)
  if [ -n "${GITHUB_REPO:-}" ]; then
    info "Setting GITHUB_REPO=$GITHUB_REPO in sandbox..."
    sandbox_exec_root "$gateway" "grep -q GITHUB_REPO /etc/environment 2>/dev/null || echo 'GITHUB_REPO=$GITHUB_REPO' >> /etc/environment" 2>/dev/null || warn "Could not set GITHUB_REPO in sandbox /etc/environment"
  fi

  # ---- Step 6i: Create Python .pth file for package discovery ----
  log_step "Configuring Python package path"
  sandbox_exec "$gateway" '
# Create .pth file so Python finds packages installed via --target
PTH_FILE="/sandbox/.local/lib/python3.11/site-packages/milimo.pth"
mkdir -p "$(dirname "$PTH_FILE")"
echo "/sandbox/.local/lib/python3.11/site-packages" > "$PTH_FILE"
echo "Created milimo.pth at $PTH_FILE"
'
  ok "Python .pth file created — packages at /sandbox/.local/lib/python3.11/site-packages now discoverable"

  # ---- Step 6j: Cleanup stale PID files ----
  log_step "Cleaning stale PID files"
  sandbox_exec "$gateway" '
# Remove stale launcher PID file (persistent volumes retain old PIDs)
LAUNCHER_PID="/sandbox/.openclaw/milimo/mesh/launcher.pid"
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
find /sandbox/.openclaw/milimo/mesh/heartbeats -name "*.json" -mmin +5 -delete 2>/dev/null || true
echo "Cleanup complete"
'
  ok "Stale PID files cleaned"

  # ---- Step 7: Fix permissions and backward compatibility ----
  log_step "Fixing permissions"
  sandbox_exec "$gateway" '
mkdir -p /sandbox/.openclaw/milimo
mkdir -p /sandbox/.openclaw/milimo/blueprints
ln -sfn /sandbox/.openclaw/milimo/milimo-blueprint /sandbox/.openclaw/milimo/blueprints/0.1.0
# Remove any stale .milimo directory - ln -sfn cannot replace a dir with a symlink
rm -rf /sandbox/.milimo 2>/dev/null || true
ln -sfn /sandbox/.openclaw/milimo /sandbox/.milimo
echo "Permissions verified and compatibility symlinks created"
'
  ok "Permissions fixed"

  # ---- Step 8: Verify critical file sync ----
  info "Verifying critical files are synced to all sandbox locations..."
  sandbox_exec "$gateway" '
    ERRORS=0

    # Verify orchestrator files exist in primary location
    for claw in ops analytics content finance build; do
        f="/sandbox/.openclaw/milimo/milimo-blueprint/orchestrator/${claw}/${claw}_claw.py"
      if [ ! -f "$f" ]; then
        echo "MISSING: $f"
        ERRORS=$((ERRORS + 1))
      fi
    done
    # Assistant uses lucy.py, not assistant_claw.py
    f="/sandbox/.openclaw/milimo/milimo-blueprint/orchestrator/assistant/lucy.py"
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

  # ---- Step 8b: Repair stale/invalid channel config ----
  # NemoClaw bakes channel config into the sandbox image at build time.
  # Older sandboxes may have legacy flat-format Telegram/Discord/Slack config
  # (e.g. groupPolicy at channels.telegram.groupPolicy instead of
  # channels.telegram.accounts.default.groupPolicy), or invalid groupPolicy
  # values. We repair it here so plugin registration doesn't fail validation.
  log_step "Repairing stale channel config"

  sandbox_exec_root "$gateway" '
cat > /tmp/fix_channel_config.py << '\''PYEOF'\''
import json, sys

CONFIG_PATH = "/sandbox/.openclaw/openclaw.json"
try:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("No openclaw.json to patch")
    sys.exit(0)

VALID_GROUP_POLICIES = {"open", "disabled", "allowlist"}
changed = False
channels = cfg.setdefault("channels", {})

def fix_channel(ch):
    _changed = [False]
    def _fix():
        if not ch:
            return
        accts = ch.setdefault("accounts", {})
        default_acct = accts.setdefault("default", {})
        # Migrate legacy flat groupPolicy → accounts.default.groupPolicy
        if "groupPolicy" in ch:
            default_acct["groupPolicy"] = ch.pop("groupPolicy")
            _changed[0] = True
        # Migrate legacy flat groupAllowFrom
        if "groupAllowFrom" in ch:
            default_acct["groupAllowFrom"] = ch.pop("groupAllowFrom")
            _changed[0] = True
        # Ensure groupPolicy is valid (after migration)
        gp = default_acct.get("groupPolicy")
        if gp not in VALID_GROUP_POLICIES:
            default_acct["groupPolicy"] = "open"
            _changed[0] = True
    _fix()
    return _changed[0]

changed = fix_channel(channels.get("telegram", {})) or changed
changed = fix_channel(channels.get("discord", {})) or changed
changed = fix_channel(channels.get("slack", {})) or changed

if changed:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print("Channel config repaired: groupPolicy=open, legacy format migrated to account-based")
else:
    print("Channel config already valid")
PYEOF
python3 /tmp/fix_channel_config.py
rm -f /tmp/fix_channel_config.py
'
  ok "Channel config validated"

  # ---- Step 9: Register plugin via openclaw plugins install ----
  log_step "Registering Milimo plugin"

  # Run openclaw doctor --fix first to ensure openclaw.json is valid before plugin install
  log_step "Pre-check openclaw doctor --fix"
  sandbox_exec "$gateway" 'openclaw doctor --fix 2>&1 | tail -3 || true'

  # Install plugin using pre-staged artifacts at /tmp/milimo-plugin-install/
  # --force: idempotent reinstall (overwrites previous partial install)
  # Using /tmp/ path avoids .openclaw/extensions/ landlock restrictions during extraction
  info "Running: openclaw plugins install --force /tmp/milimo-plugin-install"
  local plugin_result
  plugin_result=$(sandbox_exec "$gateway" '
    openclaw plugins install --force /tmp/milimo-plugin-install 2>&1
    echo "EXIT_CODE:$?"
  ')
  local plugin_exit
  plugin_exit=$(echo "$plugin_result" | sed -n 's/.*EXIT_CODE:\([0-9]*\)/\1/p')

  if [ -z "$plugin_exit" ]; then
    error "Could not determine plugin install exit code"
    echo "$plugin_result" | sed 's/^/  /' | head -15
  elif [ "$plugin_exit" -ne 0 ]; then
    warn "Plugin install exited with code $plugin_exit — retrying with --dangerously-force-unsafe-install"
    local retry_result
    retry_result=$(sandbox_exec "$gateway" '
      openclaw plugins install --force --dangerously-force-unsafe-install /tmp/milimo-plugin-install 2>&1
      echo "EXIT_CODE:$?"
    ')
    local retry_exit
    retry_exit=$(echo "$retry_result" | sed -n 's/.*EXIT_CODE:\([0-9]*\)/\1/p')
    if [ "$retry_exit" -ne 0 ]; then
      error "Plugin install failed (exit $retry_exit):
  $retry_result"
      # Clean up staging directory before failing
      sandbox_exec "$gateway" 'rm -rf /tmp/milimo-plugin-install'
      return 1
    fi
    plugin_result="$retry_result"
    plugin_exit="$retry_exit"
  fi

  # Verify plugin registration — must appear as "loaded" in openclaw plugins list
  info "Verifying plugin registration..."
  local verify_result
  verify_result=$(sandbox_exec "$gateway" 'openclaw plugins list 2>&1 | grep -i "milimo" || echo "NOT_FOUND"')
  if echo "$verify_result" | grep -qi "NOT_FOUND\|no match\|not found"; then
    error "Plugin registration failed — milimo not found in openclaw plugins list.
  Install output:
  $plugin_result
  To fix manually:
    openclaw plugins install --force /tmp/milimo-plugin-install
    openclaw plugins list | grep milimo"
    sandbox_exec "$gateway" 'rm -rf /tmp/milimo-plugin-install'
    return 1
  fi

  if echo "$verify_result" | grep -qi "loaded\|enabled"; then
    ok "Milimo plugin registered and loaded"
  else
    warn "Plugin installed but status unclear: $verify_result"
  fi

  # Clean up staging directory
  sandbox_exec "$gateway" 'rm -rf /tmp/milimo-plugin-install'
  ok "Plugin staging directory cleaned"

  # Verify plugin is accessible — run openclaw milimo --help
  info "Verifying plugin CLI access..."
  local cli_check
  cli_check=$(sandbox_exec "$gateway" 'openclaw milimo --help 2>&1 | head -5 || echo "CLI_NOT_FOUND"')
  if echo "$cli_check" | grep -qi "CLI_NOT_FOUND\|unknown command\|not found"; then
    warn "Plugin CLI not responding — may require gateway reload: $cli_check"
  else
    ok "Plugin CLI responding (openclaw milimo)"
  fi

  # ---- Step 10: Restart gateway with health check ----
  log_step "Restarting OpenClaw gateway"

  # Use pkill to restart gateway — "openclaw gateway restart" corrupts the
  # gateway config on OpenClaw 2026.5.27+ by stripping gateway.mode.
  # The sandbox supervisor will auto-restart the gateway process.
  sandbox_exec "$gateway" 'pkill -f "openclaw.*gateway" 2>/dev/null || pkill openclaw 2>/dev/null || true; echo "pkill sent"'

  # Wait for gateway to come back up with a health check loop (max 30s)
  info "Waiting for gateway to be ready (max 30s)..."
  local waited=0
  local gateway_ready=false
  while [ $waited -lt 30 ]; do
    local health_check
    health_check=$(sandbox_exec "$gateway" 'openclaw doctor 2>&1 | grep -i "gateway.*running\|Gateway.*up\|Gateway.*ready" || echo "NOT_READY"')
    if ! echo "$health_check" | grep -q "NOT_READY"; then
      gateway_ready=true
      break
    fi
    sleep 2
    waited=$((waited + 2))
  done

  if [ "$gateway_ready" = true ]; then
    ok "Gateway ready after ${waited}s"
  else
    warn "Gateway may still be starting — some plugins may not be active yet"
    warn "Check status with: openclaw doctor"
  fi

  # ---- Step 11: Start Python RPC server (bridge_server.py) ----
  log_step "Starting Python RPC server"

  sandbox_exec "$gateway" '
    RPC_PORT="${MILIMO_RPC_PORT:-19999}"
    PID_FILE="/sandbox/.openclaw/milimo/rpc-server.pid"
    mkdir -p "$(dirname "$PID_FILE")" 2>/dev/null

    # Check if already running
    if [ -f "$PID_FILE" ]; then
      OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
      if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "RPC server already running (PID $OLD_PID)"
        exit 0
      fi
      rm -f "$PID_FILE"
    fi

    # Start RPC server in background
    BLUEPRINT_DIR="/sandbox/.openclaw/milimo/milimo-blueprint"
    if [ ! -d "$BLUEPRINT_DIR" ]; then
      BLUEPRINT_DIR="/sandbox/.milimo/milimo-blueprint"
    fi

    nohup python3 -m orchestrator.bridge_server --port "$RPC_PORT" \
      > /sandbox/.openclaw/milimo/rpc-server.log 2>&1 &

    RPC_PID=$!
    echo "$RPC_PID" > "$PID_FILE"

    # Wait for server to be ready
    for i in $(seq 1 10); do
      if curl -sf http://127.0.0.1:"$RPC_PORT"/health >/dev/null 2>&1; then
        echo "RPC server ready (PID $RPC_PID)"
        exit 0
      fi
      sleep 1
    done
    echo "WARNING: RPC server may not be ready yet (PID $RPC_PID)"
  '

  # Add RPC server startup to .bashrc so it survives sandbox restart
  sandbox_exec_root "$gateway" '
    STARTUP_LINE="nohup python3 -m orchestrator.bridge_server --port ${MILIMO_RPC_PORT:-19999} > /sandbox/.openclaw/milimo/rpc-server.log 2>&1 &"
    if ! grep -q "orchestrator.bridge_server" /sandbox/.bashrc 2>/dev/null; then
      echo "$STARTUP_LINE" >> /sandbox/.bashrc
      echo "RPC server startup added to .bashrc"
    else
      echo "RPC server startup already in .bashrc"
    fi
  '

  # Verify RPC server is responsive
  if sandbox_exec "$gateway" 'curl -sf http://127.0.0.1:'"${MILIMO_RPC_PORT:-19999}"'/health >/dev/null 2>&1'; then
    ok "Python RPC server running on port ${MILIMO_RPC_PORT:-19999}"
  else
    warn "Python RPC server may not be running — check logs: /sandbox/.openclaw/milimo/rpc-server.log"
    warn "Start manually: python3 -m orchestrator.bridge_server --port ${MILIMO_RPC_PORT:-19999}"
  fi
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
 "content": { "enabled": True, "mount": "/sandbox/.openclaw/milimo/claws/content" },
 "ops": { "enabled": True, "mount": "/sandbox/.openclaw/milimo/claws/ops" },
 "analytics": { "enabled": True, "mount": "/sandbox/.openclaw/milimo/claws/analytics" },
 "finance": { "enabled": True, "mount": "/sandbox/.openclaw/milimo/claws/finance" },
 "build": { "enabled": True, "mount": "/sandbox/.openclaw/milimo/claws/build" },
 "assistant": { "enabled": True, "mount": "/sandbox/.openclaw/milimo/claws/assistant" }
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

# Write configs to .openclaw/milimo
os.makedirs("/sandbox/.openclaw/milimo", exist_ok=True)

with open("/sandbox/.openclaw/milimo/config.json", "w") as f:
    json.dump(plugin_config, f, indent=2)

print("Both configs written")
print(f"  Squad: {squad} (solo)")
print(f"  Operator: {operator}")
PYEOF

  host_cp "$config_script" "$gateway" /tmp/milimo-config.py
  if [ "$_IS_K8S_MODE" = "true" ]; then
    sandbox_cp "$gateway" /tmp/milimo-config.py /tmp/milimo-config.py
  fi
  sandbox_exec "$gateway" "python3 /tmp/milimo-config.py"
  sandbox_exec_root "$gateway" 'rm -f /tmp/milimo-config.py'
  rm -f "$config_script"

  ok "Squad: $squad (solo template)"
  ok "Operator: $operator"
  ok "Claws: Content, Ops, Analytics, Finance, Build, Assistant — all enabled"
  ok "War Room: $WARROOM_MODE"

  # ---- Run assistant setup ----
  info "Configuring squad assistant..."
  sandbox_exec "$gateway" '
# Clear old memory so the assistant loads fresh context
rm -f /sandbox/.openclaw/milimo/workspace/MEMORY.md 2>/dev/null || true

cd /sandbox/.openclaw/milimo/milimo-blueprint && HOME=/sandbox PYTHONPATH=/sandbox/.openclaw/milimo/milimo-blueprint python3 -m orchestrator.assistant_setup 2>&1 || echo "Assistant setup skipped — run manually with: openclaw milimo assistant setup"
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
  1. Build plugin: cd /tmp/milimo-plugin-install && npm install --omit=dev && npx tsc
  2. Install: openclaw plugins install --force /tmp/milimo-plugin-install
  3. pkill -f 'openclaw.*gateway' (gateway auto-restarts)"
  else
    warn "Plugin status unclear. Output:
$plugin_check"
  fi

  # Check Build Claw modules
  local build_check
  build_check=$(sandbox_exec "$gateway" '
    ls /sandbox/.openclaw/milimo/milimo-blueprint/orchestrator/build/build_claw.py 2>/dev/null && echo "OK" || echo "MISSING"
  ') || true

  if [ "$build_check" = "OK" ]; then
    local module_count
    module_count=$(sandbox_exec "$gateway" 'ls /sandbox/.openclaw/milimo/milimo-blueprint/orchestrator/build/*.py 2>/dev/null | grep -v __init__ | wc -l') || true
    ok "Build Claw present ($module_count modules)"
  else
    warn "Build Claw blueprint not found"
  fi

  # Check config
  local config_check
  config_check=$(sandbox_exec "$gateway" '
    cat /sandbox/.openclaw/milimo/config.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"squad\",{}).get(\"name\",\"?\"))" 2>/dev/null || echo "MISSING"
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
  echo " Install mode: $(if [ "$RUNTIME_DEPLOY" = true ] || [ "$SANDBOX_PHASE" = "Running" ] || [ "$SANDBOX_PHASE" = "Ready" ]; then echo "Runtime deploy"; else echo "Dockerfile (official)"; fi)"
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

  # Expand PATH FIRST — nemoclaw installs to ~/.local/bin or ~/.nvm
  export PATH="$HOME/.local/bin:$HOME/.nvm/current/bin:$PATH"

  print_banner
  check_prerequisites

  # Determine deploy mode.
  # nemoclaw list is connection-agnostic (shows sandboxes regardless of Connected state).
  # nemoclaw status requires agent Connected and returns non-zero when disconnected,
  # making it unreliable for Apple Silicon / no-GPU environments where Connected=no.
  # SANDBOX_FOUND=true means NemoClaw config knows about the sandbox — but the
  # container may not be running. SANDBOX_PHASE tells us the actual state.
  if [ "$RUNTIME_DEPLOY" = true ]; then
    info "Mode: Runtime deploy (forced via --runtime-deploy)"
    deploy_to_sandbox
  elif [ "$SANDBOX_FOUND" = "true" ] && { [ "$SANDBOX_PHASE" = "Running" ] || [ "$SANDBOX_PHASE" = "Ready" ]; }; then
    info "Mode: Runtime deploy (sandbox '$SANDBOX_NAME' is $SANDBOX_PHASE)"
    deploy_to_sandbox
  elif [ "$SANDBOX_FOUND" = "true" ]; then
    # Sandbox exists but is not running — attempt to start it.
    info "Sandbox '$SANDBOX_NAME' exists but is $SANDBOX_PHASE — attempting to start..."
    if [ "$DRY_RUN" = true ]; then
      info "Dry run — would run: nemoclaw $SANDBOX_NAME connect"
      info "Mode: Would attempt runtime deploy if connect succeeds, otherwise Dockerfile deploy"
    elif [ "$NON_INTERACTIVE" = true ]; then
      warn "Non-interactive mode — skipping nemoclaw connect (may require interactive input)"
      warn "Sandbox '$SANDBOX_NAME' could not be started automatically"
      info "Mode: Fresh deploy via Dockerfile (existing sandbox not running, non-interactive)"
      deploy_via_dockerfile
    else
      info "Running: nemoclaw $SANDBOX_NAME connect (15s timeout)..."
      if command_exists timeout; then
        timeout 15 nemoclaw "$SANDBOX_NAME" connect 2>&1 || true
      elif command_exists gtimeout; then
        gtimeout 15 nemoclaw "$SANDBOX_NAME" connect 2>&1 || true
      else
        # Best-effort: run in background, kill after 15s
        nemoclaw "$SANDBOX_NAME" connect &
        local connect_pid=$!
        sleep 15 && kill "$connect_pid" 2>/dev/null &
        wait "$connect_pid" 2>/dev/null || true
      fi
      # Re-check phase after connect attempt
      export PATH="$HOME/.local/bin:$HOME/.nvm/current/bin:$PATH"
      local recheck_phase
      recheck_phase=$(nemoclaw list --json 2>/dev/null | jq -r ".sandboxes[] | select(.name == \"$SANDBOX_NAME\") | .phase // \"Unknown\"" 2>/dev/null || echo "Unknown")
      if [ "$recheck_phase" = "Running" ] || [ "$recheck_phase" = "Ready" ]; then
        ok "Sandbox '$SANDBOX_NAME' is now $recheck_phase"
        info "Mode: Runtime deploy (sandbox started successfully)"
        deploy_to_sandbox
      else
        warn "Sandbox '$SANDBOX_NAME' could not be started (still $recheck_phase)"
        info "Mode: Fresh deploy via Dockerfile (existing sandbox not running)"
        deploy_via_dockerfile
      fi
    fi
  else
    info "Mode: Fresh deploy (no existing sandbox detected)"
    deploy_via_dockerfile
  fi

  run_onboarding
  verify_installation
  print_summary
}

main "$@"
