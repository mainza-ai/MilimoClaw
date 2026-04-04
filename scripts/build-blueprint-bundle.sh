#!/usr/bin/env bash
#
# build-blueprint-bundle.sh — Create a self-contained MilimoClaw blueprint bundle
#
# Produces a .tar.gz with the full milimo-blueprint/ directory
# (orchestrator, roles, policies, templates) excluding caches and tests.
#
# Usage:
#   ./scripts/build-blueprint-bundle.sh              # outputs to dist-bundle/
#   ./scripts/build-blueprint-bundle.sh --version 2.0.1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BLUEPRINT_DIR="$ROOT_DIR/milimo-blueprint"
BUNDLE_DIR="$ROOT_DIR/dist-bundle"
BUNDLE_VERSION="${MILIMO_BUNDLE_VERSION:-}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      BUNDLE_VERSION="$2"
      shift 2
      ;;
    --output)
      BUNDLE_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [ -z "$BUNDLE_VERSION" ]; then
  BUNDLE_VERSION=$(node -p "require('$ROOT_DIR/milimo/package.json').version" 2>/dev/null || echo "0.1.0")
fi

BUNDLE_NAME="milimo-blueprint-v${BUNDLE_VERSION}.tar.gz"

echo "============================================"
echo " MilimoClaw Blueprint Bundle Builder v${BUNDLE_VERSION}"
echo "============================================"
echo ""

# Step 1: Prepare bundle directory
echo "[1/3] Preparing bundle directory..."
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

# Step 2: Create tar excluding caches and tests
echo "[2/3] Creating tar archive..."
cd "$ROOT_DIR"

tar \
  --owner=sandbox \
  --group=sandbox \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='*.egg-info' \
  --exclude='tests/' \
  --exclude='test_*.py' \
  --exclude='.mypy_cache' \
  -czf "$BUNDLE_DIR/$BUNDLE_NAME" \
  milimo-blueprint/

# Generate SHA256 checksum
cd "$BUNDLE_DIR"
sha256sum "$BUNDLE_NAME" > "${BUNDLE_NAME}.sha256"

BUNDLE_SIZE=$(du -h "$BUNDLE_NAME" | cut -f1)
CHECKSUM=$(cat "${BUNDLE_NAME}.sha256" | awk '{print $1}')

echo "  ✓ Archive created: $BUNDLE_SIZE"
echo "  ✓ SHA256: $CHECKSUM"

# Step 3: Cleanup temp files
echo "[3/3] Cleaning up..."
echo "  ✓ Cleanup complete"

echo ""
echo "============================================"
echo " Blueprint bundle ready: $BUNDLE_DIR/$BUNDLE_NAME"
echo " Size: $BUNDLE_SIZE"
echo " Checksum: $CHECKSUM"
echo "============================================"
echo ""
echo "Deploy with:"
echo "  ./scripts/deploy-to-sandbox.sh --blueprint $BUNDLE_DIR/$BUNDLE_NAME"
