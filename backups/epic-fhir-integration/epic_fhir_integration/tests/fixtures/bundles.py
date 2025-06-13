import os
import json
import pytest
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, MapType


@pytest.fixture
def sample_patient_bundle(spark):
    """Load the sample patient bundle from test data."""
    bundle_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_patient_bundle.json")
    with open(bundle_path, "r") as f:
        bundle = json.load(f)
    
    # Convert to a format suitable for Spark
    return bundle_to_df(spark, bundle)


@pytest.fixture
def sample_observation_bundle(spark):
    """Load the sample observation bundle from test data."""
    bundle_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_observation_bundle.json")
    with open(bundle_path, "r") as f:
        bundle = json.load(f)
    
    # Convert to a format suitable for Spark
    return bundle_to_df(spark, bundle)


def extract_resources_from_bundle(bundle):
    """Extract resource entries from a FHIR bundle."""
    if "entry" not in bundle:
        return []
    
    resources = []
    for entry in bundle["entry"]:
        if "resource" in entry:
            resources.append(entry["resource"])
    
    return resources


def bundle_to_df(spark, bundle):
    """Convert a FHIR bundle to a Spark DataFrame."""
    # Extract resource type from the first resource
    resources = extract_resources_from_bundle(bundle)
    if not resources:
        return create_empty_resource_df(spark)
    
    resource_type = resources[0]["resourceType"]
    
    # Convert resources to JSON strings for Spark
    resources_json = [json.dumps(r) for r in resources]
    
    # Create a DataFrame with the resources as a JSON column
    df = spark.createDataFrame([(r,) for r in resources_json], ["resource_json"])
    
    # Parse the JSON into a structured column
    df = df.selectExpr("from_json(resource_json, 'STRUCT<*>') as resource")
    
    return df


def create_empty_resource_df(spark):
    """Create an empty DataFrame with the expected structure for resources."""
    schema = StructType([
        StructField("resource", MapType(StringType(), StringType()), True)
    ])
    return spark.createDataFrame([], schema) 