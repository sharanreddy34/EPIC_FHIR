#!/bin/bash

# CI Script for running live smoke tests against Epic sandbox
# This is meant to be run in the Foundry CI environment where secrets are available

set -e  # Exit on any error

echo "==== Running Epic FHIR API Connection Test ===="

# Foundry CI environment variables should be set
if [ -z "$EPIC_BASE_URL" ] || [ -z "$EPIC_CLIENT_ID" ] || [ -z "$EPIC_PRIVATE_KEY" ]; then
    echo "Error: Required environment variables not set."
    echo "Required: EPIC_BASE_URL, EPIC_CLIENT_ID, EPIC_PRIVATE_KEY"
    echo "These should be provided via Foundry secrets"
    exit 1
fi

# If running in CI, make sure pytest is installed
if [ -n "$CI" ]; then
    pip install -q pytest requests
fi

# Run only the connection test to verify API access without full transform
pytest -xvs tests/live/test_epic_sandbox_extract.py::test_connection

echo "==== Connection test complete ===="

# Exit with the status from pytest
exit $? 