#!/usr/bin/env bash
# prepare_foundry_upload.sh
# -------------------------------------------------------------
# One-click script that produces **exactly two artefacts** ready
# for Foundry upload:
#   1. dist/epic_fhir_integration-<version>-py3-none-any.whl
#   2. epic-fhir-foundry.tar.gz (container image tarball)
#
# Usage:
#   ./scripts/prepare_foundry_upload.sh [IMAGE_TAG]
#
# If IMAGE_TAG is omitted the current git short-sha is used.
# -------------------------------------------------------------

set -euo pipefail

# -------- 0. Prerequisites ---------------------------------------------------
command -v docker  >/dev/null || { echo "Docker not found";        exit 1; }
command -v python3 >/dev/null || { echo "Python3 not found";       exit 1; }

# Optional: ensure GNU make is present (only if you rely on make targets)
if ! command -v make >/dev/null; then
  echo "[WARN] make not found – falling back to direct docker build"
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

IMAGE_TAG="${1:-$(git rev-parse --short HEAD)}"
IMAGE_NAME="epic-fhir-foundry:$IMAGE_TAG"
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

# -------- 2. Build container image ------------------------------------------
if [[ -f Makefile ]] && command -v make >/dev/null; then
  echo "[INFO] Building image via Makefile target 'foundry-img'..."
  make foundry-img
  
  # Tag the image with our custom tag since Makefile builds with 'latest'
  echo "[INFO] Tagging image as $IMAGE_NAME"
  docker tag epic-fhir-foundry:latest "$IMAGE_NAME"
else
  echo "[INFO] Building image via docker build..."
  docker build -t "$IMAGE_NAME" -f ops/foundry/Dockerfile .
fi

echo "[INFO] Image built: $IMAGE_NAME"

# -------- 3. Save image to tar.gz -------------------------------------------
TAR_NAME="epic-fhir-foundry.tar.gz"

echo "[INFO] Saving image to $TAR_NAME..."
docker save "$IMAGE_NAME" | gzip > "$TAR_NAME"

echo "[INFO] Image saved to $TAR_NAME"

# -------- 4. Success message -------------------------------------------------
echo ""
echo "🎉 Build complete"
echo "Upload the following files to Foundry (or via CLI):"
echo "  • $(ls $DIST_DIR/*epic_fhir_integration*.whl 2>/dev/null | head -1)"
echo "  • $REPO_ROOT/$TAR_NAME"
echo "-------------------------------------------------------------"
echo "Next steps (manual):"
echo "  foundry repo create epic-fhir-integration"
echo "  cd epic-fhir-integration"
echo "  foundry fs put $(ls $DIST_DIR/*epic_fhir_integration*.whl 2>/dev/null | head -1)"
echo "  foundry container-image import $REPO_ROOT/$TAR_NAME --name epic-fhir-tools"
echo "-------------------------------------------------------------" 