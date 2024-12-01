#!/usr/bin/env bash
# build_wheel_only.sh
# -------------------------------------------------------------
# Simple script that just builds the Python wheel ready for
# Foundry upload.
#
# Usage:
#   ./scripts/build_wheel_only.sh
# -------------------------------------------------------------

set -euo pipefail

# -------- 0. Prerequisites ---------------------------------------------------
command -v python3 >/dev/null || { echo "Python3 not found"; exit 1; }

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

DIST_DIR="$REPO_ROOT/dist"
TEMP_VENV="$REPO_ROOT/.build_venv"

# Ensure dist directory exists
mkdir -p "$DIST_DIR"

# -------- 1. Build Python wheel ---------------------------------------------
echo "[INFO] Creating temporary virtual environment for building wheel..."
python3 -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

echo "[INFO] Installing build package..."
pip install --upgrade build

echo "[INFO] Building wheel..."
python -m build --wheel --outdir "$DIST_DIR"

# Deactivate and clean up the virtual environment
deactivate
rm -rf "$TEMP_VENV"

# -------- 2. Success message -------------------------------------------------
echo ""
echo "🎉 Wheel build complete"
echo "Upload the following file to Foundry (or via CLI):"
# Use find instead of ls to better handle spaces in paths
WHEEL_PATH=$(find "$DIST_DIR" -name "*epic_fhir_integration*.whl" | head -1)
echo "  • $WHEEL_PATH"
echo "-------------------------------------------------------------"
echo "Next steps (manual):"
echo "  foundry repo create epic-fhir-integration"
echo "  cd epic-fhir-integration"
echo "  foundry fs put \"$WHEEL_PATH\""
echo "-------------------------------------------------------------"
echo ""
echo "To build the Docker image separately, use:"
echo "  docker build -t epic-fhir-foundry:latest -f ops/foundry/Dockerfile ."
echo "  docker save epic-fhir-foundry:latest | gzip > epic-fhir-foundry.tar.gz"
echo "-------------------------------------------------------------" 