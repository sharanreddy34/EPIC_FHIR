#!/bin/bash
# Script to rename the legacy src directory to avoid import confusion

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Define source and destination paths
SRC_PATH="$REPO_DIR/src"
DEST_PATH="$REPO_DIR/legacy_src"

# Check if src exists
if [ ! -d "$SRC_PATH" ]; then
    echo "Error: src directory not found at $SRC_PATH"
    exit 1
fi

# Check if destination already exists
if [ -d "$DEST_PATH" ]; then
    echo "Error: destination directory already exists at $DEST_PATH"
    echo "Please remove or rename it first"
    exit 1
fi

# Create backup (just in case)
BACKUP_PATH="$REPO_DIR/backups/src_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPO_DIR/backups"
echo "Creating backup at $BACKUP_PATH"
cp -r "$SRC_PATH" "$BACKUP_PATH"

# Rename the directory
echo "Renaming $SRC_PATH to $DEST_PATH"
mv "$SRC_PATH" "$DEST_PATH"

# Create a README.md in the legacy directory
echo "Creating README.md in $DEST_PATH"
cat > "$DEST_PATH/README.md" << EOF
# Legacy Source Code

This directory contains legacy code that is NOT deployed to Foundry.
It is kept for reference only and should not be modified.

The canonical source of code that is deployed to Foundry is in:
- \`transforms-python/src/epic_fhir_integration\`

If you need any utilities from this legacy code, please migrate them
to the transforms-python tree.
EOF

echo "Done!"
echo "The legacy code is now in $DEST_PATH"
echo "A backup was created at $BACKUP_PATH"
echo ""
echo "IMPORTANT: The canonical source of code is now only in transforms-python/src/" 