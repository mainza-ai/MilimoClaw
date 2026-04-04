#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# MilimoClaw Installer
#
# Installs Milimo Claw on top of an existing NemoClaw + OpenShell setup.
# MilimoClaw extends NemoClaw with multi-agent squad coordination,
# role-specific claw blueprints, privacy routing, and the War Room TUI.
#
# Prerequisites:
#   - NVIDIA NemoClaw installed and onboarded
#   - Docker (or compatible container runtime) running
#   - Node.js >= 22.0.0
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/mainzak/MilimoClaw/main/install.sh | bash
#   # or locally:
#   ./install.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Color / style
# ---------------------------------------------------------------------------
if [[ -z "${NO_COLOR:-}" && -t 1 ]]; then
  if [[ "${COLORTERM:-}" == "truecolor" || "${COLORTERM:-}" == "24bit" ]]; then
    C_GREEN=$'\033[38;2;118;185;0m'
  else
    C_GREEN=$'\033[38;5;148m'
  fi
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RED=$'\033[1;31m'
  C_YELLOW=$'\033[1;33m'
  C_CYAN=$'\033[1;36m'
  C_RESET=$'\033[0m'
else
  C_GREEN='' C_BOLD='' C_DIM='' C_RED='' C_YELLOW='' C_CYAN='' C_RESET=''
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MILIMO_VERSION="0.1.0"
NODE_MIN_VERSION="22"
MILIMO_INSTALL_DIR="${MILIMO_INSTALL_DIR:-/opt/milimo}"
MILIMO_BLUEPRINT_DIR="${MILIMO_BLUEPRINT_DIR:-/opt/milimo-blueprint}"
MILIMO_CONFIG_DIR="${HOME}/.milimo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info() { printf "${C_CYAN}[INFO]${C_RESET}  %s\n" "$*"; }
warn() { printf "${C_YELLOW}[WARN]${C_RESET}  %s\n" "$*"; }
error() {
  printf "${C_RED}[ERROR]${C_RESET} %s\n" "$*" >&2
  exit 1
}
ok() { printf "  ${C_GREEN}✓${C_RESET}  %s\n" "$*"; }
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
# Pre-flight checks
# ---------------------------------------------------------------------------
preflight() {
  log_step "Running pre-flight checks"

  # Check Node.js
  if ! command_exists node; then
    error "Node.js is not installed. MilimoClaw requires Node.js >= ${NODE_MIN_VERSION}."
  fi

  local node_version
  node_version=$(node --version | sed 's/^v//')
  local node_major
  node_major=$(echo "$node_version" | cut -d. -f1)
  if ((node_major < NODE_MIN_VERSION)); then
    error "Node.js $node_version is too old. MilimoClaw requires Node.js >= ${NODE_MIN_VERSION}."
  fi
  ok "Node.js $node_version"

  # Check npm
  if ! command_exists npm; then
    error "npm is not installed."
  fi
  ok "npm $(npm --version)"

  # Check Docker
  if ! command_exists docker; then
    warn "Docker is not installed. Required for sandbox runtime."
    warn "Install from https://docs.docker.com/get-docker/"
  elif ! docker info &>/dev/null; then
    warn "Docker is not running. Please start Docker."
  else
    ok "Docker is running"
  fi

  # Check OpenShell (installed by NemoClaw)
  if ! command_exists openshell; then
    warn "OpenShell is not installed. MilimoClaw requires NemoClaw's OpenShell runtime."
    warn "Install NemoClaw first: curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash"
    warn ""
    read -rp "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 0
    fi
  else
    ok "OpenShell $(openshell --version 2>/dev/null || echo 'installed')"
  fi

  # Check NemoClaw onboarding
  if [ ! -d "${HOME}/.nemoclaw" ] && [ ! -f "${HOME}/.openclaw/openclaw.json" ]; then
    warn "NemoClaw does not appear to be onboarded."
    warn "MilimoClaw extends NemoClaw. You must onboard NemoClaw first:"
    warn "  nemoclaw onboard"
    warn ""
    read -rp "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 0
    fi
  else
    ok "NemoClaw appears to be onboarded"
  fi

  # Check NVIDIA API key
  if [ -z "${NVIDIA_API_KEY:-}" ]; then
    warn "NVIDIA_API_KEY environment variable is not set."
    warn "Some inference features may not work without it."
  fi
}

# ---------------------------------------------------------------------------
# Build MilimoClaw plugin
# ---------------------------------------------------------------------------
build_plugin() {
  log_step "Building MilimoClaw plugin"

  if [ ! -d "${SCRIPT_DIR}/milimo" ]; then
    error "Milimo plugin source not found at ${SCRIPT_DIR}/milimo"
    info "Run this script from the MilimoClaw repository root."
  fi

  cd "${SCRIPT_DIR}/milimo"

  info "Installing dependencies..."
  npm install --ignore-scripts

  info "Building TypeScript..."
  if npm run build 2>/dev/null; then
    ok "Plugin built successfully"
  else
    warn "Build script not found or failed. Attempting manual compilation..."
    npx tsc --noEmit || true
  fi

  cd "${SCRIPT_DIR}"
}

