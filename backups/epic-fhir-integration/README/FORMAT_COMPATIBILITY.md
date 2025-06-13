# Bronze Layer File Format Compatibility

## Overview
This document explains the file format compatibility between the bronze and silver layers in the FHIR pipeline. The pipeline now supports multiple file formats for bronze data:

- JSON (default from extraction)
- Parquet (alternative format)
- Delta (production format)

## Problem Solved
Previously, the extraction process saved data in JSON format, but the transformation expected Delta format. This mismatch caused transformation failures. 

## Implementation Details

### Format Detection
The transformation code now automatically detects file formats based on:
- File extensions (.json, .parquet)
- Directory structure (_delta_log directory for Delta tables)

### Schema Compatibility
The code handles two primary schema scenarios:
1. **Bundle structure** (most common):
   ```json
   {
     "bundle": {
       "entry": [
         {
           "resource": { ... FHIR resource ... }
         }
       ]
     }
   }
   ```

2. **Direct resource format**:
   ```json
   {
     "resourceType": "Patient",
     ... resource fields ...
   }
   ```

### Compatibility Checks
Compatibility checks have been added to verify file formats before transformation:
- In `run_local_fhir_pipeline.py` - the `check_bronze_file_compatibility` function
- In `e2e_test_fhir_pipeline.py` - the `check_bronze_format_compatibility` method

## Code Changes
The following files were modified to implement format compatibility:

1. `fhir_pipeline/pipelines/transform_load.py`
   - Added format detection logic
   - Added support for reading JSON, Parquet, and Delta formats
   - Added bundle and resource structure validation

2. `pipelines/03_transform_load.py`
   - Added format detection
   - Improved error handling for different formats
   - Added direct resource format support

3. `scripts/run_local_fhir_pipeline.py`
   - Added format compatibility check
   - Added detailed format validation

4. `e2e_test_fhir_pipeline.py`
   - Added format compatibility check before transformation
   - Improved error handling

## Testing
When running the pipeline:
1. The code will first check if the formats are compatible
2. It will log any potential issues
3. It will then attempt to process the data regardless of format warnings since the transform code is now robust enough to handle different formats

## Future Work
In the future, we could:
1. Add format conversion utilities
2. Improve format validation with schema validation
3. Add cross-format migration tools 