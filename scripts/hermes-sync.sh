#!/bin/bash
set -euo pipefail

# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# hermes-sync.sh — Hermes claw file sync for MilimoClaw
#
# Syncs claw-generated files (invoices, reports, PRs, drafts, etc.) from a
# running Hermes sandbox to the host filesystem.
#
# Transport (auto-detected, in priority order):
#   1. docker cp   — direct container copy (fast, no extra deps)
#   2. nemohermes sandbox share mount — SSHFS mount (if sshfs available)
#   3. nemohermes sandbox exec + tar  — archive via stdout
#
# Usage
# -----
#   # Sync all claws to ./claws_data/
#   ./scripts/hermes-sync.sh
#
#   # Sync only the finance claw
#   ./scripts/hermes-sync.sh --role finance
#
#   # Sync to a custom output directory
#   ./scripts/hermes-sync.sh --output /tmp/my-claws
#
#   # Watch mode: sync every 60 seconds
#   ./scripts/hermes-sync.sh --watch --interval 60
#
#   # Archive mode: produce a tarball instead of directory tree
#   ./scripts/hermes-sync.sh --archive --output ./claws-export.tar.gz
#
#   # Dry run: show what would be synced without copying
#   ./scripts/hermes-sync.sh --dry-run

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Config ──────────────────────────────────────────────────────────────────
CLAW_ROLES=("content" "ops" "analytics" "finance" "build" "assistant")

# Path candidates checked in order (new Hermes-native first, legacy fallback)
declare -a CLAWS_SOURCE_PATHS=(
  "/sandbox/.hermes/claws"
  "/sandbox/.openclaw/milimo/claws"
  "/sandbox/.openclaw-data/milimo/claws"
)

DEFAULT_OUTPUT_DIR="$PROJECT_ROOT/claws_data"
OUTPUT_DIR="$DEFAULT_OUTPUT_DIR"
ROLE=""
WATCH_MODE=false
WATCH_INTERVAL=60
ARCHIVE_MODE=false
ARCHIVE_PATH=""
DRY_RUN=false
TRANSPORT="auto"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
log_info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Help ────────────────────────────────────────────────────────────────────
usage() {
  cat <<EOH
Usage: $(basename "$0") [OPTIONS]

Sync claw files from the running Hermes sandbox to the host.

Options:
  --role ROLE       Sync only one claw role (content|ops|analytics|finance|build|assistant)
  --output DIR      Output directory (default: $DEFAULT_OUTPUT_DIR)
  --watch           Continuously sync at intervals
  --interval SECS   Watch interval in seconds (default: 60)
  --archive         Produce a tarball instead of a directory tree
  --dry-run         Show what would be synced without copying
  --transport M     Force transport: docker|exec|mount (default: auto)
  --help            Show this help

Examples:
  $(basename "$0")                          # sync all claws
  $(basename "$0") --role finance           # sync only finance claw
  $(basename "$0") --watch --interval 300   # sync every 5 minutes
  $(basename "$0") --archive --output ./claws-backup.tar.gz
EOH
  exit 0
}

# ── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      ROLE="$2"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --watch)
      WATCH_MODE=true
      shift
      ;;
    --interval)
      WATCH_INTERVAL="$2"
      shift 2
      ;;
    --archive)
      ARCHIVE_MODE=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --transport)
      TRANSPORT="$2"
      shift 2
      ;;
    --help | -h) usage ;;
    *)
      log_error "Unknown option: $1"
      usage
      ;;
  esac
done

# ── Validate role ───────────────────────────────────────────────────────────
if [[ -n "$ROLE" ]]; then
  valid=false
  for r in "${CLAW_ROLES[@]}"; do
    [[ "$r" == "$ROLE" ]] && {
      valid=true
      break
    }
  done
  $valid || {
    log_error "Invalid role '$ROLE'. Valid: ${CLAW_ROLES[*]}"
    exit 1
  }
fi

# ── Discover sandbox ────────────────────────────────────────────────────────
discover_sandbox() {
  # 1. Try nemohermes status
  local sandbox_name=""
  sandbox_name=$(nemohermes milimo-hermes status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))" 2>/dev/null || echo "")
  if [[ -n "$sandbox_name" ]]; then
    echo "$sandbox_name"
    return 0
  fi

  # 2. Try docker container discovery
  local container=""
  container=$(docker ps --filter "name=milimo-hermes" --format "{{.Names}}" 2>/dev/null | head -n 1)
  if [[ -z "$container" ]]; then
    container=$(docker ps --filter "name=openshell-milimo-hermes" --format "{{.Names}}" 2>/dev/null | head -n 1)
  fi
  if [[ -n "$container" ]]; then
    echo "$container"
    return 0
  fi

  # 3. Broader search
  container=$(docker ps --filter "ancestor=*milimo*hermes*" --format "{{.Names}}" 2>/dev/null | head -n 1)
  if [[ -n "$container" ]]; then
    echo "$container"
    return 0
  fi

  return 1
}

