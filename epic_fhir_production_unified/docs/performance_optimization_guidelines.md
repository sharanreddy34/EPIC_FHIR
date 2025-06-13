# EPIC FHIR Integration Performance Optimization Guidelines

This document outlines best practices and guidelines for optimizing performance in the EPIC FHIR Integration pipeline. These recommendations cover Spark configuration, code optimization, memory management, and monitoring.

## 1. Spark Configuration Optimization

### 1.1 Memory Configuration
- **Driver Memory**: Set `spark.driver.memory` based on dataset size and processing requirements (4-8GB recommended for most workloads)
  ```python
  spark = SparkSession.builder \
      .config("spark.driver.memory", "8g") \
      # Other configs...
  ```
- **Executor Memory**: Configure `spark.executor.memory` based on available resources
- **Memory Overhead**: Set `spark.memory.overhead` to 0.1 of executor memory for garbage collection

### 1.2 Parallelism and Partitioning
- **Shuffle Partitions**: Set `spark.sql.shuffle.partitions` based on data volume (default 200 is often too high for medium workloads)
  - For local development: `spark.sql.shuffle.partitions=4` or `number_of_cores * 2`
  - For production: `spark.sql.shuffle.partitions=200` for large datasets
- **Default Parallelism**: Set `spark.default.parallelism` to a reasonable number based on executor cores
- **Dynamic Allocation**: Enable with `spark.dynamicAllocation.enabled=true` for flexible resource usage

### 1.3 Storage Configuration
- **Compression**: Enable RDD compression with `spark.rdd.compress=true`
- **Serialization**: Use Kryo serialization with `spark.serializer=org.apache.spark.serializer.KryoSerializer` for faster serialization

## 2. Data Processing Optimization

### 2.1 Partitioning Strategies
- Partition Bronze data by resource_type and extraction_date:
  ```python
  df.write.partitionBy("resource_type", "extraction_date").parquet(path)
  ```
- Limit the number of partitions to prevent small file problem (each partition > 128MB ideal)
- For large datasets, use the existing repartitioning logic:
  ```python
  # Current implementation in transform_resource
  if transformed_df.count() > 10000000:  # 10M rows
      transformed_df = transformed_df.repartition(200)
  ```

### 2.2 File Format Selection
- Use Parquet for all persisted data (current choice is optimal)
- Use Delta Lake for tables that require ACID properties
- Consider compressed Parquet for smaller storage footprint:
  ```python
  df.write.option("compression", "snappy").parquet(path)
  ```

### 2.3 Optimization Techniques
- **Broadcast Joins**: Use for joins with small tables (<10MB):
  ```python
  from pyspark.sql.functions import broadcast
  result = df1.join(broadcast(df2), "join_column")
  ```
- **Predicate Pushdown**: Apply filters early in the transformation chain
- **Avoid UDFs**: Prefer built-in functions over UDFs where possible
- **Column Pruning**: Select only needed columns to reduce memory pressure

## 3. Memory Management

### 3.1 Handling Large Datasets
- Process large datasets in smaller batches/partitions
- Tune garbage collection settings:
  ```
  spark.executor.extraJavaOptions=-XX:+UseG1GC -XX:+UnlockDiagnosticVMOptions -XX:+G1SummarizeConcMark
  ```
- Monitor memory usage via Spark UI or metrics collection

### 3.2 Caching Strategy
- Cache intermediate DataFrames only when reused multiple times
- Unpersist DataFrames when no longer needed:
  ```python
  df.cache()  # Process and cache
  # Use df in multiple operations
  df.unpersist()  # Release memory when done
  ```
- Use appropriate storage level based on needs (MEMORY_ONLY, MEMORY_AND_DISK)

## 4. Performance Monitoring

### 4.1 Metrics to Track
- **Processing Time**: Track timing for each transformation step (already implemented)
- **Memory Usage**: Monitor executor and driver memory usage
- **Shuffle Size**: Track data shuffled between stages
- **Record Counts**: Track input/output record counts for each stage (already implemented)
- **Skew Detection**: Monitor task durations to detect data skew

### 4.2 Implementation Strategy
- Use existing metrics collector to track performance metrics:
  ```python
  from epic_fhir_integration.metrics.collector import record_metric
  
  start_time = time.time()
  # Process data...
  duration = time.time() - start_time
  record_metric("performance", "transform_duration", duration)
  record_metric("performance", "memory_usage", get_memory_usage())
  ```

### 4.3 Benchmarking
- Establish performance baselines for common operations:
  - Extraction time per patient
  - Transformation time per resource type
  - Overall pipeline execution time
- Compare metrics against baselines in validation step
- Alert on significant performance regressions

## 5. Resource Usage Optimization

### 5.1 CPU Optimization
- Match parallelism to available cores
- Avoid excessive CPU-intensive operations (e.g., frequent DataFrame.count())
- Prefer DataFrame operations over RDD operations

### 5.2 I/O Optimization
- Minimize disk I/O by reducing intermediate data writes
- Use appropriate compression for network and disk I/O
- Prefer columnar formats (Parquet) for analytics queries

### 5.3 Network Optimization
- Reduce data transfer by pushing computations to data nodes
- Use data locality optimizations
- Minimize collect() operations that bring data to driver

## 6. Specific Recommendations for FHIR Pipeline

### 6.1 Extract Phase
- Parallelize patient data extraction when possible
- Cache frequently used reference data
- Use connection pooling for API connections

### 6.2 Transform Phase
- Pre-compute and cache lookup tables
- Prioritize resource types with interdependencies
- Leverage schema information to optimize transformations

### 6.3 Load Phase
- Use bulk operations when writing to databases
- Consider write batching for better throughput
- Validate performance against established baselines

## 7. Testing and Validation

### 7.1 Performance Testing
- Create dedicated performance test suite with large representative datasets
- Test with various patient cohort sizes
- Validate memory usage under high load

### 7.2 Regression Testing
- Compare performance metrics between runs
- Integrate performance validation into CI/CD pipeline
- Add automatic alerts for significant performance degradation 