# Epic FHIR Integration Production Testing Guide

This guide provides instructions for running production tests with the latest enhancements to the Epic FHIR integration pipeline, including advanced validation, metrics collection, and reliability improvements.

## Prerequisites

- Python 3.8 or higher
- Appropriate permissions for Epic FHIR API access
- Environment variables configured (see below)
- 10+ GB of free disk space

## Environment Setup

Configure the required environment variables:

```bash
# Required environment variables
export FHIR_OUTPUT_DIR="/path/to/output"
export EPIC_API_BASE_URL="https://your-epic-instance/api/FHIR/R4"
export EPIC_CLIENT_ID="your-client-id"
export EPIC_PRIVATE_KEY_PATH="/path/to/private.key"
```

## Running a Production Test

### Basic Test

Run a basic production test with a single patient:

```bash
python scripts/production_test.py --patient-id PATIENT_ID
```

### Advanced Test with All Features

To leverage all enhanced features, run with these options:

```bash
python scripts/production_test.py \
    --patient-id PATIENT_ID \
    --output-dir /path/to/output \
    --debug \
    --keep-tests 5 \
    --min-disk-space 10.0 \
    --monitor-disk \
    --retry-count 3
```

### Command Line Options

| Option | Description | Default |
| ------ | ----------- | ------- |
| `--patient-id` | Patient ID to use for testing | *Required* |
| `--output-dir` | Output directory for test artifacts | `output/production_test` |
| `--debug` | Enable debug logging | `False` |
| `--keep-tests` | Number of test directories to keep | `5` |
| `--min-disk-space` | Minimum free disk space in GB | `10.0` |
| `--monitor-disk` | Enable disk space monitoring | `False` |
| `--retry-count` | Maximum number of retries for API calls | `3` |

## Test Output Structure

Each test run creates a timestamped directory with the following structure:

```
TEST_YYYYMMDD_HHMMSS/
├── bronze/                # Raw FHIR resources
├── silver/                # Transformed FHIR resources
├── gold/                  # Aggregated summaries
├── logs/                  # Test logs
├── metrics/               # Performance metrics
│   ├── performance_metrics.parquet
│   └── transform_metrics.parquet
├── reports/               # Test reports and visualizations
├── dashboards/            # Quality and validation dashboards
│   ├── quality_dashboard.html
│   └── validation_dashboard.html
├── schemas/               # Schema information
├── validation/            # Validation results
│   ├── results.json
│   └── thresholds.json
└── run_info.json          # Test metadata
```

## Validation

### Running Validation Separately

To validate an existing test run:

```bash
python -m epic_fhir_integration.cli.validate_run --run-dir /path/to/TEST_YYYYMMDD_HHMMSS
```

Or use the CLI entry point:

```bash
epic-fhir-validate-run --run-dir /path/to/TEST_YYYYMMDD_HHMMSS
```

### Customizing Validation Thresholds

You can customize validation thresholds in several ways:

1. **Command-line arguments:**
   ```bash
   epic-fhir-validate-run --run-dir /path/to/run \
       --row-count-threshold 0.95 \
       --extract-time-threshold 600
   ```

2. **Configuration file:**
   ```bash
   epic-fhir-validate-run --run-dir /path/to/run --config validation_thresholds.json
   ```

3. **Save current configuration:**
   ```bash
   epic-fhir-validate-run --run-dir /path/to/run --save-config my_thresholds.json
   ```

### Sample Threshold Configuration

Create a `validation_thresholds.json` file with:

```json
{
  "row_count_threshold": 0.98,
  "performance_thresholds": {
    "extract": 300,
    "transform": 600,
    "load": 300
  },
  "data_quality_thresholds": {
    "completeness": 0.95,
    "accuracy": 0.98,
    "consistency": 0.97
  },
  "resource_usage_thresholds": {
    "memory_percent_max": 90,
    "cpu_percent_max": 95
  }
}
```

## Metrics Collection

Metrics are automatically collected during pipeline execution. The system collects:

- Runtime performance metrics
- Resource counts at each stage
- Data quality metrics
- Schema metrics
- Resource usage statistics
- Validation statistics

### Dashboard Visualization

The metrics and validation results are automatically visualized through interactive dashboards:

