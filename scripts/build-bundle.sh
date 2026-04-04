#!/usr/bin/env bash
#
# build-bundle.sh — Create a self-contained MilimoClaw plugin bundle
#
# Produces a .tar.gz with dist/, node_modules/, openclaw.plugin.json,
# and package.json — everything needed to run the plugin without any
# build step on the target machine.
#
# Usage:
#   ./scripts/build-bundle.sh              # outputs to dist-bundle/
#   ./scripts/build-bundle.sh --version 2.0.1  # override version
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$ROOT_DIR/milimo"
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

# Read version from package.json if not overridden
if [ -z "$BUNDLE_VERSION" ]; then
  BUNDLE_VERSION=$(node -p "require('$PLUGIN_DIR/package.json').version" 2>/dev/null || echo "0.1.0")
fi

BUNDLE_NAME="milimo-plugin-v${BUNDLE_VERSION}.tar.gz"

echo "============================================"
echo " MilimoClaw Plugin Bundle Builder v${BUNDLE_VERSION}"
echo "============================================"
echo ""

# Step 1: Install ALL dependencies (including devDeps for build)
echo "[1/5] Installing dependencies..."
cd "$PLUGIN_DIR"
npm install --ignore-scripts 2>&1 | tail -3
echo "  ✓ Dependencies installed"

# Step 2: Build TypeScript
echo "[2/5] Building TypeScript..."
npm run build 2>&1 | tail -3
echo "  ✓ TypeScript compiled"

# Step 2b: Prune to production-only dependencies for the bundle
echo "[2b/5] Pruning to production dependencies..."
npm prune --production 2>/dev/null || true
echo "  ✓ Pruned to production only"

# Step 3: Prepare bundle directory
echo "[3/5] Preparing bundle directory..."
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/milimo"

# Copy only what's needed for runtime
cp -r "$PLUGIN_DIR/dist" "$BUNDLE_DIR/milimo/"
cp -r "$PLUGIN_DIR/node_modules" "$BUNDLE_DIR/milimo/"
cp "$PLUGIN_DIR/openclaw.plugin.json" "$BUNDLE_DIR/milimo/"
cp "$PLUGIN_DIR/package.json" "$BUNDLE_DIR/milimo/"

# Write VERSION file
echo "$BUNDLE_VERSION" > "$BUNDLE_DIR/milimo/VERSION"

echo "  ✓ Bundle directory prepared"

# Step 4: Create tar with correct ownership
echo "[4/5] Creating tar archive..."
cd "$BUNDLE_DIR"

# Use --owner and --group to set sandbox ownership at creation time
# This eliminates the need for chown after extraction in the sandbox
tar \
  --owner=sandbox \
  --group=sandbox \
  -czf "$BUNDLE_NAME" \
  milimo/

# Generate SHA256 checksum
sha256sum "$BUNDLE_NAME" > "${BUNDLE_NAME}.sha256"

BUNDLE_SIZE=$(du -h "$BUNDLE_NAME" | cut -f1)
CHECKSUM=$(cat "${BUNDLE_NAME}.sha256" | awk '{print $1}')

echo "  ✓ Archive created: $BUNDLE_SIZE"
echo "  ✓ SHA256: $CHECKSUM"

# Step 5: Cleanup
echo "[5/5] Cleaning up..."
cd "$PLUGIN_DIR"
npm prune --production 2>/dev/null || true
echo "  ✓ Cleanup complete"

echo ""
echo "============================================"
echo " Bundle ready: $BUNDLE_DIR/$BUNDLE_NAME"
echo " Size: $BUNDLE_SIZE"
echo " Checksum: $CHECKSUM"
echo "============================================"
echo ""
echo "Deploy with:"
echo "  ./scripts/deploy-to-sandbox.sh $BUNDLE_DIR/$BUNDLE_NAME"
