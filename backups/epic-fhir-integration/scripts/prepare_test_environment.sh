#!/bin/bash
# Script to prepare the complete FHIR testing environment
# This prepares all necessary components for advanced FHIR tools testing

set -e # Exit on error

echo "Preparing test environment for Advanced FHIR Tools testing..."

# 1. Create necessary directory structure if not exists
echo "Creating directory structure..."
mkdir -p epic-fhir-integration/epic_fhir_integration/profiles/epic
mkdir -p epic-fhir-integration/test_data/bronze
mkdir -p epic-fhir-integration/test_data/silver
mkdir -p epic-fhir-integration/test_data/gold

# 2. Check Python dependencies
echo "Checking Python dependencies..."
pip install -e ./epic-fhir-integration

# 3. Check for Java (required for validation and Pathling)
echo "Checking for Java..."
if which java >/dev/null; then
    java_version=$(java -version 2>&1 | head -n 1)
    echo "Found Java: $java_version"
else
    echo "WARNING: Java not found. Some validation features may not work."
fi

# 4. Check for Node.js and Sushi (for FSH)
echo "Checking for Node.js and FHIR Shorthand tools..."
if which node >/dev/null; then
    node_version=$(node --version)
    echo "Found Node.js: $node_version"
    
    # Check for Sushi
    if which sushi >/dev/null; then
        sushi_version=$(sushi --version)
        echo "Found Sushi: $sushi_version"
    else
        echo "Installing Sushi (FHIR Shorthand compiler)..."
        npm install -g fsh-sushi
    fi
else
    echo "WARNING: Node.js not found. FSH compilation features may not work."
fi

# 5. Download FHIR Validator if needed
echo "Checking for FHIR Validator..."
validator_path="$HOME/fhir/validator_cli.jar"
if [ ! -f "$validator_path" ]; then
    echo "Downloading FHIR Validator..."
    mkdir -p "$HOME/fhir"
    curl -L https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar -o "$validator_path"
    echo "FHIR Validator downloaded to $validator_path"
fi

# 6. Check Docker for Pathling
echo "Checking Docker for Pathling service..."
if which docker >/dev/null; then
    docker_version=$(docker --version)
    echo "Found Docker: $docker_version"
    
    # Check docker-compose
    if which docker-compose >/dev/null; then
        docker_compose_version=$(docker-compose --version)
        echo "Found docker-compose: $docker_compose_version"
    else
        echo "WARNING: docker-compose not found. Pathling Docker mode may not work."
    fi
else
    echo "WARNING: Docker not found. Pathling Docker mode will not work."
fi

# 7. Create test sample FHIR resources
echo "Creating sample FHIR resources for testing..."

# Create Bronze tier Patient sample
cat > epic-fhir-integration/test_data/bronze/patient.json << 'EOF'
{
  "resourceType": "Patient",
  "id": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
  "name": [
    {
      "use": "official",
      "family": "Smith",
      "given": ["John", "Samuel"]
    }
  ],
  "telecom": [
    {
      "system": "phone",
      "value": "555-123-4567"
    },
    {
      "system": "email",
      "value": "john.smith@example.com"
    }
  ],
  "gender": "male",
  "birthDate": "1970-01-25",
  "address": [
    {
      "line": ["123 Main St"],
      "city": "Anytown",
      "state": "CA",
      "postalCode": "12345"
    }
  ],
  "active": true
}
EOF

# Create Silver tier Patient sample (improved)
cat > epic-fhir-integration/test_data/silver/patient.json << 'EOF'
{
  "resourceType": "Patient",
  "id": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
  "meta": {
    "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
    "extension": [
      {
        "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
        "valueString": "silver"
      }
    ]
  },
  "identifier": [
    {
      "system": "http://hospital.example.org/identifiers/patient",
      "value": "12345"
    }
  ],
  "name": [
    {
      "use": "official",
      "family": "Smith",
      "given": ["John", "Samuel"]
    }
  ],
  "telecom": [
    {
      "system": "phone",
      "value": "555-123-4567",
      "use": "home"
    },
    {
      "system": "email",
      "value": "john.smith@example.com"
    }
  ],
  "gender": "male",
  "birthDate": "1970-01-25",
  "address": [
    {
      "use": "home",
      "line": ["123 Main St"],
      "city": "Anytown",
      "state": "CA",
      "postalCode": "12345",
      "country": "US"
    }
  ],
  "active": true
}
EOF

