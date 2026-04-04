#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# MilimoClaw Uninstaller
#
# Removes MilimoClaw resources while preserving NemoClaw and OpenShell.
#   - MilimoClaw plugin from /opt/milimo
#   - MilimoClaw blueprint from /opt/milimo-blueprint
#   - ~/.milimo config directory
#   - MilimoClaw Docker containers and images
#
# Preserves: NemoClaw, OpenShell, OpenClaw, Docker, Node.js, Ollama

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
  C_RESET=$'\033[0m'
else
  C_GREEN='' C_BOLD='' C_DIM='' C_RED='' C_YELLOW='' C_RESET=''
fi

info() { printf "${C_GREEN}[uninstall]${C_RESET} %s\n" "$*"; }
warn() { printf "${C_YELLOW}[uninstall]${C_RESET} %s\n" "$*"; }
fail() {
  printf "${C_RED}[uninstall]${C_RESET} %s\n" "$*" >&2
  exit 1
}
ok() { printf "  ${C_GREEN}✓${C_RESET}  %s\n" "$*"; }

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MILIMO_INSTALL_DIR="${MILIMO_INSTALL_DIR:-/opt/milimo}"
MILIMO_BLUEPRINT_DIR="${MILIMO_BLUEPRINT_DIR:-/opt/milimo-blueprint}"
MILIMO_CONFIG_DIR="${HOME}/.milimo"

ASSUME_YES=false

usage() {
  printf "\n"
  printf "  ${C_BOLD}MilimoClaw Uninstaller${C_RESET}\n\n"
  printf "  ${C_DIM}Usage:${C_RESET}\n"
  printf "    ./uninstall.sh [--yes]\n\n"
  printf "  ${C_GREEN}Options:${C_RESET}\n"
  printf "    --yes             Skip the confirmation prompt\n"
  printf "    -h, --help        Show this help\n"
  printf "\n"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --yes)
      ASSUME_YES=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

confirm() {
  if [ "$ASSUME_YES" = true ]; then
    return 0
  fi

  printf "\n"
  printf "  ${C_YELLOW}What will be removed:${C_RESET}\n"
  printf "  ${C_DIM}  · MilimoClaw plugin (${MILIMO_INSTALL_DIR})${C_RESET}\n"
  printf "  ${C_DIM}  · MilimoClaw blueprint (${MILIMO_BLUEPRINT_DIR})${C_RESET}\n"
  printf "  ${C_DIM}  · MilimoClaw config (~/.milimo)${C_RESET}\n"
  printf "  ${C_DIM}  · MilimoClaw Docker containers and images${C_RESET}\n"
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

remove_path() {
  local path="$1"
  if [ -e "$path" ] || [ -L "$path" ]; then
    rm -rf "$path"
    info "Removed $path"
  fi
}

remove_milimo_plugin() {
  info "Removing MilimoClaw plugin..."
  remove_path "${MILIMO_INSTALL_DIR}"
  remove_path "${MILIMO_BLUEPRINT_DIR}"
}

remove_milimo_config() {
  info "Removing MilimoClaw config..."
  remove_path "${MILIMO_CONFIG_DIR}"
}

remove_docker_resources() {
  if ! command -v docker >/dev/null 2>&1; then
    warn "docker not found; skipping Docker cleanup."
    return 0
  fi

  if ! docker info >/dev/null 2>&1; then
    warn "docker is not running; skipping Docker cleanup."
    return 0
  fi

  # Remove MilimoClaw containers
  local -a container_ids=()
  local line
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    container_ids+=("$line")
  done < <(
    docker ps -a --format '{{.ID}} {{.Image}} {{.Names}}' 2>/dev/null \
      | awk 'BEGIN { IGNORECASE=1 } { if ($0 ~ /milimo/) print $1 }' \
      | awk '!seen[$0]++'
  )

  if [ "${#container_ids[@]}" -gt 0 ]; then
    for cid in "${container_ids[@]}"; do
      docker rm -f "$cid" >/dev/null 2>&1 && info "Removed container $cid" || warn "Failed to remove container $cid"
    done
  else
    info "No MilimoClaw Docker containers found"
  fi

  # Remove MilimoClaw images
  local -a image_ids=()
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    image_ids+=("$line")
  done < <(
    docker images --format '{{.ID}} {{.Repository}}:{{.Tag}}' 2>/dev/null \
      | awk 'BEGIN { IGNORECASE=1 } { if ($0 ~ /milimo/) print $1 }' \
      | awk '!seen[$0]++'
  )

  if [ "${#image_ids[@]}" -gt 0 ]; then
    for iid in "${image_ids[@]}"; do
      docker rmi -f "$iid" >/dev/null 2>&1 && info "Removed image $iid" || warn "Failed to remove image $iid"
    done
  else
    info "No MilimoClaw Docker images found"
  fi
}

unregister_plugin() {
  if command -v openclaw >/dev/null 2>&1; then
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
  printf "  ${C_DIM}https://github.com/mainzak/MilimoClaw${C_RESET}\n"
  printf "\n"
}

main() {
  printf "\n"
  printf "  ${C_GREEN}${C_BOLD}MilimoClaw Uninstaller${C_RESET}\n"
  printf "  ${C_DIM}Removing MilimoClaw, preserving NemoClaw and OpenShell${C_RESET}\n"
  printf "\n"

  confirm
  unregister_plugin
  remove_milimo_plugin
  remove_milimo_config
  remove_docker_resources
  print_bye
}

if [ "${BASH_SOURCE[0]-}" = "$0" ] || { [ -z "${BASH_SOURCE[0]-}" ] && { [ "$0" = "bash" ] || [ "$0" = "-bash" ]; }; }; then
  main "$@"
fi
