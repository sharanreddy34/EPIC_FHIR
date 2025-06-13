"""
Epic FHIR Resource Extraction Pipeline.

This pipeline extracts FHIR resources from Epic API and stores them in the bronze layer.
"""

import os
import yaml
import json
import logging
import datetime
import argparse
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

# Foundry imports
from transforms.api import Input, Output, transform, configure
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

from lib.auth import get_token_from_foundry_secret
from lib.fhir_client import FHIRClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@configure(profile=["FHIR_RESOURCE_EXTRACTION"])
@transform(
    config_input=Input("/config/api_config.yaml"),
    resources_config=Input("/config/resources_config.yaml"),
    token_secret=Input("/secrets/epic_token"),
    cursors=Input("/control/fhir_cursors"),
    output=Output("/bronze/fhir_raw"),
)
def extract_resources(
    spark: SparkSession, 
    config_input: Input,
    resources_config: Input,
    token_secret: Input,
    cursors: Input,
    output: Output,
    resource_type: Optional[str] = None,
    max_workers: int = 4,
) -> None:
    """
    Extract FHIR resources from Epic API.
    
    Args:
        spark: SparkSession
        config_input: API configuration
        resources_config: Resource types configuration
        token_secret: OAuth token secret
        cursors: Dataset tracking extraction progress
        output: Output location for raw FHIR bundles
        resource_type: Optional specific resource to extract
        max_workers: Maximum number of concurrent extraction workers
    """
    # Load configurations
    api_config = yaml.safe_load(config_input.read_file())["api"]
    resources_dict = yaml.safe_load(resources_config.read_file())["resources"]
    
    # Get token
    access_token, token_expiry = get_token_from_foundry_secret("/secrets/epic_token")
    
    # Check if token is valid
    if token_expiry < datetime.datetime.now() + datetime.timedelta(minutes=10):
        logger.error("Token will expire soon, please refresh token first")
        raise ValueError("Token expiration imminent")
    
    # Create FHIR client
    client = FHIRClient(
        base_url=api_config["base_url"],
        token_provider=lambda: access_token,
        max_retries=api_config.get("max_retries", 3),
        timeout=api_config.get("timeout", 30),
        verify_ssl=api_config.get("verify_ssl", True),
    )
    
    # Validate connection
    if not client.validate_connection():
        raise ConnectionError("Failed to connect to Epic FHIR API")
    
    # Get cursor data - ensure default schema if empty
    try:
        cursor_df = cursors.dataframe()
        
        # Verify schema by selecting key columns
        cursor_df.select("resource_type", "last_updated", "extracted_at").count()
    except Exception as e:
        logger.warning(f"Error reading cursor data: {str(e)}, creating new cursor dataset")
        # Create empty cursor DataFrame
        cursor_schema = StructType([
            StructField("resource_type", StringType(), False),
            StructField("last_updated", StringType(), False),
            StructField("extracted_at", StringType(), False),
            StructField("record_count", StringType(), True),
        ])
        cursor_df = spark.createDataFrame([], cursor_schema)
    
    # Determine resources to extract
    if resource_type:
        if resource_type not in resources_dict:
            raise ValueError(f"Unknown resource type: {resource_type}")
        resources_to_extract = {resource_type: resources_dict[resource_type]}
    else:
        # Filter to only enabled resources
        resources_to_extract = {k: v for k, v in resources_dict.items() if v.get("enabled", True)}
    
    # Sort resources by priority
    sorted_resources = sorted(
        resources_to_extract.items(), 
        key=lambda x: x[1].get("priority", 999)
    )
    
    # Extract independent resources first, then patient-scoped resources
    independent_resources = [(res_type, res_config) for res_type, res_config in sorted_resources 
                            if not res_config.get("patient_scoped", False)]
    
    patient_scoped_resources = [(res_type, res_config) for res_type, res_config in sorted_resources 
                               if res_config.get("patient_scoped", False)]
    
    # Functions for extraction
    def extract_resource(res_type: str, res_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a single resource type."""
        logger.info(f"Extracting {res_type} resources")
        
        # Get last cursor for this resource
        last_cursor_rows = cursor_df.filter(f"resource_type = '{res_type}'").collect()
        if last_cursor_rows:
            last_updated = last_cursor_rows[0]["last_updated"]
        else:
            last_updated = "1900-01-01T00:00:00Z"
        
        # Prepare search parameters
        incremental_param = res_config.get("incremental_param", "_lastUpdated")
        search_params = {incremental_param: f"gt{last_updated}"}
        
        # Add page size
        search_params["_count"] = api_config.get("page_size", 100)
        
        # Special handling for Observation resources - add required category parameter
        if res_type == "Observation" and "category" not in search_params:
            search_params["category"] = "laboratory"
            logger.info(f"Added required 'category=laboratory' parameter for Observation resources")
        
        # Keep track of max updated time and count
        max_updated = last_updated
        page_count = 0
        bundle_count = 0
        error_count = 0
        
        # Extract data with metrics tracking
        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        
        try:
            for bundle in client.search_resource(res_type, search_params):
                # Check for entries
                if "entry" in bundle and bundle["entry"]:
                    # Update max timestamp
                    for entry in bundle["entry"]:
                        if "resource" in entry and "meta" in entry["resource"] and "lastUpdated" in entry["resource"]["meta"]:
                            entry_updated = entry["resource"]["meta"]["lastUpdated"]
                            if entry_updated > max_updated:
                                max_updated = entry_updated
                    
                    # Add metadata
                    bundle_metadata = {
                        "resource_type": res_type,
                        "extracted_at": datetime.datetime.now().isoformat(),
                        "page_number": page_count,
                        "entry_count": len(bundle.get("entry", [])),
                    }
                    
                    # Write bundle to output
                    bundle_with_metadata = {
                        "metadata": bundle_metadata,
                        "bundle": bundle,
                    }
                    
                    # Write to filesystem using Foundry Output
                    # Default to Parquet format for better performance and compatibility
                    try:
                        import pandas as pd
                        from pyspark.sql import SparkSession
                        
                        # Convert to pandas DataFrame and then to Spark DataFrame
                        spark = SparkSession.builder.getOrCreate()
                        
                        # Create a pandas DataFrame with the bundle data
                        pdf = pd.DataFrame([bundle_with_metadata])
                        
                        # Convert to Spark DataFrame
                        sdf = spark.createDataFrame(pdf)
                        
                        # Write as Parquet
                        file_path = f"{res_type}/{timestamp}_{page_count}"
                        
                        # Write to temp location then move to output
                        temp_dir = f"/tmp/fhir_extract_{timestamp}_{page_count}"
                        sdf.write.mode("overwrite").parquet(temp_dir)
                        
                        # Use output.write_file for parquet files
                        for filename in os.listdir(temp_dir):
                            if filename.endswith(".parquet") and not filename.startswith("_"):
                                with open(f"{temp_dir}/{filename}", "rb") as f:
                                    output.write_file(f"{file_path}.parquet", f.read())
                        
                        # Clean up temp files
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    except Exception as e:
                        # Fall back to JSON if there's an error with Parquet
                        logger.warning(f"Failed to write Parquet, falling back to JSON: {str(e)}")
                        file_path = f"{res_type}/{timestamp}_{page_count}.json"
                        output.write_file(file_path, json.dumps(bundle_with_metadata))
                    
                    bundle_count += len(bundle.get("entry", []))
                    page_count += 1
                    
                    # Rate limiting - be nice to the API
                    if page_count % 5 == 0:
                        logger.info(f"Extracted {bundle_count} {res_type} resources in {page_count} pages so far")
        except Exception as e:
            logger.error(f"Error extracting {res_type}: {str(e)}")
            error_count += 1
            # Continue with partial results if we have any
            if page_count == 0:
                return {
                    "resource_type": res_type,
                    "success": False,
                    "error": str(e),
                    "duration_seconds": (datetime.datetime.now() - start_time).total_seconds(),
                }
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"Extracted {bundle_count} {res_type} resources in {page_count} pages. "
            f"Duration: {duration:.2f}s. New cursor: {max_updated}"
        )
        
        return {
            "resource_type": res_type,
            "last_updated": max_updated,
            "extracted_at": end_time.isoformat(),
            "record_count": bundle_count,
            "page_count": page_count,
            "success": True,
            "duration_seconds": duration,
            "error_count": error_count,
        }
    
    def extract_patient_resource(patient_id: str, res_type: str, res_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patient-scoped resources for a specific patient."""
        logger.info(f"Extracting {res_type} for patient {patient_id}")
        
        # Implementation would be similar to extract_resource but with patient context
        # This would be implemented if we're doing patient-by-patient extraction
        pass
    
    # Extract independent resources in parallel
    new_cursors = []
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all extraction tasks
        future_to_resource = {
            executor.submit(extract_resource, res_type, res_config): res_type
            for res_type, res_config in independent_resources
        }
        
        # Process results as they complete
        for future in as_completed(future_to_resource):
            result = future.result()
            res_type = future_to_resource[future]
            
            if result["success"]:
                new_cursors.append(result)
                success_count += 1
            else:
                error_count += 1
                logger.error(f"Failed to extract {res_type}: {result.get('error', 'Unknown error')}")
    
    # For patient-scoped resources we could:
    # 1. Extract all patients first
    # 2. For each patient, extract all required resources
    # This is more complex and would be implemented based on specific requirements
    
    # Update cursors
    if new_cursors:
        # Create DataFrame from new cursors
        new_cursor_rows = []
        for cursor in new_cursors:
            # Only include fields that exist in the cursor schema
            new_cursor_rows.append({
                "resource_type": cursor["resource_type"],
                "last_updated": cursor["last_updated"],
                "extracted_at": cursor["extracted_at"],
                "record_count": str(cursor["record_count"]),
            })
        
        new_cursor_df = spark.createDataFrame(new_cursor_rows)
        
        # Merge with existing cursors
        resource_types = [c["resource_type"] for c in new_cursors]
        updated_cursors = cursor_df.filter(~cursor_df.resource_type.isin(resource_types))
        updated_cursors = updated_cursors.union(new_cursor_df)
        
        # Write back to cursors dataset
        cursors.write_dataframe(updated_cursors)
    
    logger.info(f"Extraction complete. Success: {success_count}, Errors: {error_count}")


# Allow command-line usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract FHIR resources")
    parser.add_argument("--resource", help="Specific resource type to extract")
    parser.add_argument("--workers", type=int, default=4, help="Maximum number of concurrent workers")
    args = parser.parse_args()
    
    # When running locally, you would need to set up connections to Foundry datasets
    # This is just a sketch of how it would work
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("fhir_extract").getOrCreate()
    
    # In a real scenario, you would need to connect to Foundry datasets
    extract_resources(spark, None, None, None, None, None, args.resource, args.workers)