# Create Gold tier Patient sample (US Core compliant)
cat > epic-fhir-integration/test_data/gold/patient.json << 'EOF'
{
  "resourceType": "Patient",
  "id": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
  "meta": {
    "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
    "extension": [
      {
        "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
        "valueString": "gold"
      }
    ]
  },
  "identifier": [
    {
      "system": "http://hospital.example.org/identifiers/patient",
      "value": "12345"
    },
    {
      "system": "http://hl7.org/fhir/sid/us-ssn",
      "value": "123-45-6789"
    }
  ],
  "name": [
    {
      "use": "official",
      "family": "Smith",
      "given": ["John", "Samuel"],
      "suffix": ["Jr."]
    }
  ],
  "telecom": [
    {
      "system": "phone",
      "value": "555-123-4567",
      "use": "home"
    },
    {
      "system": "email",
      "value": "john.smith@example.com"
    }
  ],
  "gender": "male",
  "birthDate": "1970-01-25",
  "address": [
    {
      "use": "home",
      "line": ["123 Main St"],
      "city": "Anytown",
      "state": "CA",
      "postalCode": "12345",
      "country": "US"
    }
  ],
  "extension": [
    {
      "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
      "extension": [
        {
          "url": "ombCategory",
          "valueCoding": {
            "system": "urn:oid:2.16.840.1.113883.6.238",
            "code": "2106-3",
            "display": "White"
          }
        },
        {
          "url": "text",
          "valueString": "White"
        }
      ]
    },
    {
      "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
      "extension": [
        {
          "url": "ombCategory",
          "valueCoding": {
            "system": "urn:oid:2.16.840.1.113883.6.238",
            "code": "2186-5",
            "display": "Not Hispanic or Latino"
          }
        },
        {
          "url": "text",
          "valueString": "Not Hispanic or Latino"
        }
      ]
    }
  ],
  "active": true,
  "communication": [
    {
      "language": {
        "coding": [
          {
            "system": "urn:ietf:bcp:47",
            "code": "en",
            "display": "English"
          }
        ],
        "text": "English"
      },
      "preferred": true
    }
  ]
}
EOF

# Create sample Observation (Bronze)
cat > epic-fhir-integration/test_data/bronze/observation.json << 'EOF'
{
  "resourceType": "Observation",
  "id": "obs-1",
  "status": "final",
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "8480-6",
        "display": "Systolic blood pressure"
      }
    ]
  },
  "subject": {
    "reference": "Patient/T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
  },
  "effectiveDateTime": "2024-05-15T09:30:00Z",
  "valueQuantity": {
    "value": 120,
    "unit": "mmHg",
    "system": "http://unitsofmeasure.org",
    "code": "mm[Hg]"
  }
}
EOF

# Create sample Observation (Gold)
cat > epic-fhir-integration/test_data/gold/observation.json << 'EOF'
{
  "resourceType": "Observation",
  "id": "obs-1",
  "meta": {
    "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-blood-pressure"],
    "extension": [
      {
        "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
        "valueString": "gold"
      }
    ]
  },
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/observation-category",
          "code": "vital-signs",
          "display": "Vital Signs"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "85354-9",
        "display": "Blood pressure panel with all children optional"
      }
    ],
    "text": "Blood pressure panel"
  },
  "subject": {
    "reference": "Patient/T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
  },
  "effectiveDateTime": "2024-05-15T09:30:00Z",
  "performer": [
    {
      "reference": "Practitioner/practitioner-1",
      "display": "Dr. Jane Smith"
    }
  ],
  "component": [
    {
      "code": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": "8480-6",
            "display": "Systolic blood pressure"
          }
        ],
        "text": "Systolic blood pressure"
      },
      "valueQuantity": {
        "value": 120,
        "unit": "mmHg",
        "system": "http://unitsofmeasure.org",
        "code": "mm[Hg]"
      }
    },
    {
      "code": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": "8462-4",
            "display": "Diastolic blood pressure"
          }
        ],
        "text": "Diastolic blood pressure"
      },
      "valueQuantity": {
        "value": 80,
        "unit": "mmHg",
        "system": "http://unitsofmeasure.org",
        "code": "mm[Hg]"
      }
    }
  ]
}
EOF

