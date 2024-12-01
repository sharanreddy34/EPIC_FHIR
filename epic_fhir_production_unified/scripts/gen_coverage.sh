#!/bin/bash
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

# Ensure required directories exist
mkdir -p coverage_report

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pytest pytest-cov coverage
else
    source venv/bin/activate
fi

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest fhir_pipeline \
    --cov=fhir_pipeline \
    --cov-report=term \
    --cov-report=html:coverage_report \
    --cov-report=xml:coverage_report/coverage.xml

# Generate coverage badge
echo "Generating coverage badge..."
COVERAGE_PCT=$(grep -o 'total.*[0-9]\+%' coverage_report/index.html | grep -o '[0-9]\+%' | head -1 | tr -d '%')

echo "Coverage: $COVERAGE_PCT%"

# Create badge JSON
cat > coverage_report/coverage-badge.json << EOF
{
  "schemaVersion": 1,
  "label": "coverage",
  "message": "$COVERAGE_PCT%",
  "color": "$(
    if [ "$COVERAGE_PCT" -lt 50 ]; then
      echo "red"
    elif [ "$COVERAGE_PCT" -lt 80 ]; then
      echo "yellow"
    else
      echo "brightgreen"
    fi
  )"
}
EOF

# Open coverage report
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open coverage_report/index.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux with X11
    if command -v xdg-open > /dev/null; then
        xdg-open coverage_report/index.html
    else
        echo "Coverage report available at: $PWD/coverage_report/index.html"
    fi
else
    # Windows or other
    echo "Coverage report available at: $PWD/coverage_report/index.html"
fi

echo "✅ Coverage report generated successfully!" 