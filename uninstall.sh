#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# MilimoClaw Uninstaller
#
# Removes MilimoClaw resources while preserving NemoClaw and OpenShell.
#   - MilimoClaw plugin from sandbox
#   - MilimoClaw blueprint from sandbox
#   - ~/.milimo config directory
#   - Local build bundles
#
# Preserves: NemoClaw, OpenShell, OpenClaw, Docker, Node.js

set -euo pipefail

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
  # shellcheck disable=SC2034
  C_GREEN='' C_BOLD='' C_DIM='' C_RED='' C_YELLOW='' C_CYAN='' C_RESET=''
fi

info() { printf "${C_CYAN}[INFO]${C_RESET}  %s\n" "$*"; }
warn() { printf "${C_YELLOW}[WARN]${C_RESET}  %s\n" "$*"; }
ok() { printf "  ${C_GREEN}✓${C_RESET}  %s\n" "$*"; }
log_step() { printf "\n${C_GREEN}${C_BOLD}>>> %s${C_RESET}\n" "$*"; }

command_exists() { command -v "$1" &>/dev/null; }

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SANDBOX_NAME="${MILIMO_SANDBOX_NAME:-my-assistant}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
BUNDLE_DIR="$ROOT_DIR/dist-bundle"

ASSUME_YES=false

usage() {
  printf "\n"
  printf "  ${C_BOLD}MilimoClaw Uninstaller${C_RESET}\n\n"
  printf "  ${C_DIM}Usage:${C_RESET}\n"
  printf "    ./uninstall.sh [--yes]\n\n"
  printf "  ${C_GREEN}Options:${C_RESET}\n"
  printf "    --yes             Skip the confirmation prompt\n"
  printf "    --sandbox-name N  Sandbox pod name (default: my-assistant)\n"
  printf "    -h, --help        Show this help\n"
  printf "\n"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --yes)
      ASSUME_YES=true
      shift
      ;;
    --sandbox-name)
      shift
      SANDBOX_NAME="$1"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) warn "Unknown argument: $1" ;;
  esac
done

confirm() {
  if [ "$ASSUME_YES" = true ]; then
    return 0
  fi

  printf "\n"
  printf "  ${C_YELLOW}What will be removed:${C_RESET}\n"
  printf "  ${C_DIM}  · MilimoClaw plugin from sandbox${C_RESET}\n"
  printf "  ${C_DIM}  · MilimoClaw blueprint from sandbox${C_RESET}\n"
  printf "  ${C_DIM}  · ~/.milimo config directory${C_RESET}\n"
  printf "  ${C_DIM}  · Local build bundles (dist-bundle/)${C_RESET}\n"
  printf "\n"
  printf "  ${C_DIM}NemoClaw, OpenShell, OpenClaw, Docker, Node.js are preserved.${C_RESET}\n"
  printf "\n"
  printf "  ${C_BOLD}Continue?${C_RESET} [y/N] "
  local reply=""
  if [ -t 2 ] && read -r reply 0</dev/tty 2>/dev/null; then
    :
  else
    read -r reply || true
  fi
  case "$reply" in
    y | Y | yes | YES) ;;
    *)
      info "Aborted."
      exit 0
      ;;
  esac
}

remove_sandbox_plugin() {
  log_step "Removing plugin from sandbox"

  if ! command_exists docker; then
    warn "Docker not found; skipping sandbox cleanup."
    return 0
  fi

  if ! docker info &>/dev/null; then
    warn "Docker is not running; skipping sandbox cleanup."
    return 0
  fi

  local gateway
  gateway=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i "openshell\|nemoclaw\|cluster" | head -1 || true)

  if [ -z "$gateway" ]; then
    info "No gateway container found; skipping sandbox cleanup."
    return 0
  fi

  # Uninstall plugin via OpenClaw
  docker exec "$gateway" kubectl exec -n openshell "$SANDBOX_NAME" -- bash -c "
    openclaw plugins uninstall milimo 2>/dev/null || true
    rm -rf /sandbox/extensions/milimo
    rm -rf /sandbox/milimo-blueprint
    rm -rf /sandbox/.milimo
    rm -rf /sandbox/.nemoclaw/config.json
    echo 'Milimo plugin removed from sandbox'
  " 2>/dev/null || warn "Could not remove plugin from sandbox (it may not be installed)"

  ok "Plugin removed from sandbox"
}

remove_local_files() {
  log_step "Removing local files"

  # Remove ~/.milimo config
  if [ -d "${HOME}/.milimo" ]; then
    rm -rf "${HOME}/.milimo"
    ok "Removed ~/.milimo"
  else
    info "$HOME/.milimo does not exist"
  fi

  # Remove legacy install paths
  if [ -d "/opt/milimo" ]; then
    rm -rf /opt/milimo
    ok "Removed /opt/milimo"
  fi

  if [ -d "/opt/milimo-blueprint" ]; then
    rm -rf /opt/milimo-blueprint
    ok "Removed /opt/milimo-blueprint"
  fi

  # Remove build bundles
  if [ -d "$BUNDLE_DIR" ]; then
    rm -rf "$BUNDLE_DIR"
    ok "Removed build bundles"
  fi
}

unregister_plugin() {
  if command_exists openclaw; then
    info "Unregistering Milimo plugin from OpenClaw..."
    openclaw plugins uninstall milimo >/dev/null 2>&1 \
      || warn "Could not unregister plugin. It may not be registered."
  fi
}

print_bye() {
  printf "\n"
  printf "  ${C_GREEN}${C_BOLD}MilimoClaw${C_RESET}\n"
  printf "\n"
  printf "  ${C_GREEN}${C_BOLD}Claws retracted.${C_RESET}  ${C_DIM}Until next time.${C_RESET}\n"
  printf "\n"
  printf "  ${C_DIM}https://github.com/mainza-ai/MilimoClaw${C_RESET}\n"
  printf "\n"
}

main() {
  printf "\n"
  printf "  ${C_GREEN}${C_BOLD}MilimoClaw Uninstaller${C_RESET}\n"
  printf "  ${C_DIM}Removing MilimoClaw, preserving NemoClaw and OpenShell${C_RESET}\n"
  printf "\n"

  confirm
  unregister_plugin
  remove_sandbox_plugin
  remove_local_files
  print_bye
}

if [ "${BASH_SOURCE[0]-}" = "$0" ] || { [ -z "${BASH_SOURCE[0]-}" ] && { [ "$0" = "bash" ] || [ "$0" = "-bash" ]; }; }; then
  main "$@"
fi
