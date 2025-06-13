#!/bin/bash

# Script to run real-world tests against Epic FHIR API - Simplified version
# This script skips dependency checks and data fetching

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
CONFIG_FILE="$PROJECT_ROOT/config/live_epic_auth.json"
TEST_DATA_DIR="$PROJECT_ROOT/test_data"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
LOG_FILE="$LOG_DIR/real_world_tests_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "$LOG_FILE"
}

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    log "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Function to run tests
run_tests() {
    local mode=$1
    
    log "Running tests in $mode mode..."
    
    # Set environment variables based on mode
    if [ "$mode" == "api" ]; then
        export RUN_LIVE_API_TESTS=true
        log "Running tests against live Epic FHIR API"
    else
        export EPIC_TEST_DATA_PATH="$TEST_DATA_DIR"
        log "Running tests against local test data at: $TEST_DATA_DIR"
    fi
    
    # Run the minimal FHIRPath test
    log "Running minimal FHIRPath test..."
    python3 "$SCRIPT_DIR/minimal_fhirpath_test.py" 2>&1 | tee -a "$LOG_FILE"
    
    log "Tests completed in $mode mode"
}

# Main script execution
main() {
    log "Starting minimal test execution"
    
    # Check for test data directory
    if [ ! -d "$TEST_DATA_DIR" ]; then
        log "ERROR: Test data directory not found at: $TEST_DATA_DIR"
        exit 1
    fi
    
    # Parse command line arguments
    local mode="local"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --api)
                mode="api"
                shift
                ;;
            --local)
                mode="local"
                shift
                ;;
            *)
                log "Unknown option: $1"
                log "Usage: $0 [--api|--local]"
                exit 1
                ;;
        esac
    done
    
    # Run the tests
    run_tests "$mode"
    
    log "All tests completed"
    log "Log file: $LOG_FILE"
}

# Run the main function with all arguments
main "$@" 