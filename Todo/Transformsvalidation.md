Epic FHIR Integration - Validation Implementation To-Do List

A. Metrics Collection Infrastructure
[+] Create epic_fhir_integration/metrics/collector.py (as a façade for existing Spark-based metric collection)
[+] Implement record_metric(step, name, value) function (appends to in-memory list)
[+] Implement flush(run_dir) function (converts list to Spark/Pandas DF, writes to existing 'transform_metrics' path in Parquet)
[+] Add atexit handler to ensure metrics are always written (Note: for driver process; Spark executors have own context)
[+] Create __init__.py to make the package importable
[+] Review existing metric categories/schema in 'pipelines/03_transform_load.py' and align; add 'metric_type="SCHEMA"' for schema stats.
[+] Implement metric aggregation for distributed runs (Re-evaluate: Focus on driver-process collection; Spark handles its own aggregation for now)
[+] Add 'metric_version' column to existing 'transform_metrics' schema (e.g., in 'pipelines/03_transform_load.py').
[+] Implement batch metrics recording for high-frequency scenarios

Testing Metrics System
[+] Create unit tests for metrics collector in tests/unit/test_metrics_collector.py (reflecting façade and Spark integration)
[+] Test recording metrics and flushing to file (Parquet via Spark/Pandas DF)
[+] Test handling of different value types (int, float, dict)
[+] Test concurrent metric recording (within driver process scope)
[+] Test metric persistence across process restarts

B. Output Directory Restructuring
Update Directory Structure Logic
[+] Create shared util (e.g., epic_fhir_integration.utils.paths) with get_run_root(output_dir) -> Path function: `output_dir / f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"`
[+] Modify create_directories() in scripts/production_test.py to use `get_run_root()`.
[+] Update create_dataset_structure() in scripts/run_local_fhir_pipeline.py to use `get_run_root()`.
[+] Create standard subdirectories inside each test directory (ensure 'metrics', 'schemas', 'validation' are consistently created by both scripts, extending the 'directories' map):
    directories = {
        "bronze": root_dir / "bronze",
        "silver": root_dir / "silver",
        "gold": root_dir / "gold",
        "logs": root_dir / "logs",
        "reports": root_dir / "reports",
        "metrics": root_dir / "metrics", # Existing path for transform_metrics
        "schemas": root_dir / "schemas",  # Store schema definitions/outputs
        "validation": root_dir / "validation"  # Store validation results (e.g., results.json)
    }
[+] Add run metadata file (run_info.json) with:
    - Start/end timestamps
    - Patient IDs processed
    - Configuration used
    - System environment
    - Version information

Update References to Output Directories
[+] Review all file paths in production_test.py AND run_local_fhir_pipeline.py to use the new structure (via 'directories' map).
[+] Ensure log files go to the test-specific logs directory
[+] Update report generation to use the test-specific reports directory
[+] Add directory structure validation on startup
[+] Implement cleanup of old test directories
[+] Check .yml pipeline files for paths needing parameter updates based on new structure.
[+] Implement disk space monitoring and cleanup

C. Bronze Layer Validation
Enhance Data Extraction
[+] Import and use metrics collector in extract_patient_data() function (in scripts/production_test.py).
[+] After extraction (in scripts/production_test.py), record resource counts:
    for resource_type, resources in patient_data.items():
        record_metric("bronze", f"{resource_type}_count", len(resources))
        record_metric("bronze", f"{resource_type}_bytes", sys.getsizeof(resources)) # If feasible with collector
