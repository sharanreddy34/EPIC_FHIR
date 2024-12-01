#!/bin/bash
# Script to run all FHIR tools prototypes

echo "==============================="
echo "FHIR Tools Evaluation Prototype Runner"
echo "==============================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install common dependencies
echo "Installing common dependencies..."
pip install -r requirements.txt

# Run FHIRPath prototype
echo ""
echo "==============================="
echo "Running FHIRPath prototype..."
echo "==============================="
echo "Installing fhirpath..."
pip install fhirpath
echo ""
echo "Running fhirpath_prototype.py..."
python fhirpath/fhirpath_prototype.py

# Run FHIR-PYrate prototype
echo ""
echo "==============================="
echo "Running FHIR-PYrate prototype..."
echo "==============================="
echo "Installing fhir-pyrate..."
pip install fhir-pyrate
echo ""
echo "Running fhir_pyrate_prototype.py..."
python fhir-pyrate/fhir_pyrate_prototype.py

# Run Pathling prototype
echo ""
echo "==============================="
echo "Running Pathling prototype..."
echo "==============================="
echo "Checking Java version..."
java -version

# Check if we have Java 11+
java_version=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}')
java_major_version=$(echo $java_version | awk -F '.' '{print $1}')

if [ "$java_major_version" -lt 11 ]; then
  echo "Warning: Java version $java_version detected. Pathling requires Java 11 or higher."
  echo "See prototypes/pathling/JAVA_REQUIREMENTS.md for setup instructions."
  echo "Skipping Pathling prototype."
else
  echo "Java $java_version detected. Proceeding with Pathling installation..."
  pip install pathling jpype1
  echo ""
  echo "Running pathling_prototype.py..."
  python pathling/pathling_prototype.py
fi

echo ""
echo "==============================="
echo "All prototypes complete!"
echo "==============================="
echo ""
echo "Next steps:"
echo "1. Review prototype outputs"
echo "2. Complete evaluation templates for each tool"
echo "3. Make integration recommendations"

# Deactivate virtual environment
deactivate 