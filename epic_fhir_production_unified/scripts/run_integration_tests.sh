#!/bin/bash

# Script to run all integration tests for the Epic FHIR Integration project

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Ensure all dependencies are installed
echo "Checking dependencies..."
pip install -e "[$PROJECT_ROOT]"

# Run all integration tests
echo "Running integration tests..."
cd "$PROJECT_ROOT"
python -m pytest epic_fhir_integration/tests/integration/ -v

# Run performance tests (skipped by default)
if [ "$1" == "--with-perf" ]; then
    echo "Running performance benchmarks..."
    python -m pytest epic_fhir_integration/tests/perf/ -v
fi

# Run end-to-end tests (skipped by default)
if [ "$1" == "--with-e2e" ] || [ "$2" == "--with-e2e" ]; then
    echo "Running end-to-end tests..."
    python -m pytest epic_fhir_integration/tests/live/ -v
fi

echo "Testing complete!" 