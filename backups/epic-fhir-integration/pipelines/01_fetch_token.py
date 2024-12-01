"""
Epic FHIR API OAuth Token Fetch Pipeline.

This pipeline fetches and stores an OAuth bearer token for use with the Epic FHIR API.
"""

import os
import yaml
import json
import logging
import datetime
import requests
from typing import Dict, Any

# Foundry imports
from transforms.api import Input, Output, transform, configure
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@configure(profile=["FHIR_TOKEN_REFRESH"])
@transform(
    config_input=Input("/config/api_config.yaml"),
    output=Output("/secrets/epic_token"),
)
def fetch_token(spark: SparkSession, config_input: Input, output: Output) -> None:
    """
    Fetch and store an OAuth token for the Epic FHIR API.
    
    Args:
        spark: SparkSession
        config_input: Input containing API configuration
        output: Output dataset for token storage
    """
    # Load API config
    config = load_config(config_input)
    
    # Get credentials from environment / secrets
    client_id = os.environ.get("EPIC_CLIENT_ID")
    client_secret = os.environ.get("EPIC_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError(
            "EPIC_CLIENT_ID and EPIC_CLIENT_SECRET must be set as environment variables"
        )
    
    # Fetch token
    token_data = fetch_oauth_token(
        config["api"]["token_url"], client_id, client_secret
    )
    
    # Create DataFrame with token data
    token_df = create_token_dataframe(spark, token_data)
    
    # Write to output
    output.write_dataframe(token_df)
    
    logger.info("Successfully fetched and stored Epic FHIR API token")


def load_config(config_input: Input) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_input: Input containing API configuration
        
    Returns:
        Dictionary with configuration values
    """
    try:
        config_str = config_input.read_file()
        config = yaml.safe_load(config_str)
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        raise


def fetch_oauth_token(token_url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
    """
    Fetch OAuth token from Epic's token endpoint.
    
    Args:
        token_url: Epic OAuth token endpoint URL
        client_id: Epic client ID
        client_secret: Epic client secret
        
    Returns:
        Dictionary containing token data
    """
    logger.info(f"Fetching OAuth token from {token_url}")
    
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()
        
        # Add expiration timestamp
        token_data["expires_at"] = (
            datetime.datetime.now() +
            datetime.timedelta(seconds=token_data.get("expires_in", 3600))
        ).isoformat()
        
        return token_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch OAuth token: {str(e)}")
        raise


def create_token_dataframe(spark: SparkSession, token_data: Dict[str, Any]) -> DataFrame:
    """
    Create a DataFrame containing token data.
    
    Args:
        spark: SparkSession
        token_data: Dictionary containing token data
        
    Returns:
        DataFrame with token data
    """
    # Define schema
    schema = StructType([
        StructField("access_token", StringType(), False),
        StructField("token_type", StringType(), True),
        StructField("expires_in", LongType(), True),
        StructField("scope", StringType(), True),
        StructField("expires_at", StringType(), False),
        StructField("fetch_timestamp", TimestampType(), False),
    ])
    
    # Add fetch timestamp
    token_data["fetch_timestamp"] = datetime.datetime.now()
    
    # Create DataFrame
    return spark.createDataFrame([token_data], schema=schema)


if __name__ == "__main__":
    # For local testing
    import os
    from pathlib import Path
    
    # Set environment variables
    os.environ["EPIC_CLIENT_ID"] = "test_client_id"
    os.environ["EPIC_CLIENT_SECRET"] = "test_client_secret"
    
    # Mock inputs/outputs
    config_path = Path("config/api_config.yaml")
    output_path = Path("output/secrets/epic_token")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a minimal config file if it doesn't exist
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump({
                "api": {
                    "token_url": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
                }
            }, f)
    
    # Create spark session
    spark = SparkSession.builder.appName("fetch_token").getOrCreate()
    
    # Run transform
    class MockInput:
        def read_file(self):
            with open(config_path, "r") as f:
                return f.read()
    
    class MockOutput:
        def write_dataframe(self, df):
            df.write.format("delta").mode("overwrite").save(str(output_path))
    
    fetch_token(spark, MockInput(), MockOutput())
