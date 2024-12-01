#!/bin/bash

# CI Script for running chaos tests to verify resilience
# This script runs network failures simulations and verifies retry behavior

set -e  # Exit on any error

echo "==== Running Epic FHIR API Chaos Tests ===="

# Install dependencies needed for chaos tests
pip install -q pytest pytest-xdist responses requests pandas

# Run the chaos tests and generate a report
pytest -xvs tests/perf/chaos_test.py

# Store test status for later
TEST_STATUS=$?

# Check if report was generated
if [ -f "tests/perf/chaos_report.md" ]; then
    echo "==== Chaos Test Report Generated ===="
    cat tests/perf/chaos_report.md
    
    # If we're in CI, make report available as artifact
    if [ -n "$CI" ] && [ -n "$CI_ARTIFACTS_DIR" ]; then
        mkdir -p "$CI_ARTIFACTS_DIR/reports"
        cp tests/perf/chaos_report.md "$CI_ARTIFACTS_DIR/reports/"
        echo "Report copied to CI artifacts directory"
    fi
else
    echo "WARNING: No chaos test report found!"
fi

echo "==== Chaos tests complete ===="

# Exit with the status from pytest
exit $TEST_STATUS 