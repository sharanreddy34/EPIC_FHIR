import os
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Create a local Spark session for testing."""
    # Configure local Spark with Delta support
    spark = (
        SparkSession.builder.appName("FHIR-Pipeline-Test")
        .master("local[2]")  # 2 local cores
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
        .config("spark.ui.enabled", "false")  # Disable Spark UI for testing
        .config("spark.driver.memory", "2g")  # Small memory allocation for tests
        .getOrCreate()
    )
    
    # Create a temporary warehouse directory
    warehouse_dir = "/tmp/fhir-test-warehouse"
    os.makedirs(warehouse_dir, exist_ok=True)
    
    spark.conf.set("spark.sql.warehouse.dir", warehouse_dir)
    
    # Set up log level to reduce test output noise
    spark.sparkContext.setLogLevel("ERROR")
    
    yield spark
    
    # Stop Spark session after tests complete
    spark.stop()


def create_test_df(spark, data, schema=None):
    """Helper to create a test DataFrame from data."""
    if schema:
        return spark.createDataFrame(data, schema)
    else:
        return spark.createDataFrame(data) 