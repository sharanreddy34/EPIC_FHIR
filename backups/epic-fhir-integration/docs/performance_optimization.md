# Performance Optimization Guidelines

This document provides guidelines and best practices for optimizing the performance of the Epic FHIR integration pipeline at each layer (Bronze, Silver, Gold). These recommendations are based on observed performance characteristics and common bottlenecks in the data pipeline.

## Table of Contents
- [General Guidelines](#general-guidelines)
- [Bronze Layer Optimization](#bronze-layer-optimization)
- [Silver Layer Optimization](#silver-layer-optimization)
- [Gold Layer Optimization](#gold-layer-optimization)
- [Memory Management](#memory-management)
- [Spark Optimization](#spark-optimization)
- [Monitoring and Tuning](#monitoring-and-tuning)
- [Performance Testing](#performance-testing)

## General Guidelines

### Resource Allocation
- Allocate appropriate resources based on data volume and processing needs
- Monitor CPU, memory, and I/O utilization to identify bottlenecks
- Consider data locality to minimize network transfers
- Use parallelism appropriately for your hardware configuration

### Batch Processing
- Process data in appropriately sized batches to balance memory usage and throughput
- Use streaming processing for real-time requirements
- Consider incremental processing for large datasets

### Caching
- Cache frequently accessed data to avoid repeated API calls or computations
- Use memory caching for small, frequently accessed datasets
- Use disk caching for larger datasets

### Logging and Metrics
- Use appropriate logging levels to avoid performance overhead in production
- Collect performance metrics consistently to establish baselines
- Implement targeted metrics at potential bottlenecks

## Bronze Layer Optimization

### API Optimization
- Implement connection pooling for API connections
- Use asynchronous requests where possible
- Batch API requests when the API supports it
- Implement exponential backoff for retries
- Cache API responses appropriately

### Recommended request patterns:
```python
# Batch requests where possible
patient_ids = ["patient1", "patient2", "patient3"]
resources = client.get_resources_batch(patient_ids, resource_type="Observation")

# Use async requests for multiple parallel calls
async def get_patient_data(patient_id):
    tasks = [
        get_resource(patient_id, "Patient"),
        get_resource(patient_id, "Observation"),
        get_resource(patient_id, "MedicationRequest")
    ]
    return await asyncio.gather(*tasks)
```

### Data Extraction
- Request only required resources (avoid extracting unused resource types)
- Use appropriate date filters to limit data volume
- Implement pagination for large datasets
- Process and store data in smaller chunks

### Serialization and Storage
- Use efficient serialization formats (Parquet, ORC, Avro) instead of JSON/CSV
- Compress data at rest (Gzip, Snappy, LZ4)
- Partition bronze storage by appropriate dimensions (date, resource type)

### Parallelization
- Extract data for multiple patients in parallel, but respect API rate limits
- Implement worker pools to parallelize extraction

## Silver Layer Optimization

### Transformation Logic
- Optimize transformation logic to minimize passes through the data
- Use vectorized operations where possible
- Avoid row-by-row processing for large datasets
- Implement efficient joins by using appropriate join strategies

Example of vectorized operations in Spark:
```python
# Vectorized operation (faster)
df = df.withColumn("full_name", 
                  concat(col("given_name"), lit(" "), col("family_name")))

# Avoid row-by-row UDFs when possible, but when needed:
@pandas_udf("string")
def combine_names(given, family):
    return given + " " + family

df = df.withColumn("full_name", combine_names(col("given_name"), col("family_name")))
```

### Schema Optimization
- Define and enforce schemas early
- Use appropriate data types to minimize memory usage
- Consider denormalization for query performance
- Use dynamic schema handling for evolving data structures

### Data Partitioning
- Partition silver data by appropriate access patterns
- Balance partition size to avoid small-file problems
- Consider repartitioning based on data skew

### Memory Management
- Monitor executor memory usage
- Adjust broadcast thresholds appropriately
- Use disk spill settings for large datasets

## Gold Layer Optimization

### Aggregation Strategies
- Implement multi-level aggregation for large datasets
- Use windowing functions efficiently
- Optimize join strategies based on data distribution
- Pre-compute common aggregations

Example of efficient window functions:
```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, col

# Efficient window function
window_spec = Window.partitionBy("patient_id").orderBy(col("observation_date").desc())
latest_observations = df.withColumn("row_number", row_number().over(window_spec)) \
                        .filter(col("row_number") == 1) \
                        .drop("row_number")
```

### Data Compaction
- Compact small files into larger files
- Use table optimization commands for Spark tables

### Caching for Interactive Analysis
- Cache commonly used gold datasets in memory
- Persist optimized versions of gold data

### Filtering Strategies
- Push down predicates to minimize data processed
- Use bloom filters for large-scale filtering operations
- Implement materialized views for common filter patterns

## Memory Management

### JVM Tuning
- Set appropriate heap sizes for driver and executors
- Configure garbage collection strategy
- Monitor and adjust off-heap memory

### Spark Memory Configuration
- Properly configure `spark.memory.fraction` and `spark.memory.storageFraction`
- Use appropriate serializers and compression for shuffle operations
- Configure disk spill settings for large operations

### Data Structures
- Use appropriate data structures based on access patterns
- Consider columnar formats for analytical workloads
- Use sparse representations for sparse datasets

## Spark Optimization

### Physical Execution Plan
- Review and optimize physical execution plans
- Manage partition counts for optimal parallelism
- Use broadcast joins for small tables

Example configuration:
```python
# Set broadcast threshold (in bytes)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 100 * 1024 * 1024)  # 100MB

# Manage partition count
df = df.repartition(200)  # Adjust based on cluster size
```

### Shuffle Operations
- Minimize shuffle operations where possible
- Configure appropriate parallelism for shuffles
- Monitor exchange operations in query plans

### Caching Strategy
- Cache at appropriate points in the computation graph
- Use the appropriate storage level based on memory availability
- Unpersist cached data when no longer needed

```python
# Different storage levels based on needs
df.persist(StorageLevel.MEMORY_ONLY)  # Memory only
df.persist(StorageLevel.MEMORY_AND_DISK)  # Spill to disk if needed
df.persist(StorageLevel.MEMORY_ONLY_SER)  # Serialized in memory (smaller footprint)
```

### Input/Output
- Use efficient file formats (Parquet) with appropriate compression
- Configure I/O buffer sizes based on underlying storage
- Use appropriate file sizes (avoid small files problem)

## Monitoring and Tuning

### Key Metrics to Monitor
- Job execution time
- Stage processing times
- Executor CPU and memory utilization
- Garbage collection behavior
- Shuffle read/write size
- I/O throughput
- Cache hit rate

### Continuous Improvement Process
1. Measure baseline performance
2. Identify bottlenecks through metrics
3. Implement targeted optimizations
4. Measure improvement
5. Repeat

### Alerting
- Set thresholds for performance alerts
- Create alerts for significant performance degradation
- Implement proactive monitoring

## Performance Testing

### Load Testing
- Test with realistic data volumes
- Implement progressive load testing
- Measure resource scaling characteristics

### Benchmark Tests
- Create repeatable benchmark tests
- Test under different hardware and configuration options
- Compare against baseline measurements

### Performance Regression Testing
- Implement automated performance testing
- Compare performance metrics across versions
- Establish acceptable variance thresholds

## Additional Resources

### Reading
- [Apache Spark Performance Tuning](https://spark.apache.org/docs/latest/tuning.html)
- [PySpark Performance Tuning](https://spark.apache.org/docs/latest/api/python/user_guide/python_performance.html)

### Tools
- Spark UI for performance analysis
- [Flame Graphs](http://www.brendangregg.com/flamegraphs.html) for CPU profiling
- [Apache Spark Metrics](https://spark.apache.org/docs/latest/monitoring.html) for detailed performance metrics

## Example Performance Optimization Flow

1. **Identify bottlenecks** using the metrics collector:
   ```python
   # Analyze where time is spent
   metrics_df = pd.read_parquet("metrics/performance_metrics.parquet")
   runtime_metrics = metrics_df[metrics_df['metric_type'] == 'RUNTIME']
   
   # Find the slowest operations
   slowest_ops = runtime_metrics.sort_values(by='value', ascending=False).head(5)
   print("Top 5 most time-consuming operations:")
   for _, row in slowest_ops.iterrows():
       print(f"{row['step']} - {row['name']}: {row['value']:.2f} seconds")
   ```

2. **Implement targeted optimizations** based on bottlenecks
3. **Measure improvement** using the same metrics
4. **Document optimizations** and their impact 