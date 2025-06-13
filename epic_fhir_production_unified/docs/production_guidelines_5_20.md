# Epic FHIR Integration Production Guidelines (May 20)

## Overview

This document outlines the production guidelines for the Epic FHIR integration pipeline, incorporating recent enhancements to validation, metrics collection, and performance optimization. These guidelines are designed to ensure reliable operation and maintainable code in production environments.

## Recent Enhancements

### 1. Metrics Collection System
- Comprehensive metrics collection at each pipeline stage
- Thread-safe metric recording
- Persistent storage in Parquet format
- Support for various metric types (runtime, schema, quality)
- Automatic metric flushing via atexit handlers

### 2. Validation Framework
- End-to-end validation of pipeline outputs
- Row count parity checks between layers
- Data quality validation
- Schema compliance verification
- Performance threshold monitoring

### 3. Directory Structure
- Standardized test output organization
- Separate directories for metrics, logs, and validation results
- Automatic cleanup of old test directories
- Run metadata tracking

## Production Deployment Guidelines

### 1. Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest epic_fhir_integration/tests/unit
```

### 2. Configuration

Required environment variables:
```bash
export FHIR_OUTPUT_DIR="/path/to/output"
export EPIC_API_BASE_URL="https://your-epic-instance/api/FHIR/R4"
export EPIC_CLIENT_ID="your-client-id"
export EPIC_PRIVATE_KEY_PATH="/path/to/private.key"
```

### 3. Running the Pipeline

Basic execution:
```bash
python production_test.py --patient-id PATIENT_ID --output-dir /path/to/output
```

With validation and debugging:
```bash
python production_test.py \
    --patient-id PATIENT_ID \
    --output-dir /path/to/output \
    --debug \
    --validate
```

### 4. Monitoring and Metrics

Key metrics to monitor:
- Authentication success rate
- API response times
- Resource extraction counts
- Transformation success rates
- Row count parity between layers
- Overall pipeline execution time

Metrics are stored in:
```
<output_dir>/TEST_<timestamp>/metrics/performance_metrics.parquet
```

### 5. Validation

The validation framework checks:
- Data completeness
- Row count consistency
- Schema compliance
- Performance thresholds
- Business rule compliance

Validation results are stored in:
```
<output_dir>/TEST_<timestamp>/validation/results.json
```

## Testing Guidelines

### 1. Unit Testing

Run unit tests:
```bash
python -m pytest epic_fhir_integration/tests/unit
```

Key test areas:
- Metrics collector functionality
- Data type handling
- Concurrent metric recording
- Metric persistence
- Validation rules

### 2. Integration Testing

Run integration tests:
```bash
python -m pytest epic_fhir_integration/tests/integration
```

Test with various scenarios:
- Multiple patient records
- Different resource types
- Error conditions
- Performance under load

### 3. Performance Testing

```bash
# Run with performance monitoring
python production_test.py \
    --patient-id PATIENT_ID \
    --debug \
    --validate \
    --output-dir /path/to/output
```

Monitor:
- CPU utilization
- Memory usage
- I/O operations
- API response times
- Overall pipeline duration

## Error Handling and Recovery

### 1. Common Error Scenarios

- API authentication failures
- Network timeouts
- Resource not found
- Schema validation errors
- Data quality issues

### 2. Recovery Procedures

1. Authentication failures:
   ```bash
   # Refresh authentication token
   python scripts/refresh_epic_token.py
   ```

2. Failed validations:
   - Review validation results in `validation/results.json`
   - Check metrics for specific failure points
   - Rerun pipeline with debug logging

3. Performance issues:
   - Review performance_metrics.parquet
   - Check resource utilization
   - Adjust batch sizes or parallelism

## Maintenance and Optimization

### 1. Regular Maintenance

- Monitor disk usage
- Clean up old test directories
- Review performance metrics
- Update validation rules

### 2. Performance Optimization

Follow the guidelines in `performance_optimization.md` for:
- API request optimization
- Data transformation efficiency
- Memory management
- Spark configuration

### 3. Logging and Debugging

Log files are stored in:
```
<output_dir>/TEST_<timestamp>/logs/
```

Enable debug logging:
```bash
python production_test.py --debug ...
```

## Production Checklist

Before deployment:
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance tests meet thresholds
- [ ] Environment variables configured
- [ ] Logging properly configured
- [ ] Monitoring in place
- [ ] Cleanup scripts scheduled
- [ ] Error handling verified
- [ ] Recovery procedures documented
- [ ] Team trained on validation results

## Support and Troubleshooting

### 1. Common Issues

1. Metric collection failures:
   - Check disk space
   - Verify write permissions
   - Review atexit handler logs

2. Validation failures:
   - Check validation/results.json
   - Review metrics for specific stages
   - Enable debug logging

3. Performance issues:
   - Review performance_metrics.parquet
   - Check resource utilization
   - Adjust configuration parameters

### 2. Getting Help

1. Review logs:
   ```bash
   cat <output_dir>/TEST_<timestamp>/logs/test_*.log
   ```

2. Generate debug report:
   ```bash
   python production_test.py --debug --patient-id TEST_ID
   ```

3. Contact support with:
   - Test run directory
   - Debug logs
   - Validation results
   - Performance metrics

## Version Information

- Document version: May 20, 2024
- Pipeline version: Current main branch
- Last validated: May 20, 2024

## Additional Resources

- [Performance Optimization Guidelines](performance_optimization.md)
- [API Documentation](https://your-epic-instance/api-docs)
- [Validation Rules Reference](validation_rules.md)
- [Metrics Reference](metrics_reference.md) 