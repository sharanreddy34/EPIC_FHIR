#!/bin/bash

# Real-world testing script for Epic FHIR Integration

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$ROOT_DIR/venv"
TEST_DATA_DIR="$ROOT_DIR/test_data"
TEST_OUTPUT_DIR="$ROOT_DIR/test_output"
CONFIG_FILE="$ROOT_DIR/config/live_epic_auth.json"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/real_world_test_$(date +%Y%m%d_%H%M%S).log"

# Parse command line arguments
USE_API=false
USE_LOCAL=false
FORCE_FETCH=false
VERBOSE=false
SINGLE_TEST=""

# Process arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --api)
      USE_API=true
      shift
      ;;
    --local)
      USE_LOCAL=true
      shift
      ;;
    --force-fetch)
      FORCE_FETCH=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --test)
      SINGLE_TEST=$2
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--api] [--local] [--force-fetch] [--verbose] [--test TEST_NAME]"
      exit 1
      ;;
  esac
done

# If neither API nor local is specified, show usage
if [[ "$USE_API" == "false" && "$USE_LOCAL" == "false" ]]; then
  echo "Please specify either --api or --local option"
  echo "Usage: $0 [--api] [--local] [--force-fetch] [--verbose] [--test TEST_NAME]"
  exit 1
fi

# Create necessary directories
mkdir -p "$TEST_DATA_DIR"
mkdir -p "$TEST_OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# Setup logging
exec > >(tee -a "$LOG_FILE") 2>&1

echo "==== Epic FHIR Integration Real-World Testing ===="
echo "Date: $(date)"
echo "Test mode: $([ "$USE_API" == "true" ] && echo "API" || echo "Local")"
echo "Force fetch: $FORCE_FETCH"
echo "Verbose: $VERBOSE"
echo "Single test: ${SINGLE_TEST:-All tests}"
echo "=================================================="

# Check if Python virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found at $VENV_DIR"
  echo "Creating virtual environment..."
  python -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install package in development mode if not already installed
if ! pip show epic-fhir-integration > /dev/null 2>&1; then
  echo "Installing package in development mode..."
  pip install -e "$ROOT_DIR"
fi

# Install test dependencies
echo "Installing test dependencies..."
pip install pytest pytest-cov pytest-xdist

# Fetch test data if needed
if [[ "$USE_LOCAL" == "true" && ("$FORCE_FETCH" == "true" || ! -f "$TEST_DATA_DIR/Patient.json") ]]; then
  echo "Fetching test data..."
  python "$SCRIPT_DIR/fetch_test_data.py" \
    --config "$CONFIG_FILE" \
    --output "$TEST_DATA_DIR" \
    --deidentify
  
  if [ $? -ne 0 ]; then
    echo "Failed to fetch test data"
    exit 1
  fi
fi

# Run tests
RUN_TESTS=()

if [ -z "$SINGLE_TEST" ]; then
  # Run all tests
  RUN_TESTS=(
    "test_resource_coverage.py"
    "test_auth.py"
    "test_pathling_live.py"
    "test_datascience_live.py"
    "test_validation_live.py"
    "test_e2e_live.py"
  )
else
  # Run a single test
  RUN_TESTS=("$SINGLE_TEST")
fi

FAILED_TESTS=()

# Set environment variables for tests
if [ "$USE_API" == "true" ]; then
  export RUN_LIVE_API_TESTS=true
else
  export EPIC_TEST_DATA_PATH="$TEST_DATA_DIR"
fi

export EPIC_CONFIG_PATH="$CONFIG_FILE"
export EPIC_TEST_OUTPUT_DIR="$TEST_OUTPUT_DIR"

# Run each test
for TEST in "${RUN_TESTS[@]}"; do
  echo
  echo "Running test: $TEST"
  echo "=================================================="
  
  PYTEST_ARGS="epic_fhir_integration/tests/live/$TEST -v"
  
  if [ "$VERBOSE" == "true" ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
  fi
  
  python -m pytest $PYTEST_ARGS
  
  if [ $? -ne 0 ]; then
    FAILED_TESTS+=("$TEST")
  fi
  
  echo
  echo "Completed test: $TEST"
  echo "--------------------------------------------------"
done

# Report results
echo
echo "==== Test Results Summary ===="
echo "Total tests: ${#RUN_TESTS[@]}"
echo "Failed tests: ${#FAILED_TESTS[@]}"

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
  echo
  echo "Failed tests:"
  for TEST in "${FAILED_TESTS[@]}"; do
    echo "  - $TEST"
  done
  exit 1
else
  echo
  echo "All tests passed!"
  exit 0
fi 