```bash
# Generate quality dashboard from report
epic-fhir-dashboard quality --report-path /path/to/TEST_YYYYMMDD_HHMMSS/metrics/quality_report.json

# Generate validation dashboard from results
epic-fhir-dashboard validation --results-path /path/to/TEST_YYYYMMDD_HHMMSS/validation/results.json

# Generate both dashboards in static HTML mode
epic-fhir-dashboard combined --quality-report /path/to/quality_report.json --validation-results /path/to/results.json --static-only

# Create example dashboards with sample data for reference
epic-fhir-dashboard create-examples --output-dir /path/to/output
```

### Viewing Metrics

The metrics are stored in Parquet format in the `metrics/` directory:

```bash
# View metrics summary
python -c "import pandas as pd; print(pd.read_parquet('TEST_YYYYMMDD_HHMMSS/metrics/performance_metrics.parquet').describe())"
```

## Error Handling and Recovery

The pipeline includes several reliability improvements:

1. **Retry Mechanisms:** API calls and other operations automatically retry on transient failures with exponential backoff.

2. **Disk Space Monitoring:** The pipeline checks and monitors disk space, with automatic cleanup of old test directories when space is low.

3. **Batch Metrics Recording:** High-frequency metrics are recorded in batches for better performance.

4. **Validation Thresholds:** Configurable thresholds allow for environment-specific validation settings.

## Troubleshooting

### Common Issues

1. **API Authentication Failures:**
   - Check environment variables
   - Verify your API key and client ID
   - Check network connectivity to Epic FHIR server

2. **Insufficient Disk Space:**
   - Use `--min-disk-space` to specify a lower threshold if needed
   - Enable `--monitor-disk` for automatic cleanup
   - Manually clean up old test directories

3. **Validation Failures:**
   - Check validation logs in `validation/results.json`
   - Adjust thresholds if necessary
   - Look for specific metrics in `metrics/performance_metrics.parquet`

### Logs

Detailed logs are stored in the `logs/` directory for each test run:

```bash
# View test logs
cat TEST_YYYYMMDD_HHMMSS/logs/test.log
```

Enable debug logging for more verbose output:

```bash
python scripts/production_test.py --patient-id PATIENT_ID --debug
```

## Testing Multiple Patients

To test multiple patients, you can use a simple script:

```bash
#!/bin/bash
PATIENTS=("patient1" "patient2" "patient3")
OUTPUT_DIR="output/multi_patient_test"

for patient in "${PATIENTS[@]}"; do
  echo "Testing patient: $patient"
  python scripts/production_test.py \
    --patient-id "$patient" \
    --output-dir "$OUTPUT_DIR" \
    --monitor-disk
done

# Validate the latest test
python -m epic_fhir_integration.cli.validate_run --latest --output-dir "$OUTPUT_DIR"
```

## Advanced Testing Practices

### CI Integration

Add this to your CI pipeline:

```yaml
test-production:
  stage: test
  script:
    - python scripts/production_test.py --patient-id $TEST_PATIENT_ID
    - python -m epic_fhir_integration.cli.validate_run --latest
  artifacts:
    paths:
      - output/production_test/TEST_*
```

### Performance Benchmarking

Compare performance metrics across runs:

```python
import pandas as pd
import glob
import os

def get_latest_runs(base_dir, count=5):
    runs = sorted(glob.glob(os.path.join(base_dir, "TEST_*")), reverse=True)
    return runs[:count]

def compare_metrics(runs):
    metrics = []
    
    for run in runs:
        try:
            metrics_file = os.path.join(run, "metrics", "performance_metrics.parquet")
            df = pd.read_parquet(metrics_file)
            df['run'] = os.path.basename(run)
            metrics.append(df)
        except Exception as e:
            print(f"Error loading metrics from {run}: {e}")
    
    if not metrics:
        return pd.DataFrame()
    
    all_metrics = pd.concat(metrics)
    return all_metrics

runs = get_latest_runs("output/production_test")
metrics = compare_metrics(runs)

# Filter to just the extraction time metrics
extraction_times = metrics[
    (metrics['step'] == 'extract') & 
    (metrics['name'] == 'extraction_time')
]

# Compare across runs
pivot = extraction_times.pivot(index='run', values='value', columns='name')
print(pivot)
```

## Further Reading

- [High-Impact Improvements](high_impact_improvements.md)
- [Performance Optimization Guidelines](performance_optimization.md)
- [Production Guidelines](production_guidelines_5_20.md)
- [Validation Rule Documentation](validation_rules.md) 