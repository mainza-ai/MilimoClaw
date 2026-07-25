#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# check-plugin-sync.sh — CI/local guard that verifies the root
# milimo-hermes-plugin/ and milimo-core/ copies are byte-identical to their
# counterparts in milimo-hermes-sandbox/. install-hermes.sh copies the root
# copies into the sandbox directory before docker build, so divergence causes
# silent build-context drift.
#
# Exit 0 when in sync, exit 1 with a diff summary otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SANDBOX_DIR="$PROJECT_ROOT/milimo-hermes-sandbox"

ROOT_PLUGIN="$PROJECT_ROOT/milimo-hermes-plugin"
SANDBOX_PLUGIN="$SANDBOX_DIR/milimo-hermes-plugin"

ROOT_CORE="$PROJECT_ROOT/milimo-core"
SANDBOX_CORE="$SANDBOX_DIR/milimo-core"

cleanup_tmpdirs() {
  [ -n "${TMP_A:-}" ] && [ -d "${TMP_A:-}" ] && rm -rf "$TMP_A"
  [ -n "${TMP_B:-}" ] && [ -d "${TMP_B:-}" ] && rm -rf "$TMP_B"
}
trap cleanup_tmpdirs EXIT

check_copy() {
  local label="$1"
  local root_src="$2"
  local sandbox_copy="$3"

  if [ ! -d "$root_src" ]; then
    echo "[SKIP] $label: $root_src does not exist"
    return 0
  fi
  if [ ! -d "$sandbox_copy" ]; then
    echo "[FAIL] $label: sandbox copy missing: $sandbox_copy"
    return 1
  fi

  local TMP_A TMP_B
  TMP_A="$(mktemp -d)"
  TMP_B="$(mktemp -d)"

  # Exclude __pycache__, .pyc, and .pth finder files (generated at install)
  local exclude_args=()
  exclude_args+=(--exclude='__pycache__')
  exclude_args+=(--exclude='*.pyc')
  exclude_args+=(--exclude='*.pth')
  exclude_args+=(--exclude='*.egg-info')
  exclude_args+=(--exclude='.DS_Store')

  local rc=0
  diff -ruN "${exclude_args[@]}" "$root_src" "$sandbox_copy" >"$TMP_A/diff.txt" 2>&1 || rc=$?

  if [ "$rc" -eq 0 ]; then
    echo "[OK] $label: $root_src ↔ $sandbox_copy"
    return 0
  fi

  local file_count
  file_count="$(grep -cE '^(Only|diff )' "$TMP_A/diff.txt" 2>/dev/null || echo 0)"
  echo "[DRIFT] $label: $root_src ↔ $sandbox_copy — $file_count file(s) differ"
  echo "  Run: rsync -a --delete $root_src/ $sandbox_copy/"
  echo ""
  sed 's/^/    /' "$TMP_A/diff.txt"
  return 1
}

rc=0

echo "Plugin-sync check (root ↔ sandbox)"
echo "  ROOT_PLUGIN:   $ROOT_PLUGIN"
echo "  SANDBOX_PLUGIN:$SANDBOX_PLUGIN"
echo "  ROOT_CORE:     $ROOT_CORE"
echo "  SANDBOX_CORE:  $SANDBOX_CORE"
echo ""

check_copy "plugin" "$ROOT_PLUGIN" "$SANDBOX_PLUGIN" || rc=1
check_copy "core" "$ROOT_CORE" "$SANDBOX_CORE" || rc=1

if [ "$rc" -ne 0 ]; then
  echo ""
  echo "Sync check FAILED — resolve drift before building the sandbox image."
  exit 1
fi

echo ""
echo "Sync check PASSED."