[+] Record total extraction time as metric
[+] Record API response times and status codes
[+] Track failed API requests and retries
[+] Flush metrics to disk before function returns (via collector's flush)
[+] Implement retry mechanisms for transient failures

Export Resource Schema Information
[+] Create helper function to extract schema information from resources (Re-evaluate: Leverage existing flattening in Spark's transform_resources() in pipelines/03_transform_load.py)
[+] Record schema metrics for each resource type (in Spark's transform_resources()):
    - Use df.agg() for schema stats (field presence, type distributions, null rates, value ranges)
    - Record these stats using `record_metric(metric_type="SCHEMA", ...)`
[+] Save full schema info to metrics directory (Schema stats will go into the main 'transform_metrics' dataset or a dedicated schema metrics file via the collector)
[+] Generate schema evolution report
[+] Track schema violations and warnings

D. Silver Layer Validation
Rewrite Silver Transformation Logic
[+] Replace custom CSV writer with proper pandas-based flattener (Focus on Spark pipeline: transform_bronze_to_silver.py / pipelines/03_transform_load.py. Deprecate or wrap the simple CSV transformation in production_test.py).
    import pandas as pd # For collector internal conversion if needed
    
    def flatten_resource(resources, resource_type): # This logic is mainly in Spark now
        """Convert FHIR resources to flattened DataFrame."""
        # Implementation depends on resource type
        # ...
        return pd.DataFrame(...)
[+] Ensure all resources are processed, not just the recognized ones (Verify in Spark pipeline)
[+] Record pre-transformation row counts as metrics (In Spark pipeline (03_transform_load.py), use `record_metric` for `input_count`. Partially done, ensure consistent collector use).
[+] Add data quality checks:
    - Completeness (non-null values)
    - Consistency (value ranges)
    - Uniqueness (duplicate detection)
    - Referential integrity
[+] Implement error handling for malformed data
[+] Add data profiling statistics

Add Silver Validation
[+] Count rows after transformation and before writing (In Spark pipeline (03_transform_load.py), use `record_metric` for `output_count`. Partially done).
[+] Record silver pre-write metrics for each resource type (Covered by output_count)
[+] Write the data (CSV or Parquet) (Spark pipeline writes Parquet)
[+] Count rows after writing (Covered by output_count metric)
[+] Record silver post-write metrics (Covered by output_count metric)
[+] Compare pre (bronze) and post (silver) counts using metrics from collector and log any discrepancies or emit a validation record/metric.
[+] Validate data types and constraints
[+] Check for data corruption
[+] Flush metrics before function returns (via collector's flush)

E. Gold Layer Validation
Enhance Gold Transformation
[+] Rewrite to process ALL silver files, not just the first one (Verify `scripts/transform_silver_to_gold.py` correctly handles all relevant silver files for each summary type)
[+] Implement proper aggregation logic (instead of file copies) (Verify Spark logic in `pipelines/gold/*` is robust)
[+] Record gold input row counts as metrics for each resource type (In `scripts/transform_silver_to_gold.py`, after loading silver data for a summary, use `record_metric`).
[+] Add business rule validation (Implement in individual `pipelines/gold/*` modules. Emit validation results (pass/fail, details) using `record_metric` or a dedicated validation event to be stored, possibly in `validation` dir).
[+] Implement data quality scoring
[+] Track transformation lineage

Add Gold Validation
[+] Count rows after transformation and before writing (In `scripts/transform_silver_to_gold.py`, after creating `summary_df`, use `record_metric` for output counts).
[+] Record gold pre-write metrics (Covered by output count metric)
[+] Write the data
[+] Count rows after writing (Covered by output count metric)
[+] Record gold post-write metrics (Covered by output count metric)
[+] Compare input (silver) and output (gold) counts using metrics and log any discrepancies or emit a validation record/metric.
[+] Validate business rules (Results emitted as metrics/validation events as above)
[+] Check data quality thresholds
[+] Verify referential integrity
[+] Flush metrics before function returns (via collector's flush)

F. Validation CLI Tool
[+] Create epic_fhir_integration/cli/validate_run.py
[+] Implement loading of metrics from a test directory (`<run_root>/metrics/**` for Parquet/JSON, and potentially `<run_root>/validation/**` for specific validation outputs).
[+] Implement validation rules (based on loaded metrics and a YAML configuration file):
    - Row count parity (Bronze-Silver, Silver-Gold)
    - Schema compliance (against recorded schema stats)
    - Data quality thresholds
    - Business rule compliance (based on emitted validation events/metrics)
    - Performance benchmarks
[+] Add command-line parsing for test directory path
[+] Implement validation result export (JSON to `<run_root>/validation/results.json`, optionally HTML).
[+] Add validation rule configuration file
[+] Implement configurable validation thresholds

Integration with Main Script
[+] Add validation as the final step in production_test.py
[+] Pass the test directory to the validator
[+] Include validation results in the final report
[+] Add validation status to run metadata
[+] Implement validation failure handling

Setup CLI Entry Point
[+] Update pyproject.toml to add the new command:
    epic-fhir-validate-run = "epic_fhir_integration.cli.validate_run:main"
[+] Add validation configuration options
[+] Implement validation result formatting

G. Report Enhancement
Expand Test Report
[+] Add resource metrics section to report (Enhance `generate_report()` in `production_test.py` to read from `<run_root>/metrics/transform_metrics.parquet`).
[+] Include validation results in the report (Enhance `generate_report()` to read `<run_root>/validation/results.json`).
[+] Add schema comparison details
[+] Include metrics visualization
[+] Add data quality scorecards
[+] Include performance metrics
[+] Add error summaries and recommendations

Create Summary Table
[+] Add a table showing counts of resources at each layer (from metrics)
[+] Highlight any discrepancies (from validation results)
[+] Add timestamps for each transformation step (from metrics)
[+] Include data quality scores
[+] Show validation rule compliance (from validation results)
[+] Add performance metrics

H. Quick Fix Implementation (Row Parity Focus)
[+] Implement the CSV counter function in production_test.py (Deprecated if focusing on Spark. Parity check should use metrics from the collector).
[+] Compare bronze and silver counts after transformation (Implement comparison using data from the metrics collector. This can be part_of the Validation CLI or an immediate check within the pipeline script writing a validation metric/log).
[+] Log warnings for any discrepancies
[+] Update status flags based on validation results
[+] Add data quality checks
[+] Implement error recovery

I. CI Integration
[+] Add validation step to CI pipeline (e.g., run `epic-fhir-validate-run <latest_run_dir_from_test_step>`).
[+] Configure CI to run with test patient data
[+] Set up failure conditions based on validation results
[+] Archive test results and reports as CI artifacts (Archive the entire `<run_root>` folder).
[+] Add performance regression detection (can be part of validation CLI checks)
[+] Implement validation result tracking

J. Documentation
Update Documentation
[+] Document the new validation system (metrics collector, directory structure, CLI, report changes)
[+] Create examples of validation reports
[+] Add troubleshooting guide for validation failures
[+] Update README with the new output structure information
[+] Add validation rule documentation
[+] Create data quality guidelines

Create Visualization Tools
[+] Add metrics visualization script
[+] Generate charts of resource counts across transformation layers
[+] Include visualizations in test reports
[+] Add data quality dashboards
[+] Create validation result visualizations
[+] Implement trend analysis

K. Testing & QA
End-to-End Testing
[+] Add pytest tests for `epic-fhir-validate-run` CLI using pre-defined test run outputs (in `tests/e2e/` or similar).
[+] Test with various patient datasets
[+] Verify that validation catches introduced errors
[+] Test error handling and recovery
[+] Validate performance under load
[+] Test concurrent runs

Manual Testing
[+] Run full production test with several patients
[+] Verify that output follows the new directory structure
[+] Verify that all validation steps work correctly
[+] Confirm all metrics are recorded and validated
[+] Test error scenarios
[+] Validate performance

L. Data Quality Framework
[+] Define data quality dimensions:
    - Completeness
    - Accuracy
    - Consistency
    - Timeliness
    - Uniqueness
[+] Implement quality metrics for each dimension (can leverage the metrics collector)
[+] Create quality thresholds and alerts (can be part of validation_rules.yaml)
[+] Add quality score calculation
[+] Implement quality reporting

M. Performance Monitoring
[+] Add performance metrics collection (Timings for steps are already in `transform_metrics` and can be added by collector for other stages)
[+] Implement resource usage tracking
[+] Create performance baselines
[+] Add performance regression detection (can be part of validation CLI checks)
[+] Implement performance reporting
[+] Create performance optimization guidelines