# Create a simple FSH profile for Pathling
mkdir -p epic-fhir-integration/epic_fhir_integration/profiles/epic
cat > epic-fhir-integration/epic_fhir_integration/profiles/epic/Patient.fsh << 'EOF'
Profile: EpicPatient
Parent: Patient
Id: epic-patient
Title: "Epic Patient Profile"
Description: "Profile for patients in the Epic FHIR Integration."

* identifier 1..*
* name 1..*
* gender 1..1
* birthDate 1..1
* telecom 0..*
* address 0..*
EOF

cat > epic-fhir-integration/epic_fhir_integration/profiles/epic/sushi-config.yaml << 'EOF'
id: epic-fhir-integration
canonical: http://atlaspalantir.com/epic-fhir
version: 0.1.0
name: EpicFHIRIntegration
title: Epic FHIR Integration Profiles
status: active
publisher: Atlas Palantir
contact:
  - name: Atlas Palantir
    telecom:
      - system: email
        value: support@atlaspalantir.com
description: Profiles for Epic FHIR Integration
license: CC0-1.0
fhirVersion: 4.0.1
parameters:
  apply-contact: true
  apply-jurisdiction: true
  apply-publisher: true
  apply-version: true
EOF

# Create a config file with mock credentials for testing
mkdir -p epic-fhir-integration/config
cat > epic-fhir-integration/config/test_config.json << 'EOF'
{
  "client_id": "test_client_id",
  "fhir_base_url": "https://apporchard.epic.com/interconnect-aocurprd-oauth/api/FHIR/R4",
  "token_url": "https://apporchard.epic.com/interconnect-aocurprd-oauth/oauth2/token",
  "private_key_path": "secrets/private_key.pem",
  "private_key_password": null
}
EOF

echo "Creating placeholder for private key..."
mkdir -p epic-fhir-integration/secrets
touch epic-fhir-integration/secrets/private_key.pem
echo "Note: You need to replace this with a real private key for actual API testing"

# 8. Create a runner script for all tests
echo "Creating test runner script..."
cat > epic-fhir-integration/scripts/run_all_tests.sh << 'EOF'
#!/bin/bash
# Run all advanced FHIR tools tests

set -e  # Exit on error

# Directory where test outputs will be stored
OUTPUT_DIR="fhir_test_output_$(date +%Y%m%d_%H%M%S)"

echo "Running all FHIR tests with output to $OUTPUT_DIR"

# Run main E2E test
echo "----- Running Advanced FHIR Tools E2E Test -----"
python epic-fhir-integration/scripts/advanced_fhir_tools_e2e_test.py --output-dir $OUTPUT_DIR --debug

# Run data quality tests across tiers
echo "----- Running Data Quality Tests -----"
python epic-fhir-integration/scripts/test_data_quality.py --input-dir epic-fhir-integration/test_data --output-dir $OUTPUT_DIR/quality

# Run validation tests
echo "----- Running Validation Tests -----"
python epic-fhir-integration/scripts/test_validation.py --input-dir epic-fhir-integration/test_data --output-dir $OUTPUT_DIR/validation

echo "All tests completed. Results are in $OUTPUT_DIR"
EOF
chmod +x epic-fhir-integration/scripts/run_all_tests.sh

