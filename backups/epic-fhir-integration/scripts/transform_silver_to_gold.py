#!/usr/bin/env python3
"""
Silver to Gold Transformation Script

This script transforms data from the FHIR normalized silver layer to the gold layer
with analytical summaries, removing all mock data fallbacks.

Usage:
    python transform_silver_to_gold.py --silver-dir DIR --gold-dir DIR [--summaries LIST] [--debug]

Example:
    python transform_silver_to_gold.py --silver-dir output/silver --gold-dir output/gold --summaries patient,encounter,observation
"""

import os
import sys
import time
import logging
import argparse
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the repository root to the Python path
repo_root = Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, str(repo_root))

try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.errors import AnalysisException
except ImportError:
    print("PySpark not found. Please install pyspark package.", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_logging(debug_mode: bool):
    """Configure logging based on debug mode."""
    if debug_mode:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("pyspark").setLevel(logging.WARN)
        
        # Add file handler for debugging
        debug_log_file = Path("silver_to_gold_debug.log")
        file_handler = logging.FileHandler(debug_log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug("Debug logging enabled")

def get_spark_session() -> SparkSession:
    """Create and configure a Spark session for gold transforms."""
    logger.debug("Creating Spark session for gold transformations")
    
    # Setup Delta Lake catalog if available
    packages = []
    try:
        # Try to include Delta Lake
        import delta
        delta_version = delta.__version__
        packages.append(f"io.delta:delta-core_{pyspark.__version__[:3]}:{delta_version}")
        logger.debug(f"Including Delta Lake package: {packages[-1]}")
    except ImportError:
        logger.warning("Delta Lake not found, proceeding with standard Parquet")
    
    # Create Spark session
    builder = (
        SparkSession.builder
        .appName("FHIR Silver to Gold")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    
    # Add packages if any
    if packages:
        builder = builder.config("spark.jars.packages", ",".join(packages))
    
    spark = builder.getOrCreate()
    
    logger.debug(f"Created Spark session v{spark.version}")
    return spark

def validate_silver_data(silver_dir: Path) -> Dict[str, bool]:
    """
    Validate that required silver data exists.
    
    Args:
        silver_dir: Silver layer directory
        
    Returns:
        Dict of resource types with existence status
    """
    logger.info("Validating silver layer data")
    
    # Required resource types for gold transforms
    required_resources = {
        "patient": False,
        "encounter": False,
        "observation": False,
        "condition": False,
        "medicationrequest": False
    }
    
    silver_normalized_dir = silver_dir / "fhir_normalized"
    if not silver_normalized_dir.exists():
        logger.error(f"Silver normalized directory not found: {silver_normalized_dir}")
        return required_resources
        
    # Check each resource type
    for resource_type in required_resources.keys():
        resource_file = silver_normalized_dir / f"{resource_type}.parquet"
        if resource_file.exists():
            required_resources[resource_type] = True
            logger.debug(f"Found silver data for {resource_type}")
        else:
            logger.warning(f"Missing silver data for {resource_type}")
    
    # Summary
    available_resources = [k for k, v in required_resources.items() if v]
    logger.info(f"Available silver resources: {', '.join(available_resources)}")
    
    return required_resources

def transform_patient_summary(spark: SparkSession, silver_dir: Path, gold_dir: Path) -> bool:
    """
    Transform patient data to create patient summary gold dataset.
    
    Args:
        spark: Spark session
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
        
    Returns:
        Success status
    """
    logger.info("Transforming patient data to gold patient summary")
    start_time = time.time()
    
    # Ensure output directory exists
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # Path to silver patient data
    silver_patient_path = silver_dir / "fhir_normalized" / "patient.parquet"
    
    # Verify silver data exists
    if not silver_patient_path.exists():
        logger.error(f"Silver patient data not found: {silver_patient_path}")
        return False
    
    try:
        # Load patient data
        logger.debug(f"Loading patient data from {silver_patient_path}")
        patients_df = spark.read.parquet(str(silver_patient_path))
        
        # If no data, fail
        if patients_df.count() == 0:
            logger.error("No patient data found in silver layer")
            return False
        
        # Import patient_summary module
        sys.path.insert(0, str(repo_root / "pipelines" / "gold"))
        try:
            from pipelines.gold.patient_summary import create_patient_summary
            
            # Create patient summary
            logger.debug("Creating patient summary")
            summary_df = create_patient_summary(spark, patients_df)
            
            # Save to gold layer
            gold_output_path = gold_dir / "patient_summary.parquet"
            logger.debug(f"Writing patient summary to {gold_output_path}")
            summary_df.write.mode("overwrite").parquet(str(gold_output_path))
            
            # Verify output
            if gold_output_path.exists():
                logger.info(f"Patient summary created successfully")
                return True
            else:
                logger.error(f"Failed to create patient summary output")
                return False
                
        except ImportError as e:
            logger.error(f"Failed to import patient_summary module: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating patient summary: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        elapsed = time.time() - start_time
        logger.debug(f"Patient summary transform took {elapsed:.2f} seconds")

def transform_encounter_summary(spark: SparkSession, silver_dir: Path, gold_dir: Path) -> bool:
    """
    Transform encounter data to create encounter summary gold dataset.
    
    Args:
        spark: Spark session
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
        
    Returns:
        Success status
    """
    logger.info("Transforming encounter data to gold encounter summary")
    start_time = time.time()
    
    # Ensure output directory exists
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # Path to silver encounter data
    silver_encounter_path = silver_dir / "fhir_normalized" / "encounter.parquet"
    
    # Verify silver data exists
    if not silver_encounter_path.exists():
        logger.error(f"Silver encounter data not found: {silver_encounter_path}")
        return False
    
    try:
        # Load encounter data
        logger.debug(f"Loading encounter data from {silver_encounter_path}")
        encounters_df = spark.read.parquet(str(silver_encounter_path))
        
        # If no data, fail
        if encounters_df.count() == 0:
            logger.error("No encounter data found in silver layer")
            return False
        
        # Import encounter_summary module
        sys.path.insert(0, str(repo_root / "pipelines" / "gold"))
        try:
            from pipelines.gold.encounter_summary import create_encounter_summary
            
            # Create encounter summary
            logger.debug("Creating encounter summary")
            summary_df = create_encounter_summary(spark, encounters_df)
            
            # Save to gold layer
            gold_output_path = gold_dir / "encounter_summary.parquet"
            logger.debug(f"Writing encounter summary to {gold_output_path}")
            summary_df.write.mode("overwrite").parquet(str(gold_output_path))
            
            # Verify output
            if gold_output_path.exists():
                logger.info(f"Encounter summary created successfully")
                return True
            else:
                logger.error(f"Failed to create encounter summary output")
                return False
                
        except ImportError as e:
            logger.error(f"Failed to import encounter_summary module: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating encounter summary: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        elapsed = time.time() - start_time
        logger.debug(f"Encounter summary transform took {elapsed:.2f} seconds")

def transform_observation_summary(spark: SparkSession, silver_dir: Path, gold_dir: Path) -> bool:
    """
    Transform observation data to create observation summary gold dataset.
    
    Args:
        spark: Spark session
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
        
    Returns:
        Success status
    """
    logger.info("Transforming observation data to gold observation summary")
    start_time = time.time()
    
    # Ensure output directory exists
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # Path to silver observation data
    silver_observation_path = silver_dir / "fhir_normalized" / "observation.parquet"
    
    # Verify silver data exists
    if not silver_observation_path.exists():
        logger.error(f"Silver observation data not found: {silver_observation_path}")
        return False
    
    try:
        # Load observation data
        logger.debug(f"Loading observation data from {silver_observation_path}")
        observations_df = spark.read.parquet(str(silver_observation_path))
        
        # If no data, fail
        if observations_df.count() == 0:
            logger.error("No observation data found in silver layer")
            return False
        
        # Import observation_summary module
        sys.path.insert(0, str(repo_root / "pipelines" / "gold"))
        try:
            from pipelines.gold.observation_summary import create_observation_summary
            
            # Create observation summary
            logger.debug("Creating observation summary")
            summary_df = create_observation_summary(spark, observations_df)
            
            # Save to gold layer
            gold_output_path = gold_dir / "observation_summary.parquet"
            logger.debug(f"Writing observation summary to {gold_output_path}")
            summary_df.write.mode("overwrite").parquet(str(gold_output_path))
            
            # Verify output
            if gold_output_path.exists():
                logger.info(f"Observation summary created successfully")
                return True
            else:
                logger.error(f"Failed to create observation summary output")
                return False
                
        except ImportError as e:
            logger.error(f"Failed to import observation_summary module: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating observation summary: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        elapsed = time.time() - start_time
        logger.debug(f"Observation summary transform took {elapsed:.2f} seconds")

def transform_medication_summary(spark: SparkSession, silver_dir: Path, gold_dir: Path) -> bool:
    """
    Transform medication data to create medication summary gold dataset.
    
    Args:
        spark: Spark session
        silver_dir: Silver layer directory
        gold_dir: Gold layer directory
        
    Returns:
        Success status
    """
    logger.info("Transforming medication data to gold medication summary")
    start_time = time.time()
    
    # Ensure output directory exists
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # Path to silver medication data
    silver_medication_path = silver_dir / "fhir_normalized" / "medicationrequest.parquet"
    
    # Verify silver data exists
    if not silver_medication_path.exists():
        logger.error(f"Silver medication data not found: {silver_medication_path}")
        return False
    
    try:
        # Load medication data
        logger.debug(f"Loading medication data from {silver_medication_path}")
        medications_df = spark.read.parquet(str(silver_medication_path))
        
        # If no data, fail
        if medications_df.count() == 0:
            logger.error("No medication data found in silver layer")
            return False
        
        # Import medication_summary module
        sys.path.insert(0, str(repo_root / "pipelines" / "gold"))
        try:
            from pipelines.gold.medication_summary import create_medication_summary
            
            # Create medication summary
            logger.debug("Creating medication summary")
            summary_df = create_medication_summary(spark, medications_df)
            
            # Save to gold layer
            gold_output_path = gold_dir / "medication_summary.parquet"
            logger.debug(f"Writing medication summary to {gold_output_path}")
            summary_df.write.mode("overwrite").parquet(str(gold_output_path))
            
            # Verify output
            if gold_output_path.exists():
                logger.info(f"Medication summary created successfully")
                return True
            else:
                logger.error(f"Failed to create medication summary output")
                return False
                
        except ImportError as e:
            logger.error(f"Failed to import medication_summary module: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating medication summary: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        elapsed = time.time() - start_time
        logger.debug(f"Medication summary transform took {elapsed:.2f} seconds")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Transform FHIR silver data to gold layer")
    parser.add_argument("--silver-dir", required=True, help="Silver layer directory")
    parser.add_argument("--gold-dir", required=True, help="Gold layer output directory")
    parser.add_argument("--summaries", default="patient,encounter,observation,medication",
                       help="Comma-separated list of summaries to generate")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    logger.info("Starting silver to gold transformation")
    
    # Convert paths
    silver_dir = Path(args.silver_dir)
    gold_dir = Path(args.gold_dir)
    
    # Parse summaries
    summaries = [s.strip().lower() for s in args.summaries.split(",")]
    logger.info(f"Requested summaries: {', '.join(summaries)}")
    
    # Validate input
    if not silver_dir.exists():
        logger.error(f"Silver directory does not exist: {silver_dir}")
        return 1
        
    # Create gold directory
    gold_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate silver data
    silver_resources = validate_silver_data(silver_dir)
    missing_resources = [k for k, v in silver_resources.items() if not v]
    if missing_resources:
        logger.warning(f"Missing silver resources: {', '.join(missing_resources)}")
    
    # Create Spark session
    try:
        spark = get_spark_session()
    except Exception as e:
        logger.error(f"Failed to create Spark session: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1
    
    # Run requested summaries
    results = {}
    
    if "patient" in summaries:
        if silver_resources.get("patient", False):
            results["patient"] = transform_patient_summary(spark, silver_dir, gold_dir)
        else:
            logger.error("Cannot create patient summary: patient data not available")
            results["patient"] = False
    
    if "encounter" in summaries:
        if silver_resources.get("encounter", False):
            results["encounter"] = transform_encounter_summary(spark, silver_dir, gold_dir)
        else:
            logger.error("Cannot create encounter summary: encounter data not available")
            results["encounter"] = False
    
    if "observation" in summaries:
        if silver_resources.get("observation", False):
            results["observation"] = transform_observation_summary(spark, silver_dir, gold_dir)
        else:
            logger.error("Cannot create observation summary: observation data not available")
            results["observation"] = False
    
    if "medication" in summaries:
        if silver_resources.get("medicationrequest", False):
            results["medication"] = transform_medication_summary(spark, silver_dir, gold_dir)
        else:
            logger.error("Cannot create medication summary: medication data not available")
            results["medication"] = False
    
    # Print summary
    print("\nGOLD TRANSFORMATION SUMMARY:")
    print("="*80)
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"Successfully created {success_count} out of {total_count} gold summaries")
    
    for summary, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {summary}_summary")
    
    # Return success if all requested summaries succeeded
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main()) 