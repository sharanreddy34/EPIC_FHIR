#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=false
JUNIT_REPORT=false

# Help message
show_help() {
    echo "FHIR Pipeline Test Runner"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE     Test type to run (all, unit, integration, perf, or a specific file path)"
    echo "  -v, --verbose       Show verbose output"
    echo "  -c, --coverage      Generate coverage report"
    echo "  -j, --junit         Generate JUnit XML reports"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                   # Run all tests"
    echo "  $0 -t unit           # Run unit tests only"
    echo "  $0 -t integration    # Run integration tests only"
    echo "  $0 -t perf           # Run performance tests only"
    echo "  $0 -t auth           # Run auth-related tests only"
    echo "  $0 -c                # Run all tests with coverage"
    echo "  $0 -t unit -c -j     # Run unit tests with coverage and JUnit reports"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -j|--junit)
            JUNIT_REPORT=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# Determine test path based on type
case "$TEST_TYPE" in
    all)
        TEST_PATH="tests"
        ;;
    unit)
        TEST_PATH="tests/unit"
        ;;
    integration)
        TEST_PATH="tests/integration"
        ;;
    perf)
        TEST_PATH="tests/perf"
        ;;
    auth)
        TEST_PATH="tests/unit/test_auth.py"
        ;;
    client)
        TEST_PATH="tests/unit/test_fhir_client.py"
        ;;
    transform)
        TEST_PATH="tests/unit/test_transforms.py tests/unit/test_transformations.py tests/integration/test_transform_pipeline.py"
        ;;
    extract)
        TEST_PATH="tests/integration/test_extract_pipeline.py"
        ;;
    validation)
        TEST_PATH="tests/unit/test_validation.py"
        ;;
    *)
        # Assume it's a specific file or pattern
        TEST_PATH="tests/*/$TEST_TYPE*.py"
        ;;
esac

# Build command
CMD="python -m pytest $TEST_PATH"

# Add options
if [ "$VERBOSE" = true ]; then
    CMD="$CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    CMD="$CMD --cov=fhir_pipeline --cov-report=term --cov-report=html:coverage_report"
fi

if [ "$JUNIT_REPORT" = true ]; then
    CMD="$CMD --junitxml=test-reports/junit.xml"
    mkdir -p test-reports
fi

# Echo command if verbose
if [ "$VERBOSE" = true ]; then
    echo "Running: $CMD"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pytest pytest-cov
else
    source venv/bin/activate
fi

# Run the tests
echo "Running $TEST_TYPE tests..."
eval $CMD

# Print success message
echo ""
if [ "$COVERAGE" = true ]; then
    echo "Coverage report generated in coverage_report/index.html"
fi
echo "✅ Tests completed successfully!" 