# ---------------------------------------------------------------------------
# Install MilimoClaw plugin into OpenClaw
# ---------------------------------------------------------------------------
install_plugin() {
  log_step "Installing MilimoClaw plugin"

  # Copy plugin to install directory
  if [ -d "${MILIMO_INSTALL_DIR}" ]; then
    info "Removing previous installation from ${MILIMO_INSTALL_DIR}"
    rm -rf "${MILIMO_INSTALL_DIR}"
  fi

  mkdir -p "${MILIMO_INSTALL_DIR}"

  # Prefer built dist/, fall back to src/
  if [ -d "${SCRIPT_DIR}/milimo/dist" ]; then
    cp -r "${SCRIPT_DIR}/milimo/dist/"* "${MILIMO_INSTALL_DIR}/"
  else
    cp -r "${SCRIPT_DIR}/milimo/src/"* "${MILIMO_INSTALL_DIR}/"
  fi
  cp "${SCRIPT_DIR}/milimo/openclaw.plugin.json" "${MILIMO_INSTALL_DIR}/"
  cp "${SCRIPT_DIR}/milimo/package.json" "${MILIMO_INSTALL_DIR}/"

  # Install runtime dependencies
  cd "${MILIMO_INSTALL_DIR}"
  npm install --omit=dev --ignore-scripts 2>/dev/null || true
  cd "${SCRIPT_DIR}"

  ok "Plugin files installed to ${MILIMO_INSTALL_DIR}"

  # Copy blueprint
  if [ -d "${SCRIPT_DIR}/milimo-blueprint" ]; then
    if [ -d "${MILIMO_BLUEPRINT_DIR}" ]; then
      rm -rf "${MILIMO_BLUEPRINT_DIR}"
    fi
    mkdir -p "${MILIMO_BLUEPRINT_DIR}"
    cp -r "${SCRIPT_DIR}/milimo-blueprint/"* "${MILIMO_BLUEPRINT_DIR}/"
    ok "Blueprint installed to ${MILIMO_BLUEPRINT_DIR}"
  fi

  # Install plugin into OpenClaw (if available on host)
  if command_exists openclaw; then
    info "Registering plugin with OpenClaw..."
    openclaw plugins install "${MILIMO_INSTALL_DIR}" 2>/dev/null \
      || warn "Could not register plugin. You may need to run this inside the sandbox."
  fi
}

# ---------------------------------------------------------------------------
# Set up Milimo config directory
# ---------------------------------------------------------------------------
setup_config() {
  log_step "Setting up MilimoClaw configuration"

  mkdir -p "${MILIMO_CONFIG_DIR}"
  mkdir -p "${MILIMO_CONFIG_DIR}/blueprints"
  mkdir -p "${MILIMO_CONFIG_DIR}/audit"
  mkdir -p "${MILIMO_CONFIG_DIR}/mesh"
  mkdir -p "${MILIMO_CONFIG_DIR}/evolution"
  mkdir -p "${MILIMO_CONFIG_DIR}/tools"
  mkdir -p "${MILIMO_CONFIG_DIR}/attestations"
  mkdir -p "${MILIMO_CONFIG_DIR}/keys"
  mkdir -p "${MILIMO_CONFIG_DIR}/health"

  ok "Config directory created at ${MILIMO_CONFIG_DIR}"
}

# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------
print_summary() {
  echo ""
  printf "  ${C_GREEN}${C_BOLD}──────────────────────────────────────────────────────${C_RESET}\n"
  printf "  ${C_GREEN}${C_BOLD}  MilimoClaw v%s — Installation Complete${C_RESET}\n" "$MILIMO_VERSION"
  printf "  ${C_GREEN}${C_BOLD}──────────────────────────────────────────────────────${C_RESET}\n"
  echo ""
  echo "  Plugin:     ${MILIMO_INSTALL_DIR}"
  echo "  Blueprint:  ${MILIMO_BLUEPRINT_DIR}"
  echo "  Config:     ${MILIMO_CONFIG_DIR}"
  echo ""
  echo "  Next steps:"
  echo "    1. Connect to sandbox:  openshell sandbox connect <name>"
  echo "    2. Onboard Milimo:      openclaw milimo onboard"
  echo "    3. Check status:        openclaw milimo squad status"
  echo "    4. Launch War Room:     openclaw milimo warroom"
  echo ""
  printf "  ${C_GREEN}${C_BOLD}──────────────────────────────────────────────────────${C_RESET}\n"
  echo ""
  ok "Installation complete!"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  # Parse flags
  NON_INTERACTIVE=""
  for arg in "$@"; do
    case "$arg" in
      --non-interactive) NON_INTERACTIVE=1 ;;
      --version | -v)
        printf "milimo-claw-installer v%s\n" "$MILIMO_VERSION"
        exit 0
        ;;
      --help | -h)
        printf "\n  ${C_BOLD}MilimoClaw Installer${C_RESET}  ${C_DIM}v%s${C_RESET}\n\n" "$MILIMO_VERSION"
        printf "  ${C_DIM}Usage:${C_RESET}\n"
        printf "    curl -fsSL https://raw.githubusercontent.com/mainzak/MilimoClaw/main/install.sh | bash\n"
        printf "    ./install.sh [options]\n\n"
        printf "  ${C_DIM}Options:${C_RESET}\n"
        printf "    --non-interactive    Skip prompts (uses env vars / defaults)\n"
        printf "    --version, -v        Print installer version and exit\n"
        printf "    --help               Show this help message and exit\n\n"
        printf "  ${C_DIM}Environment:${C_RESET}\n"
        printf "    NVIDIA_API_KEY          API key for NVIDIA inference\n"
        printf "    MILIMO_INSTALL_DIR      Plugin install path (default: /opt/milimo)\n"
        printf "    MILIMO_BLUEPRINT_DIR    Blueprint install path (default: /opt/milimo-blueprint)\n"
        printf "\n"
        exit 0
        ;;
      *) error "Unknown option: $arg" ;;
    esac
  done

  _INSTALL_START=$SECONDS
  print_banner
  preflight
  build_plugin
  install_plugin
  setup_config
  print_summary
}

main "$@"
