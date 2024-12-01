# FHIR Tooling Additions

This document provides details on additional FHIR tools being integrated into our Epic FHIR workflow to enhance data quality, validation, and profiling capabilities.

## FHIR Shorthand (FSH) & Sushi

### Overview
[FHIR Shorthand (FSH)](https://build.fhir.org/ig/HL7/fhir-shorthand/) is a domain-specific language for defining FHIR profiles, extensions, and other artifacts in a concise, human-readable format. [Sushi](https://github.com/FHIR/sushi) is the official compiler that transforms FSH files into FHIR conformance resources.

### Benefits for Epic FHIR Integration
1. **Simplified Profile Authoring**: Create and maintain Epic-specific FHIR profiles with less verbosity
2. **Version Control Friendly**: FSH files are text-based and diff well in Git
3. **Consistent Constraints**: Standardize data expectations across the organization
4. **Implementation Guide Creation**: Generate IG documentation for Epic integration
5. **Enhanced Interoperability**: Clearly document extensions and constraints

### Installation Requirements
```bash
# Install Node.js (v14+) and npm
brew install node

# Install Sushi globally
npm install -g fsh-sushi

# Verify installation
sushi --version
```

### Directory Structure
```
epic_fhir_integration/
└── profiles/
    ├── fsh/                  # FSH source files
    │   ├── aliases.fsh       # Common prefixes and URI definitions
    │   ├── extensions.fsh    # Custom extensions
    │   ├── patient.fsh       # Patient profile
    │   ├── encounter.fsh     # Encounter profile
    │   └── ...               # Other resource profiles
    ├── ig-data/              # Implementation guide content
    ├── input/                # Sushi input files
    │   └── fsh/              # Symlinked to ../fsh
    ├── output/               # Generated FHIR artifacts
    │   ├── StructureDefinition/
    │   └── ...
    └── sushi-config.yaml     # Sushi configuration
```

### Sample FSH Profile
```
Profile: EpicPatient
Parent: Patient
Id: epic-patient
Title: "Epic Patient Profile"
Description: "Patient profile for Epic FHIR integration"

* identifier 1..*
* identifier ^slicing.discriminator.type = #pattern
* identifier ^slicing.discriminator.path = "system"
* identifier ^slicing.rules = #open
* identifier ^slicing.description = "Slice based on identifier system"

* identifier contains mrn 1..1
* identifier[mrn].system = "urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.0" (exactly)
* identifier[mrn].type.coding.system = "http://terminology.hl7.org/CodeSystem/v2-0203"
* identifier[mrn].type.coding.code = #MR
```

### Build Process
```bash
#!/bin/bash
# Script to compile FSH definitions to FHIR artifacts

cd epic_fhir_integration/profiles
sushi .
echo "FSH compilation complete. Output in ./output/"
```

## HAPI FHIR Validator

### Overview
[HAPI FHIR Validator](https://hapifhir.io/hapi-fhir/docs/validation/instance_validator.html) is a powerful tool for validating FHIR resources against the FHIR specification and custom profiles. It can be used as a Java library or standalone CLI tool.

### Benefits for Epic FHIR Integration
1. **Data Quality Assurance**: Validate Epic FHIR resources before processing
2. **Custom Profile Validation**: Ensure conformance to our specific profiles
3. **Error Detection**: Identify issues early in the pipeline
4. **Compliance Verification**: Ensure regulatory and standards compliance
5. **Integration Testing**: Test resource validity programmatically

### Installation Options

#### Java Library
Add to `pom.xml` (if using Maven) or `build.gradle` (if using Gradle):
```xml
<!-- HAPI FHIR Validator -->
<dependency>
  <groupId>ca.uhn.hapi.fhir</groupId>
  <artifactId>hapi-fhir-validation</artifactId>
  <version>6.6.0</version>
</dependency>
<dependency>
  <groupId>ca.uhn.hapi.fhir</groupId>
  <artifactId>hapi-fhir-structures-r4</artifactId>
  <version>6.6.0</version>
</dependency>
```

#### CLI Tool
```bash
# Download the validator
curl -L https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar \
  -o validator_cli.jar

# Run validation (example)
java -jar validator_cli.jar input.json -version 4.0.1 -ig ./profiles/output/
```

### Python Integration
We'll create a Python wrapper to utilize the HAPI FHIR Validator:

```python
# epic_fhir_integration/validation/validator.py
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

class FHIRValidator:
    """Wrapper for HAPI FHIR Validator tool."""
    
    def __init__(self, validator_path: str, ig_path: Optional[str] = None):
        """
        Initialize the FHIR validator.
        
        Args:
            validator_path: Path to the validator_cli.jar file
            ig_path: Path to the implementation guide directory
        """
        self.validator_path = Path(validator_path)
        self.ig_path = Path(ig_path) if ig_path else None
        
        if not self.validator_path.exists():
            raise FileNotFoundError(f"Validator not found at {validator_path}")
        
        if self.ig_path and not self.ig_path.exists():
            raise FileNotFoundError(f"Implementation guide not found at {ig_path}")
    
    def validate(self, resource_path: str, fhir_version: str = "4.0.1") -> Dict:
        """
        Validate a FHIR resource against profiles.
        
        Args:
            resource_path: Path to the FHIR resource file
            fhir_version: FHIR version to validate against
            
        Returns:
            Dict containing validation results
        """
        cmd = [
            "java", "-jar", str(self.validator_path),
            resource_path,
            "-version", fhir_version,
            "-output", "json"
        ]
        
        if self.ig_path:
            cmd.extend(["-ig", str(self.ig_path)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse validator output",
                "output": result.stdout,
                "stderr": result.stderr
            }
    
    def validate_string(self, resource_json: str, fhir_version: str = "4.0.1") -> Dict:
        """
        Validate a FHIR resource string against profiles.
        
        Args:
            resource_json: JSON string of the FHIR resource
            fhir_version: FHIR version to validate against
            
        Returns:
            Dict containing validation results
        """
        # Write resource to temporary file
        temp_file = Path("temp_resource.json")
        with open(temp_file, "w") as f:
            f.write(resource_json)
        
        try:
            return self.validate(str(temp_file), fhir_version)
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()

    def is_valid(self, resource_path: Union[str, Dict]) -> bool:
        """
        Check if a FHIR resource is valid.
        
        Args:
            resource_path: Path to the FHIR resource file or resource dict
            
        Returns:
            True if valid, False otherwise
        """
        if isinstance(resource_path, dict):
            result = self.validate_string(json.dumps(resource_path))
        else:
            result = self.validate(resource_path)
        
        # Check for errors in validation result
        return result.get("success", False)
```

### Validation Pipeline Integration

We'll integrate validation at multiple points in the Epic FHIR pipeline:

1. **Extraction Phase**: Validate resources as they are fetched from Epic
2. **Pre-Processing**: Validate resources before transformation
3. **Post-Processing**: Ensure transformed resources are still valid
4. **Export Validation**: Validate resources before storage or transmission

#### Command-line Interface
```python
# epic_fhir_integration/cli/validate.py
import click
import json
from pathlib import Path
from epic_fhir_integration.validation.validator import FHIRValidator

@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--profile', '-p', help='Path to specific profile to validate against')
@click.option('--ig', help='Path to implementation guide directory')
@click.option('--output', '-o', help='Output file for validation results')
def validate(input_path, profile, ig, output):
    """Validate FHIR resources against profiles."""
    validator = FHIRValidator(
        validator_path="path/to/validator_cli.jar",
        ig_path=ig
    )
    
    path = Path(input_path)
    if path.is_file():
        # Validate single file
        result = validator.validate(str(path))
        click.echo(f"Validation {'successful' if result.get('success', False) else 'failed'}")
        
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            click.echo(json.dumps(result, indent=2))
    
    elif path.is_dir():
        # Validate all JSON files in directory
        results = {}
        for file in path.glob('**/*.json'):
            results[str(file)] = validator.validate(str(file))
        
        success_count = sum(1 for r in results.values() if r.get('success', False))
        click.echo(f"Validated {len(results)} files, {success_count} successful")
        
        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
        else:
            click.echo(json.dumps(results, indent=2))

if __name__ == '__main__':
    validate()
```

## Integration Workflow

### 1. Define Profiles
1. Create FSH definitions for Epic-specific resources
2. Compile to FHIR StructureDefinitions using Sushi
3. Version control the FSH source files and compiled outputs

### 2. Setup Validation
1. Install HAPI FHIR Validator
2. Configure with our profiles
3. Set up validation functions and CLI tools

### 3. Pipeline Integration
1. Add validation steps to the FHIR processing pipeline
2. Create configuration for validation strictness
3. Implement error handling for validation failures

### 4. Continuous Integration
1. Add validation tests to CI pipeline
2. Set up automatic profile generation from FSH
3. Test new profiles against sample data

## Development Roadmap

| Step | Timeframe | Dependencies |
|------|-----------|--------------|
| FSH toolchain setup | 1 week | Node.js |
| Core profile definition | 2 weeks | FSH toolchain |
| HAPI validator setup | 1 week | Java runtime |
| Validation module development | 2 weeks | HAPI validator |
| Pipeline integration | 1-2 weeks | Validation module |
| Testing and refinement | 2 weeks | All components |

## Resources

* [FHIR Shorthand Documentation](https://build.fhir.org/ig/HL7/fhir-shorthand/)
* [Sushi GitHub Repository](https://github.com/FHIR/sushi)
* [HAPI FHIR Validator Documentation](https://hapifhir.io/hapi-fhir/docs/validation/instance_validator.html)
* [FSH School Tutorials](https://fshschool.org/)
* [FHIR Implementation Guide Publisher](https://github.com/FHIR/auto-ig-builder) 