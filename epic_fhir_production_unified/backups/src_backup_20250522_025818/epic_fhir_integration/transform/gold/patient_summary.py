"""
Patient summary transformer for the Gold layer.

This module transforms Patient data from the Silver layer into the Gold layer.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Union

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, lit, array, struct, to_date, to_timestamp, 
    when, expr, concat, split, first, last, udf
)
from pyspark.sql.types import StringType, ArrayType, StructType, StructField

from fhir.resources.patient import Patient

from epic_fhir_integration.schemas.gold import PATIENT_SCHEMA
from epic_fhir_integration.schemas.fhir_resources import parse_resource
from epic_fhir_integration.transform.patient_transform import legacy_transform_patient, transform_patient_to_row

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatientSummary:
    """Transformer for Patient resources to the Gold layer."""
    
    def __init__(
        self,
        spark: SparkSession,
        silver_path: Union[str, Path] = None,
        gold_path: Union[str, Path] = None,
    ):
        """Initialize a new Patient summary transformer.
        
        Args:
            spark: Spark session.
            silver_path: Path to the silver layer data.
            gold_path: Path to the gold layer output.
        """
        self.spark = spark
        
        # Set default paths if not provided
        if silver_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            silver_path = base_dir / "output" / "silver"
        elif isinstance(silver_path, str):
            silver_path = Path(silver_path)
        
        if gold_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            gold_path = base_dir / "output" / "gold"
        elif isinstance(gold_path, str):
            gold_path = Path(gold_path)
        
        self.silver_path = silver_path
        self.gold_path = gold_path
        
        # Create gold output directory
        (self.gold_path / "patient").mkdir(parents=True, exist_ok=True)
    
    def load_silver_data(self) -> DataFrame:
        """Load Patient data from the Silver layer.
        
        Returns:
            DataFrame containing Silver layer Patient data.
        """
        silver_patient_path = self.silver_path / "patient"
        
        if not silver_patient_path.exists():
            raise ValueError(f"Silver layer path does not exist: {silver_patient_path}")
        
        logger.info(f"Loading Patient data from Silver layer: {silver_patient_path}")
        df = self.spark.read.parquet(str(silver_patient_path))
        
        return df
    
    def transform_using_model(self, patient_dict: Dict) -> Dict:
        """
        Transform a patient dictionary to Gold format using FHIR resources model.
        
        Args:
            patient_dict: Dictionary containing Patient data
            
        Returns:
            Dictionary in Gold layer format
        """
        try:
            # First try to convert to Patient model
            patient_model = parse_resource(patient_dict)
            
            # Use our patient transform module
            patient_row = transform_patient_to_row(patient_model)
            
            # Map to Gold format
            return {
                "patient_id": patient_row.get("patient_id", ""),
                "mrn": next((identifier["value"] for identifier in patient_dict.get("identifier", []) 
                              if identifier.get("system") == "http://terminology.hl7.org/CodeSystem/v2-0203" 
                              and identifier.get("type", {}).get("coding", [{}])[0].get("code") == "MR"), None),
                "first_name": patient_row.get("name_first", ""),
                "last_name": patient_row.get("name_family", ""),
                "birth_date": patient_row.get("birth_date", ""),
                "gender": patient_row.get("gender", ""),
                "address_line1": patient_row.get("address_street", "").split("; ")[0] if patient_row.get("address_street") else "",
                "address_line2": "; ".join(patient_row.get("address_street", "").split("; ")[1:]) if patient_row.get("address_street") and len(patient_row.get("address_street", "").split("; ")) > 1 else "",
                "city": patient_row.get("address_city", ""),
                "state": patient_row.get("address_state", ""),
                "postal_code": patient_row.get("address_postal_code", ""),
                "country": patient_row.get("address_country", ""),
                "phone": patient_row.get("phone_home", "") or patient_row.get("phone", ""),
                "email": patient_row.get("email", ""),
                "marital_status": "",  # Extract from maritalStatus if needed
                "language": patient_row.get("language", ""),
                "race": patient_row.get("race", ""),
                "ethnicity": patient_row.get("ethnicity", ""),
                "is_deceased": False,  # Extract from deceasedBoolean/deceasedDateTime if needed
                "deceased_date": None,  # Extract from deceasedDateTime if needed
                "primary_care_provider_id": None,  # Extract from generalPractitioner if needed
                "primary_care_provider_name": None,  # Extract from generalPractitioner if needed
                "insurance_plans": [],  # Would typically come from Coverage resource
                "created_at": patient_dict.get("meta", {}).get("lastUpdated", ""),
                "updated_at": patient_dict.get("meta", {}).get("lastUpdated", ""),
                "source_system": "EPIC",
                "source_version": patient_dict.get("meta", {}).get("versionId", "1"),
            }
        except Exception as e:
            logger.warning(f"Error transforming patient using model: {e}")
            # Fall back to the original transform approach
            return None
    
    def transform(self, silver_df: Optional[DataFrame] = None) -> DataFrame:
        """Transform Silver layer Patient data to Gold layer format.
        
        Args:
            silver_df: DataFrame containing Silver layer Patient data.
                      If not provided, it will be loaded from the Silver layer.
                      
        Returns:
            DataFrame in Gold layer format.
        """
        # Load silver data if not provided
        if silver_df is None:
            silver_df = self.load_silver_data()
        
        logger.info("Transforming Patient data to Gold layer format")
        
        # First, try transforming a few patients using the new FHIR resources approach
        # If it works, use it for all patients; otherwise, fall back to the original approach
        sample_patients = silver_df.limit(5).collect()
        
        # Check if we can use the new approach with any of the sample patients
        can_use_new_approach = False
        for patient in sample_patients:
            patient_dict = patient.asDict(recursive=True)
            result = self.transform_using_model(patient_dict)
            if result is not None:
                can_use_new_approach = True
                break
        
        if can_use_new_approach:
            logger.info("Using FHIR resources model for patient transformation")
            
            # Register UDF for transforming patients
            @udf(returnType=PATIENT_SCHEMA)
            def transform_patient_udf(patient_dict):
                result = self.transform_using_model(patient_dict)
                if result is not None:
                    return result
                
                # Fall back to the original approach if the new one fails
                return {
                    "patient_id": patient_dict.get("id", ""),
                    "mrn": next((identifier["value"] for identifier in patient_dict.get("identifier", []) 
                                if identifier.get("system") == "http://terminology.hl7.org/CodeSystem/v2-0203" 
                                and identifier.get("type", {}).get("coding", [{}])[0].get("code") == "MR"), None),
                    "first_name": next((name.get("given", [""])[0] for name in patient_dict.get("name", []) 
                                        if name.get("use") == "official" or name.get("use") is None and name.get("given")), ""),
                    "last_name": next((name.get("family", "") for name in patient_dict.get("name", []) 
                                      if name.get("use") == "official" or name.get("use") is None), ""),
                    "birth_date": patient_dict.get("birthDate", ""),
                    "gender": patient_dict.get("gender", ""),
                    "address_line1": next((addr.get("line", [""])[0] for addr in patient_dict.get("address", []) 
                                          if addr.get("use") == "home" or addr.get("use") is None and addr.get("line")), ""),
                    "address_line2": next((addr.get("line", ["", ""])[1] if len(addr.get("line", [])) > 1 else "" 
                                          for addr in patient_dict.get("address", []) 
                                          if addr.get("use") == "home" or addr.get("use") is None), ""),
                    "city": next((addr.get("city", "") for addr in patient_dict.get("address", []) 
                                 if addr.get("use") == "home" or addr.get("use") is None), ""),
                    "state": next((addr.get("state", "") for addr in patient_dict.get("address", []) 
                                  if addr.get("use") == "home" or addr.get("use") is None), ""),
                    "postal_code": next((addr.get("postalCode", "") for addr in patient_dict.get("address", []) 
                                         if addr.get("use") == "home" or addr.get("use") is None), ""),
                    "country": next((addr.get("country", "") for addr in patient_dict.get("address", []) 
                                    if addr.get("use") == "home" or addr.get("use") is None), ""),
                    "phone": next((telecom.get("value", "") for telecom in patient_dict.get("telecom", []) 
                                  if telecom.get("system") == "phone" and (telecom.get("use") == "home" or telecom.get("use") is None)), ""),
                    "email": next((telecom.get("value", "") for telecom in patient_dict.get("telecom", []) 
                                  if telecom.get("system") == "email"), ""),
                    "marital_status": patient_dict.get("maritalStatus", {}).get("coding", [{}])[0].get("display", "") if patient_dict.get("maritalStatus") else "",
                    "language": "",  # Would need more complex extraction
                    "race": "",      # Would need extension extraction
                    "ethnicity": "", # Would need extension extraction
                    "is_deceased": bool(patient_dict.get("deceasedBoolean", False)) or bool(patient_dict.get("deceasedDateTime", "")),
                    "deceased_date": patient_dict.get("deceasedDateTime", ""),
                    "primary_care_provider_id": None,  # Would need reference extraction
                    "primary_care_provider_name": None,  # Would need reference extraction
                    "insurance_plans": [],  # Would typically come from Coverage resource
                    "created_at": patient_dict.get("meta", {}).get("lastUpdated", ""),
                    "updated_at": patient_dict.get("meta", {}).get("lastUpdated", ""),
                    "source_system": "EPIC",
                    "source_version": patient_dict.get("meta", {}).get("versionId", "1"),
                }
            
            # Convert each patient using the UDF
            gold_df = silver_df.select(
                transform_patient_udf(to_struct("*")).alias("patient")
            ).select("patient.*")
            
            # Handle date fields that might be strings
            gold_df = gold_df.withColumn("birth_date", to_date(col("birth_date")))
            gold_df = gold_df.withColumn("deceased_date", to_date(col("deceased_date")))
            gold_df = gold_df.withColumn("created_at", to_timestamp(col("created_at")))
            gold_df = gold_df.withColumn("updated_at", to_timestamp(col("updated_at")))
            
        else:
            logger.info("Using original transformation approach")
            # Use the original transformation approach
            gold_df = silver_df.select(
                # Required fields
                col("id").alias("patient_id"),
                
                # Basic demographics
                when(col("identifier").isNotNull(), 
                     expr("transform(identifier, x -> CASE WHEN x.system = 'http://terminology.hl7.org/CodeSystem/v2-0203' AND x.type.coding[0].code = 'MR' THEN x.value ELSE NULL END)[0]")
                ).alias("mrn"),
                
                when(col("name").isNotNull(),
                     expr("transform(name, x -> CASE WHEN x.use = 'official' OR x.use IS NULL THEN x.given[0] ELSE NULL END)[0]")
                ).alias("first_name"),
                
                when(col("name").isNotNull(),
                     expr("transform(name, x -> CASE WHEN x.use = 'official' OR x.use IS NULL THEN x.family ELSE NULL END)[0]")
                ).alias("last_name"),
                
                to_date(col("birthDate")).alias("birth_date"),
                col("gender"),
                
                # Address information
                when(col("address").isNotNull(),
                     expr("transform(address, x -> CASE WHEN x.use = 'home' OR x.use IS NULL THEN x.line[0] ELSE NULL END)[0]")
                ).alias("address_line1"),
                
                when(col("address").isNotNull(),
                     expr("transform(address, x -> CASE WHEN x.use = 'home' OR x.use IS NULL AND size(x.line) > 1 THEN x.line[1] ELSE NULL END)[0]")
                ).alias("address_line2"),
                
                when(col("address").isNotNull(),
                     expr("transform(address, x -> CASE WHEN x.use = 'home' OR x.use IS NULL THEN x.city ELSE NULL END)[0]")
                ).alias("city"),
                
                when(col("address").isNotNull(),
                     expr("transform(address, x -> CASE WHEN x.use = 'home' OR x.use IS NULL THEN x.state ELSE NULL END)[0]")
                ).alias("state"),
                
                when(col("address").isNotNull(),
                     expr("transform(address, x -> CASE WHEN x.use = 'home' OR x.use IS NULL THEN x.postalCode ELSE NULL END)[0]")
                ).alias("postal_code"),
                
                when(col("address").isNotNull(),
                     expr("transform(address, x -> CASE WHEN x.use = 'home' OR x.use IS NULL THEN x.country ELSE NULL END)[0]")
                ).alias("country"),
                
                # Contact information
                when(col("telecom").isNotNull(),
                     expr("transform(telecom, x -> CASE WHEN x.system = 'phone' AND (x.use = 'home' OR x.use IS NULL) THEN x.value ELSE NULL END)[0]")
                ).alias("phone"),
                
                when(col("telecom").isNotNull(),
                     expr("transform(telecom, x -> CASE WHEN x.system = 'email' THEN x.value ELSE NULL END)[0]")
                ).alias("email"),
                
                # Other demographics
                when(col("maritalStatus").isNotNull(),
                     col("maritalStatus.coding[0].display")
                ).alias("marital_status"),
                
                when(col("communication").isNotNull(),
                     expr("transform(communication, x -> CASE WHEN x.preferred = true THEN x.language.coding[0].display ELSE NULL END)[0]")
                ).alias("language"),
                
                # Race and ethnicity
                when(col("extension").isNotNull(),
                     expr("transform(extension, x -> CASE WHEN x.url = 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-race' THEN x.extension[0].valueCoding.display ELSE NULL END)[0]")
                ).alias("race"),
                
                when(col("extension").isNotNull(),
                     expr("transform(extension, x -> CASE WHEN x.url = 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity' THEN x.extension[0].valueCoding.display ELSE NULL END)[0]")
                ).alias("ethnicity"),
                
                # Deceased information
                when(col("deceasedBoolean").isNotNull(), col("deceasedBoolean"))
                .when(col("deceasedDateTime").isNotNull(), lit(True))
                .otherwise(lit(False)).alias("is_deceased"),
                
                to_date(col("deceasedDateTime")).alias("deceased_date"),
                
                # Provider information
                when(col("generalPractitioner").isNotNull(),
                     expr("transform(generalPractitioner, x -> CASE WHEN x.reference LIKE 'Practitioner/%' THEN substring(x.reference, 13) ELSE NULL END)[0]")
                ).alias("primary_care_provider_id"),
                
                when(col("generalPractitioner").isNotNull(),
                     expr("transform(generalPractitioner, x -> x.display)[0]")
                ).alias("primary_care_provider_name"),
                
                # Insurance plans (simplified as this would likely come from Coverage resource)
                array().alias("insurance_plans"),
                
                # Metadata
                to_timestamp(expr("meta.lastUpdated")).alias("created_at"),
                to_timestamp(expr("meta.lastUpdated")).alias("updated_at"),
                lit("EPIC").alias("source_system"),
                when(col("meta.versionId").isNotNull(), col("meta.versionId")).otherwise(lit("1")).alias("source_version"),
            )
        
        # Validate against schema
        gold_df = self.spark.createDataFrame(gold_df.rdd, PATIENT_SCHEMA)
        
        return gold_df
    
    def write(self, gold_df: DataFrame) -> None:
        """Write the Gold layer DataFrame to Parquet.
        
        Args:
            gold_df: DataFrame in Gold layer format.
        """
        output_path = self.gold_path / "patient"
        logger.info(f"Writing Patient data to Gold layer: {output_path}")
        
        gold_df.write.mode("overwrite").parquet(str(output_path))
    
    def execute(self) -> None:
        """Execute the full ETL process for Patient data."""
        try:
            # Load silver data
            silver_df = self.load_silver_data()
            
            # Transform to gold
            gold_df = self.transform(silver_df)
            
            # Write to gold layer
            self.write(gold_df)
            
            logger.info("Patient Gold ETL completed successfully")
            
        except Exception as e:
            logger.error(f"Error in Patient Gold ETL: {e}")
            raise 