detect_source_path() {
  local container="$1"
  local _is_nemo="$2"
  local path=""

  if [[ "$_is_nemo" == "true" ]]; then
    for candidate in "${CLAWS_SOURCE_PATHS[@]}"; do
      if nemohermes "$container" exec -- test -d "$candidate" 2>/dev/null; then
        path="$candidate"
        break
      fi
    done
  else
    for candidate in "${CLAWS_SOURCE_PATHS[@]}"; do
      if docker exec "$container" test -d "$candidate" 2>/dev/null; then
        path="$candidate"
        break
      fi
    done
  fi

  if [[ -z "$path" ]]; then
    # Fallback: use the first candidate (will get created at runtime)
    path="${CLAWS_SOURCE_PATHS[0]}"
  fi

  echo "$path"
}

# ── Transport: docker cp ────────────────────────────────────────────────────
sync_docker_cp() {
  local container="$1"
  local src_base="$2"
  local dest_base="$3"
  local roles=("${CLAW_ROLES[@]}")

  if [[ -n "$ROLE" ]]; then
    roles=("$ROLE")
  fi

  for role in "${roles[@]}"; do
    local src="$src_base/$role"
    local dst="$dest_base/$role"

    if $DRY_RUN; then
      log_info "[DRY-RUN] docker cp \"$container:$src/.\" \"$dst/\""
      continue
    fi

    mkdir -p "$dst"
    if docker cp "$container:$src/." "$dst/" 2>/dev/null; then
      # Fix ownership (docker cp creates root-owned files)
      chmod -R u+rwX "$dst" 2>/dev/null || true
      log_ok "Synced $role → $dst"
    else
      log_warn "No files for $role (empty or missing path)"
    fi
  done
}

# ── Transport: nemohermes exec + tar ────────────────────────────────────────
sync_exec_tar() {
  local container="$1"
  local src_base="$2"
  local dest_base="$3"
  local roles=("${CLAW_ROLES[@]}")

  if [[ -n "$ROLE" ]]; then
    roles=("$ROLE")
  fi

  for role in "${roles[@]}"; do
    local src="$src_base/$role"
    local dst="$dest_base/$role"

    if $DRY_RUN; then
      log_info "[DRY-RUN] nemohermes $container exec -- tar cf - \"$src\" | tar xf - -C \"$dest_base\""
      continue
    fi

    mkdir -p "$dst"
    if nemohermes "$container" exec -- tar cf - "$src" 2>/dev/null | tar xf - -C "$dest_base" --strip-components=1 2>/dev/null; then
      chmod -R u+rwX "$dst" 2>/dev/null || true
      log_ok "Synced $role → $dst"
    else
      log_warn "No files for $role (empty or missing path)"
    fi
  done
}

# ── Main sync ───────────────────────────────────────────────────────────────
do_sync() {
  log_info "Discovering Hermes sandbox..."
  local sandbox_id=""
  sandbox_id=$(discover_sandbox) || {
    log_error "No running Hermes sandbox found. Is the sandbox running?"
    log_error "Start it with: nemohermes milimo-hermes connect"
    exit 1
  }
  log_ok "Found sandbox: $sandbox_id"

  # Detect if this is a nemohermes-managed sandbox or just a docker container
  local is_nemo=false
  if nemohermes "$sandbox_id" status --json 2>/dev/null >/dev/null; then
    is_nemo=true
  fi

  local src_base
  src_base=$(detect_source_path "$sandbox_id" "$is_nemo")
  log_info "Claw data source: ${src_base}"

  local dest_base="$OUTPUT_DIR"
  mkdir -p "$dest_base"

  # Choose transport
  if [[ "$TRANSPORT" == "auto" ]]; then
    # Prefer docker cp when we have a container name
    if docker inspect "$sandbox_id" >/dev/null 2>&1; then
      TRANSPORT="docker"
    elif $is_nemo; then
      TRANSPORT="exec"
    else
      TRANSPORT="docker"
    fi
  fi

  log_info "Transport: $TRANSPORT"

  case "$TRANSPORT" in
    docker) sync_docker_cp "$sandbox_id" "$src_base" "$dest_base" ;;
    exec) sync_exec_tar "$sandbox_id" "$src_base" "$dest_base" ;;
    *)
      log_error "Unknown transport: $TRANSPORT"
      exit 1
      ;;
  esac

  if $ARCHIVE_MODE; then
    local archive_dest="${ARCHIVE_PATH:-${OUTPUT_DIR}.tar.gz}"
    log_info "Creating archive: $archive_dest"
    if ! $DRY_RUN; then
      tar czf "$archive_dest" -C "$(dirname "$dest_base")" "$(basename "$dest_base")"
      log_ok "Archive created: $archive_dest ($(du -h "$archive_dest" | cut -f1))"
    fi
  fi

  log_ok "Sync complete. Files at: $dest_base"
}

# ── Execute ──────────────────────────────────────────────────────────────────
if $WATCH_MODE; then
  log_info "Watch mode enabled (interval: ${WATCH_INTERVAL}s). Press Ctrl+C to stop."
  while true; do
    echo ""
    log_info "=== Sync at $(date '+%Y-%m-%d %H:%M:%S') ==="
    do_sync
    sleep "$WATCH_INTERVAL"
  done
else
  do_sync
fi
