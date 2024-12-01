#!/usr/bin/env python3
"""
Transform Silver to Gold Layer

This script transforms normalized FHIR data from the silver layer into 
more business-friendly formats in the gold layer.

It reads Parquet files from the silver/fhir_normalized directory and creates
summary tables and views in the gold layer.
"""

import os
import sys
import logging
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent dir to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_debug_logging(enable_debug: bool):
    """Configure debug logging."""
    if enable_debug:
        logger.setLevel(logging.DEBUG)
        # Log to file
        debug_file = Path("debug_gold.log")
        file_handler = logging.FileHandler(debug_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug("Debug logging enabled")

def read_silver_parquet(silver_dir: Path, resource_type: str) -> Optional[pd.DataFrame]:
    """
    Read silver layer Parquet file for a resource type.
    
    Args:
        silver_dir: Silver layer directory
        resource_type: Resource type to read
        
    Returns:
        DataFrame with resource data or None if not found
    """
    # Construct file path
    file_path = silver_dir / f"{resource_type.lower()}.parquet"
    
    if not file_path.exists():
        logger.warning(f"No silver layer data found for {resource_type}")
        return None
        
    logger.info(f"Reading {resource_type} data from {file_path}")
    
    try:
        df = pd.read_parquet(file_path)
        logger.info(f"Read {len(df)} {resource_type} records with {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error reading {resource_type} data: {str(e)}")
        if logger.level <= logging.DEBUG:
            import traceback
            logger.debug(f"Error details: {traceback.format_exc()}")
        return None

def create_patient_summary(silver_dir: Path, gold_dir: Path):
    """
    Create patient summary dataset in gold layer.
    
    Args:
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
    """
    logger.info("Creating patient summary")
    
    # Read patient data
    patients_df = read_silver_parquet(silver_dir, "patient")
    
    if patients_df is None or patients_df.empty:
        logger.warning("No patient data found, skipping patient summary")
        return
    
    # Create basic patient summary
    summary_df = pd.DataFrame()
    
    # Extract key fields
    summary_df["patient_id"] = patients_df["id"].astype(str)
    
    # Extract name
    if "name.family" in patients_df.columns:
        summary_df["family_name"] = patients_df["name.family"]
    
    if "name.given" in patients_df.columns:
        summary_df["given_name"] = patients_df["name.given"]
    
    # Extract gender and birth date
    if "gender" in patients_df.columns:
        summary_df["gender"] = patients_df["gender"]
        
    if "birthDate" in patients_df.columns:
        summary_df["birth_date"] = pd.to_datetime(patients_df["birthDate"], errors='coerce')
    
    # Add active status
    if "active" in patients_df.columns:
        summary_df["active"] = patients_df["active"]
    
    logger.info(f"Created patient summary with {len(summary_df)} patients")
    
    # Write to gold layer
    file_path = gold_dir / "patient_summary.parquet"
    summary_df.to_parquet(file_path, index=False)
    
    logger.info(f"Wrote patient summary to {file_path}")

def create_observation_summary(silver_dir: Path, gold_dir: Path):
    """
    Create observation summary dataset in gold layer.
    
    Args:
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
    """
    logger.info("Creating observation summary")
    
    # Read observation data
    observations_df = read_silver_parquet(silver_dir, "observation")
    
    if observations_df is None or observations_df.empty:
        logger.warning("No observation data found, skipping observation summary")
        return
    
    # Create basic observation summary
    summary_df = pd.DataFrame()
    
    # Extract key fields
    if "id" in observations_df.columns:
        summary_df["observation_id"] = observations_df["id"].astype(str)
    
    # Extract patient reference
    if "subject.reference" in observations_df.columns:
        # Extract patient ID from reference (Patient/id)
        summary_df["patient_id"] = observations_df["subject.reference"].str.extract(r'Patient/(.+)', expand=False)
    
    # Extract code information
    if "code.coding.code" in observations_df.columns:
        summary_df["code"] = observations_df["code.coding.code"]
        
    if "code.coding.display" in observations_df.columns:
        summary_df["display"] = observations_df["code.coding.display"]
        
    if "code.coding.system" in observations_df.columns:
        summary_df["system"] = observations_df["code.coding.system"]
    
    # Extract value
    # For quantitative observations
    if "valueQuantity.value" in observations_df.columns:
        summary_df["value"] = observations_df["valueQuantity.value"].astype(float, errors='ignore')
        
    if "valueQuantity.unit" in observations_df.columns:
        summary_df["unit"] = observations_df["valueQuantity.unit"]
    
    # Extract date
    if "effectiveDateTime" in observations_df.columns:
        summary_df["effective_date"] = pd.to_datetime(observations_df["effectiveDateTime"], errors='coerce')
    
    # Extract status
    if "status" in observations_df.columns:
        summary_df["status"] = observations_df["status"]
    
    logger.info(f"Created observation summary with {len(summary_df)} observations")
    
    # Write to gold layer
    file_path = gold_dir / "observation_summary.parquet"
    summary_df.to_parquet(file_path, index=False)
    
    logger.info(f"Wrote observation summary to {file_path}")

def create_encounter_summary(silver_dir: Path, gold_dir: Path):
    """
    Create encounter summary dataset in gold layer.
    
    Args:
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
    """
    logger.info("Creating encounter summary")
    
    # Read encounter data
    encounters_df = read_silver_parquet(silver_dir, "encounter")
    
    if encounters_df is None or encounters_df.empty:
        logger.warning("No encounter data found, skipping encounter summary")
        return
    
    # Create basic encounter summary
    summary_df = pd.DataFrame()
    
    # Extract key fields
    if "id" in encounters_df.columns:
        summary_df["encounter_id"] = encounters_df["id"].astype(str)
    
    # Extract patient reference
    if "subject.reference" in encounters_df.columns:
        # Extract patient ID from reference (Patient/id)
        summary_df["patient_id"] = encounters_df["subject.reference"].str.extract(r'Patient/(.+)', expand=False)
    
    # Extract class information
    if "class.code" in encounters_df.columns:
        summary_df["class_code"] = encounters_df["class.code"]
        
    if "class.display" in encounters_df.columns:
        summary_df["class_display"] = encounters_df["class.display"]
    
    # Extract date range
    if "period.start" in encounters_df.columns:
        summary_df["start_date"] = pd.to_datetime(encounters_df["period.start"], errors='coerce')
        
    if "period.end" in encounters_df.columns:
        summary_df["end_date"] = pd.to_datetime(encounters_df["period.end"], errors='coerce')
    
    # Extract status
    if "status" in encounters_df.columns:
        summary_df["status"] = encounters_df["status"]
    
    logger.info(f"Created encounter summary with {len(summary_df)} encounters")
    
    # Write to gold layer
    file_path = gold_dir / "encounter_summary.parquet"
    summary_df.to_parquet(file_path, index=False)
    
    logger.info(f"Wrote encounter summary to {file_path}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Transform silver FHIR data to gold")
    parser.add_argument("--silver-dir", required=True, help="Silver layer directory")
    parser.add_argument("--gold-dir", required=True, help="Gold layer output directory")
    parser.add_argument("--summaries", default="patient,observation,encounter", help="Comma-separated list of summaries to create")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup debug logging if requested
    setup_debug_logging(args.debug)
    
    # Configure input/output directories
    silver_dir = Path(args.silver_dir) / "fhir_normalized"
    gold_dir = Path(args.gold_dir)
    
    # Make sure directories exist
    if not silver_dir.exists() or not silver_dir.is_dir():
        logger.error(f"Silver directory {silver_dir} does not exist")
        return 1
    
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse summaries to create
    requested_summaries = [s.strip().lower() for s in args.summaries.split(',')]
    logger.info(f"Creating summaries: {', '.join(requested_summaries)}")
    
    # Create gold datasets
    if "patient" in requested_summaries:
        create_patient_summary(silver_dir, gold_dir)
    
    if "observation" in requested_summaries:
        create_observation_summary(silver_dir, gold_dir)
        
    if "encounter" in requested_summaries:
        create_encounter_summary(silver_dir, gold_dir)
    
    logger.info("Silver to Gold transformation complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 