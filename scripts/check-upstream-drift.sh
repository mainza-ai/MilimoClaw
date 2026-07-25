#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# check-upstream-drift.sh — detect when local NemoClaw scripts diverge from
# upstream copies baked into the hermes-sandbox-base image.
#
# The wrapper and validator scripts in milimo-hermes-sandbox/scripts/ are
# local copies verified by SHA hashes at build time. If upstream NemoClaw
# updates these scripts, Milimo's copies silently drift.
#
# Usage:
#   bash scripts/check-upstream-drift.sh
#
# Requires:
#   - Docker (to pull the latest hermes-sandbox-base)
#   - The image SHA being compared can be overridden via UPSTREAM_IMAGE

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SANDBOX_DIR="$PROJECT_ROOT/milimo-hermes-sandbox"

UPSTREAM_IMAGE="${UPSTREAM_IMAGE:-ghcr.io/nvidia/nemoclaw/hermes-sandbox-base:latest}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== Upstream Script Drift Check ==="
echo "Upstream image: $UPSTREAM_IMAGE"
echo ""

# Pull upstream image
echo "Pulling upstream image..."
if ! docker pull "$UPSTREAM_IMAGE" 2>/dev/null; then
  echo "ERROR: Could not pull $UPSTREAM_IMAGE"
  exit 1
fi

# Extract upstream scripts
echo "Extracting upstream scripts..."
UPSTREAM_HASH=$(docker inspect "$UPSTREAM_IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "$UPSTREAM_IMAGE")

docker create --name milimo-drift-check "$UPSTREAM_IMAGE" sleep 1 2>/dev/null || true
docker cp milimo-drift-check:/usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py "$TMPDIR/upstream-validate.py" 2>/dev/null || echo "  (upstream validate script not found)"
docker cp milimo-drift-check:/usr/local/lib/nemoclaw/hermes-wrapper.py "$TMPDIR/upstream-wrapper.py" 2>/dev/null || echo "  (upstream wrapper not found)"
docker rm -f milimo-drift-check 2>/dev/null || true

# Compare local vs upstream
rc=0

for script in validate-hermes-env-secret-boundary.py hermes-wrapper.py; do
  local_path="$SANDBOX_DIR/scripts/$script"
  upstream_path="$TMPDIR/upstream-${script}"

  if [ ! -f "$upstream_path" ]; then
    echo "[SKIP] $script — not found in upstream image"
    continue
  fi

  if [ ! -f "$local_path" ]; then
    echo "[FAIL] $script — local copy missing at $local_path"
    rc=1
    continue
  fi

  local_hash=$(sha256sum "$local_path" | cut -d' ' -f1)
  upstream_hash=$(sha256sum "$upstream_path" | cut -d' ' -f1)

  if [ "$local_hash" = "$upstream_hash" ]; then
    echo "[OK]   $script — local matches upstream"
  else
    echo "[DRIFT] $script — local ($local_hash) ≠ upstream ($upstream_hash)"
    echo "       Upstream image: $UPSTREAM_HASH"
    rc=1
  fi
done

echo ""
if [ "$rc" -eq 0 ]; then
  echo "All local scripts match upstream. No drift detected."
else
  echo "Drift detected. Review upstream changes and update local copies."
  echo "After updating, recompute SHA hashes and update NEMOCLAW_HERMES_*_SHA256 in the Dockerfile."
fi
exit "$rc"
