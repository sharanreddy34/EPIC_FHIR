# Bronze to Silver Transformation Fix

## Problem Overview

The transformation from the bronze to silver layer was failing due to several issues:

1. **File Format Mismatch**: The extraction saved data in JSON format, but the transformation code expected Delta format.
2. **Path Resolution Issues**: Paths to bronze files were not being correctly resolved in some cases.
3. **Error Handling**: Insufficient error handling prevented diagnosing transformation failures.
4. **Schema Compatibility**: The transformation process wasn't validating that the bronze data had the expected structure.

## Changes Implemented

### 1. Improved File Format Detection

The `transform_resource` function in `fhir_pipeline/pipelines/transform_load.py` now automatically detects and handles files in multiple formats:

- **JSON files**: The most common format from the extraction process
- **Parquet files**: Used in some cases for optimized storage
- **Delta tables**: Production format for fully managed datasets

Detection is done by checking file extensions and directory structure (`_delta_log` directory for Delta tables).

### 2. Enhanced Path Resolution

- Added the `validate_paths` function to normalize and validate input and output paths
- Handles trailing slashes and other common path issues
- Validates that the input path exists before attempting transformation
- Creates output directories automatically if they don't exist
- Case-insensitive resource directory lookup to handle resource types with inconsistent casing

### 3. Robust Error Handling

- Added detailed exception handling with specific error messages
- Enhanced tracing with stack traces for debugging
- Better logging of intermediate steps during transformation
- Sample data collection and logging when errors occur to help diagnose issues

### 4. Diagnostic Capabilities

The `diagnose_input_files` function provides comprehensive diagnostics about the bronze data:

- File counts by type (JSON, Parquet, Delta)
- Sample file information (size, structure, entry counts)
- Detailed error reporting for problematic files
- Structure validation for JSON files to ensure they match FHIR format expectations

### 5. E2E Test Improvements

The `transform_resources` method in `e2e_test_fhir_pipeline.py` now:

- Checks for bronze file compatibility before running transformation
- Provides detailed logging of file types and structures
- Has improved error messages for transformation failures
- Can fall back to command-line tools if Spark is not available

## Usage

When running the pipeline, it will automatically detect and handle various file formats. For detailed diagnostics, use the `--verbose` flag:

```bash
python fhir_pipeline/pipelines/transform_load.py --resource-types Patient Observation --verbose
```

For strict format checking, the e2e test now supports a `--strict` flag:

```bash
python e2e_test_fhir_pipeline.py --strict
```

## File Format Compatibility

The system now handles these file scenarios:

1. **Bronze JSON → Silver Delta**: Original extraction saves as JSON, transformation loads JSON and writes as Delta
2. **Bronze Parquet → Silver Delta**: Optimized extraction with Parquet, transformation loads Parquet and writes as Delta
3. **Bronze Delta → Silver Delta**: Production setup with Delta tables throughout

## Troubleshooting

If transformation fails, check:

1. The bronze layer has valid FHIR data (either bundle or direct resource format)
2. File paths are correct and accessible
3. Resource types in the transformation command match those in the bronze layer
4. Logs for detailed diagnostic information about file formats and counts

## Metrics and Monitoring

The transformation now logs metrics about each stage:

- Input and output record counts
- Processing time for each resource type
- Data loss percentage (if any records are dropped during transformation)
- File counts and sizes in both bronze and silver layers 