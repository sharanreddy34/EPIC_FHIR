#!/bin/bash

# Real-world testing script for Epic FHIR Integration

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
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
      SINGLE_TEST="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--api | --local] [--force-fetch] [--verbose] [--test test_file.py]"
      exit 1
      ;;
  esac
done

# Create necessary directories
mkdir -p "$TEST_DATA_DIR"
mkdir -p "$TEST_OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# Configure logging
if [ "$VERBOSE" = true ]; then
  export PYTHONUNBUFFERED=1
  PYTEST_OPTS="-v"
else
  PYTEST_OPTS=""
fi

# Determine test mode
if [ "$USE_API" = true ] && [ "$USE_LOCAL" = true ]; then
  echo "Error: Cannot use both --api and --local flags simultaneously"
  exit 1
elif [ "$USE_API" = true ]; then
  echo "Running tests directly against Epic FHIR API"
  export RUN_LIVE_API_TESTS=true
  unset EPIC_TEST_DATA_PATH
elif [ "$USE_LOCAL" = true ]; then
  echo "Running tests with local test data"
  export EPIC_TEST_DATA_PATH="$TEST_DATA_DIR"
  unset RUN_LIVE_API_TESTS
  
  # Check if we need to fetch/refresh test data
  if [ "$FORCE_FETCH" = true ] || [ ! -d "$TEST_DATA_DIR/Patient" ]; then
    echo "Fetching test data (this may take a few minutes)..."
    python "$ROOT_DIR/scripts/fetch_test_data.py" --config "$CONFIG_FILE" --output "$TEST_DATA_DIR" --deidentify
  fi
else
  echo "Error: Must specify either --api or --local flag"
  echo "Usage: $0 [--api | --local] [--force-fetch] [--verbose] [--test test_file.py]"
  exit 1
fi

# Set environment variables
export EPIC_CONFIG_PATH="$CONFIG_FILE"
export TEST_OUTPUT_DIR="$TEST_OUTPUT_DIR"

# Run the specified test or all tests
echo "Starting tests at $(date)"
echo "------------------------------------"

TEST_PATH="$ROOT_DIR/epic_fhir_integration/tests/live"

if [ -n "$SINGLE_TEST" ]; then
  if [[ "$SINGLE_TEST" != test_*.py ]]; then
    SINGLE_TEST="test_${SINGLE_TEST}"
  fi
  echo "Running single test: $SINGLE_TEST"
  python -m pytest "$TEST_PATH/$SINGLE_TEST" $PYTEST_OPTS | tee -a "$LOG_FILE"
else
  echo "Running all tests"
  python -m pytest "$TEST_PATH" $PYTEST_OPTS | tee -a "$LOG_FILE"
fi

TEST_STATUS=$?

echo "------------------------------------"
echo "Tests completed at $(date)"
echo "Log file saved to: $LOG_FILE"

# Generate test report
if [ -x "$ROOT_DIR/scripts/generate_test_report.py" ]; then
  echo "Generating test report..."
  python "$ROOT_DIR/scripts/generate_test_report.py" --input-dir "$TEST_OUTPUT_DIR" --log-dir "$LOG_DIR" --output "$TEST_OUTPUT_DIR/test_report.md"
fi

exit $TEST_STATUS 