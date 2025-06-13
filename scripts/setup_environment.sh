#!/bin/bash
# Complete environment setup script for Epic FHIR Integration
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "===== Epic FHIR Integration Environment Setup ====="
echo "Project root: $PROJECT_ROOT"

# Check Python
echo -e "\n===== Checking Python ====="
if command -v python3 >/dev/null 2>&1; then
    python_version=$(python3 --version)
    echo "Found $python_version"
else
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
echo -e "\n===== Setting up Python virtual environment ====="
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
else
    echo "Using existing virtual environment"
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"
echo "Activated virtual environment: $(which python)"

# Install dependencies
echo -e "\n===== Installing Python dependencies ====="
python -m pip install --upgrade pip
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    echo "WARNING: requirements.txt not found!"
fi

# Set up Java environment
echo -e "\n===== Setting up Java environment ====="
source "$PROJECT_ROOT/ops/java/use_java11.sh" || {
    echo "WARNING: Java setup script failed. Some features may not work correctly."
}

# Build Docker images
echo -e "\n===== Building Docker images ====="
if command -v docker >/dev/null 2>&1; then
    echo "Building FHIR Validator image..."
    (cd "$PROJECT_ROOT" && make validator-image)
    
    echo "Building Pathling image..."
    (cd "$PROJECT_ROOT" && make pathling-image)
else
    echo "WARNING: Docker not found. Cannot build images."
    echo "Please install Docker to use FHIR Validator and Pathling services."
fi

# Create data directories if they don't exist
echo -e "\n===== Setting up data directories ====="
mkdir -p "$PROJECT_ROOT/pathling_data"

echo -e "\n===== Setup Complete ====="
echo "To activate this environment in the future, run:"
echo "source $PROJECT_ROOT/venv/bin/activate"
echo "source $PROJECT_ROOT/ops/java/use_java11.sh" 