# 9. Create data quality test script
echo "Creating data quality test script..."
cat > epic-fhir-integration/scripts/test_data_quality.py << 'EOF'
#!/usr/bin/env python3
"""
Data Quality Test Script for FHIR Resources

This script tests the quality of FHIR resources across Bronze, Silver, and Gold tiers.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("data_quality_test")

from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
from epic_fhir_integration.validation.validator import FHIRValidator

class DataQualityTest:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.fhirpath_adapter = FHIRPathAdapter()
        self.validator = FHIRValidator()
        
        # Results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tiers": {}
        }
    
    def load_resources(self, tier):
        """Load resources for a specific tier."""
        tier_dir = self.input_dir / tier
        if not tier_dir.exists():
            logger.warning(f"Directory not found for tier: {tier}")
            return {}
        
        resources = {}
        for file_path in tier_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    resource = json.load(f)
                    resource_type = resource.get("resourceType")
                    if resource_type:
                        if resource_type not in resources:
                            resources[resource_type] = []
                        resources[resource_type].append(resource)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        return resources
    
    def test_tier(self, tier):
        """Test resources for a specific tier."""
        logger.info(f"Testing {tier} tier")
        
        resources = self.load_resources(tier)
        if not resources:
            logger.warning(f"No resources found for tier: {tier}")
            self.results["tiers"][tier] = {
                "resource_count": 0,
                "overall_quality": 0,
                "validation_results": {}
            }
            return
        
        # Count resources
        resource_counts = {k: len(v) for k, v in resources.items()}
        total_count = sum(resource_counts.values())
        
        # Validate resources
        validation_results = {}
        for resource_type, resources_list in resources.items():
            validation_results[resource_type] = []
            for resource in resources_list:
                result = self.validator.validate(resource)
                validation_results[resource_type].append({
                    "resource_id": resource.get("id", "unknown"),
                    "is_valid": result.is_valid,
                    "error_count": len(result.get_errors()),
                    "warning_count": len(result.get_warnings())
                })
        
        # Calculate quality score
        # Simple score: percentage of valid resources
        valid_count = 0
        for results in validation_results.values():
            valid_count += sum(1 for r in results if r["is_valid"])
        
        quality_score = (valid_count / total_count) * 100 if total_count > 0 else 0
        
        # Store results
        self.results["tiers"][tier] = {
            "resource_count": total_count,
            "resource_counts": resource_counts,
            "overall_quality": quality_score,
            "validation_results": validation_results
        }
        
        logger.info(f"{tier} tier: {valid_count}/{total_count} valid resources ({quality_score:.1f}% quality)")
    
    def run_tests(self):
        """Run tests for all tiers."""
        # Test each tier
        self.test_tier("bronze")
        self.test_tier("silver")
        self.test_tier("gold")
        
        # Generate report
        report_file = self.output_dir / "data_quality_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate Markdown report
        md_report = self.output_dir / "data_quality_report.md"
        with open(md_report, "w") as f:
            f.write("# FHIR Data Quality Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Quality Summary\n\n")
            f.write("| Tier | Resource Count | Quality Score |\n")
            f.write("|------|---------------|---------------|\n")
            
            for tier in ["bronze", "silver", "gold"]:
                if tier in self.results["tiers"]:
                    tier_data = self.results["tiers"][tier]
                    count = tier_data["resource_count"]
                    score = tier_data["overall_quality"]
                    f.write(f"| {tier.title()} | {count} | {score:.1f}% |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for tier in ["bronze", "silver", "gold"]:
                if tier in self.results["tiers"]:
                    tier_data = self.results["tiers"][tier]
                    f.write(f"### {tier.title()} Tier\n\n")
                    
                    f.write("**Resource Counts:**\n\n")
                    if "resource_counts" in tier_data:
                        for resource_type, count in tier_data["resource_counts"].items():
                            f.write(f"- {resource_type}: {count}\n")
                    
                    f.write("\n**Validation Results:**\n\n")
                    for resource_type, results in tier_data["validation_results"].items():
                        valid_count = sum(1 for r in results if r["is_valid"])
                        total_count = len(results)
                        f.write(f"- {resource_type}: {valid_count}/{total_count} valid\n")
        
        logger.info(f"Reports generated: {report_file} and {md_report}")
        return self.results

def main():
    parser = argparse.ArgumentParser(description="Test FHIR data quality across tiers")
    parser.add_argument("--input-dir", required=True, help="Input directory containing tier folders")
    parser.add_argument("--output-dir", required=True, help="Output directory for test results")
    
    args = parser.parse_args()
    
    tester = DataQualityTest(args.input_dir, args.output_dir)
    tester.run_tests()

if __name__ == "__main__":
    main()
EOF

# 10. Create validation test script
echo "Creating validation test script..."
cat > epic-fhir-integration/scripts/test_validation.py << 'EOF'
#!/usr/bin/env python3
"""
Validation Test Script for FHIR Resources

This script validates FHIR resources against profiles for each tier.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("validation_test")

from epic_fhir_integration.validation.validator import FHIRValidator

class ValidationTest:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create validators
        self.base_validator = FHIRValidator()  # Basic FHIR R4 validation
        
        # Results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "validation_results": {}
        }
    
    def load_resources(self, tier):
        """Load resources for a specific tier."""
        tier_dir = self.input_dir / tier
        if not tier_dir.exists():
            logger.warning(f"Directory not found for tier: {tier}")
            return {}
        
        resources = {}
        for file_path in tier_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    resource = json.load(f)
                    resource_type = resource.get("resourceType")
                    if resource_type:
                        if resource_type not in resources:
                            resources[resource_type] = []
                        resources[resource_type].append(resource)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        return resources
    
    def validate_resources(self, tier, resources):
        """Validate resources for a specific tier."""
        logger.info(f"Validating {tier} tier resources")
        
        # Validation results
        results = {}
        
        # Validate each resource type
        for resource_type, resources_list in resources.items():
            results[resource_type] = []
            
            for resource in resources_list:
                # Basic FHIR validation
                basic_result = self.base_validator.validate(resource)
                
                # Store results
                resource_id = resource.get("id", "unknown")
                result = {
                    "resource_id": resource_id,
                    "basic_validation": {
                        "is_valid": basic_result.is_valid,
                        "error_count": len(basic_result.get_errors()),
                        "warning_count": len(basic_result.get_warnings())
                    }
                }
                
                # For Gold tier, validate against US Core profiles if specified
                if tier == "gold" and resource.get("meta", {}).get("profile"):
                    profiles = resource["meta"]["profile"]
                    result["profile_validation"] = {}
                    
                    for profile in profiles:
                        # We only log this because we don't have the actual US Core profiles
                        logger.info(f"Resource {resource_id} claims conformance to profile: {profile}")
                        result["profile_validation"][profile] = {
                            "profile_claimed": True
                        }
                
                results[resource_type].append(result)
        
        return results
    
    def run_tests(self):
        """Run validation tests for all tiers."""
        # Test each tier
        for tier in ["bronze", "silver", "gold"]:
            resources = self.load_resources(tier)
            if resources:
                self.results["validation_results"][tier] = self.validate_resources(tier, resources)
        
        # Generate report
        report_file = self.output_dir / "validation_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate Markdown report
        md_report = self.output_dir / "validation_report.md"
        with open(md_report, "w") as f:
            f.write("# FHIR Validation Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Validation Summary\n\n")
            
            for tier in ["bronze", "silver", "gold"]:
                if tier in self.results["validation_results"]:
                    tier_results = self.results["validation_results"][tier]
                    f.write(f"### {tier.title()} Tier\n\n")
                    
                    # Count resources and validation results
                    total_resources = 0
                    valid_resources = 0
                    
                    for resource_type, results in tier_results.items():
                        type_total = len(results)
                        type_valid = sum(1 for r in results if r["basic_validation"]["is_valid"])
                        
                        total_resources += type_total
                        valid_resources += type_valid
                        
                        f.write(f"- {resource_type}: {type_valid}/{type_total} valid\n")
                    
                    # Overall summary
                    percent_valid = (valid_resources / total_resources * 100) if total_resources > 0 else 0
                    f.write(f"\n**Overall:** {valid_resources}/{total_resources} valid ({percent_valid:.1f}%)\n\n")
                    
                    # Profile conformance for Gold tier
                    if tier == "gold":
                        f.write("\n**Profile Conformance:**\n\n")
                        for resource_type, results in tier_results.items():
                            for result in results:
                                if "profile_validation" in result:
                                    resource_id = result["resource_id"]
                                    for profile, profile_result in result["profile_validation"].items():
                                        f.write(f"- {resource_type}/{resource_id}: Claims conformance to {profile}\n")
        
        logger.info(f"Reports generated: {report_file} and {md_report}")
        return self.results

def main():
    parser = argparse.ArgumentParser(description="Validate FHIR resources against profiles")
    parser.add_argument("--input-dir", required=True, help="Input directory containing tier folders")
    parser.add_argument("--output-dir", required=True, help="Output directory for test results")
    
    args = parser.parse_args()
    
    tester = ValidationTest(args.input_dir, args.output_dir)
    tester.run_tests()

if __name__ == "__main__":
    main()
EOF

# Make the scripts executable
chmod +x epic-fhir-integration/scripts/test_data_quality.py
chmod +x epic-fhir-integration/scripts/test_validation.py

echo "Environment preparation complete! You can now run the test suite with:"
echo "./epic-fhir-integration/scripts/run_all_tests.sh" 