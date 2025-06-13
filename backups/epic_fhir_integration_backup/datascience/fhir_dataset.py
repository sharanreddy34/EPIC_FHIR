"""
FHIR dataset utilities for FHIR data.

This module provides utilities for creating datasets from FHIR resources using FHIR-PYrate.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable

import pandas as pd
from datetime import datetime, timedelta

try:
    import fhir_pyrate
    from fhir_pyrate.fhir_pit import perform_pit_analysis, generate_pit_df
    from fhir_pyrate.fhir_dataset import FHIRDataSet as FHIRPyrateDataset
    from fhir_pyrate.fhir_pit_types import ResourceColumnData
    FHIR_PYRATE_AVAILABLE = True
except ImportError:
    FHIR_PYRATE_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class FHIRDataset:
    """
    A dataset of FHIR resources, optimized for data science and machine learning tasks.
    """
    
    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize a FHIR dataset.
        
        Args:
            dataframe: Pandas DataFrame containing FHIR data
        """
        self.dataframe = dataframe
        
    def to_csv(self, path: str, **kwargs) -> None:
        """
        Save the dataset to a CSV file.
        
        Args:
            path: Path to save the CSV file
            **kwargs: Additional arguments to pass to pandas.DataFrame.to_csv
        """
        self.dataframe.to_csv(path, **kwargs)
        
    def to_parquet(self, path: str, **kwargs) -> None:
        """
        Save the dataset to a Parquet file.
        
        Args:
            path: Path to save the Parquet file
            **kwargs: Additional arguments to pass to pandas.DataFrame.to_parquet
        """
        self.dataframe.to_parquet(path, **kwargs)
        
    def filter(self, condition: Callable[[pd.DataFrame], pd.Series]) -> "FHIRDataset":
        """
        Filter the dataset using a condition.
        
        Args:
            condition: Function that takes the dataframe and returns a boolean series
            
        Returns:
            FHIRDataset: New dataset with filtered data
        """
        filtered_df = self.dataframe[condition(self.dataframe)]
        return FHIRDataset(filtered_df)
        
    def transform(self, transformation: Callable[[pd.DataFrame], pd.DataFrame]) -> "FHIRDataset":
        """
        Apply a transformation to the dataset.
        
        Args:
            transformation: Function that takes a dataframe and returns a transformed dataframe
            
        Returns:
            FHIRDataset: New dataset with transformed data
        """
        transformed_df = transformation(self.dataframe)
        return FHIRDataset(transformed_df)
        
    def head(self, n: int = 5) -> pd.DataFrame:
        """
        Get the first n rows of the dataset.
        
        Args:
            n: Number of rows to return
            
        Returns:
            pd.DataFrame: First n rows of the dataset
        """
        return self.dataframe.head(n)
        
    def describe(self) -> pd.DataFrame:
        """
        Generate descriptive statistics for the dataset.
        
        Returns:
            pd.DataFrame: Descriptive statistics
        """
        return self.dataframe.describe(include="all")


class CohortBuilder:
    """
    Builder for creating patient cohorts based on FHIR data.
    """
    
    def __init__(self, patients: List[Dict], resources: Optional[Dict[str, List[Dict]]] = None):
        """
        Initialize a cohort builder.
        
        Args:
            patients: List of Patient resources
            resources: Dictionary mapping resource types to lists of resources
        """
        if not FHIR_PYRATE_AVAILABLE:
            raise ImportError(
                "FHIR-PYrate is not available. Install it with 'pip install fhir-pyrate>=0.8.0'"
            )
            
        self.patients = patients
        self.resources = resources or {}
        self.cohort_criteria = []
        self.patient_ids = set(p.get("id") for p in patients if p.get("id"))
        
    def add_criteria(self, name: str, condition: Callable[[Dict], bool]) -> "CohortBuilder":
        """
        Add a criterion for cohort inclusion.
        
        Args:
            name: Name of the criterion
            condition: Function that takes a patient resource and returns a boolean
            
        Returns:
            CohortBuilder: Self for method chaining
        """
        self.cohort_criteria.append({"name": name, "condition": condition})
        return self
        
    def add_observation_criteria(self, 
                                name: str, 
                                code: str, 
                                system: Optional[str] = None,
                                value_condition: Optional[Callable[[Dict], bool]] = None) -> "CohortBuilder":
        """
        Add a criterion based on observations.
        
        Args:
            name: Name of the criterion
            code: Observation code
            system: Optional code system
            value_condition: Optional function to evaluate observation values
            
        Returns:
            CohortBuilder: Self for method chaining
        """
        observations = self.resources.get("Observation", [])
        
        # Filter observations by code and system
        filtered_obs = []
        for obs in observations:
            if "code" not in obs or "coding" not in obs["code"]:
                continue
                
            for coding in obs["code"]["coding"]:
                if coding.get("code") == code:
                    if system is None or coding.get("system") == system:
                        if value_condition is None or value_condition(obs):
                            # Get the patient ID from the observation
                            if "subject" in obs and "reference" in obs["subject"]:
                                ref = obs["subject"]["reference"]
                                if ref.startswith("Patient/"):
                                    patient_id = ref[8:]  # Remove "Patient/"
                                    filtered_obs.append((patient_id, obs))
        
        # Create a set of patient IDs that meet the criteria
        matching_patient_ids = set(patient_id for patient_id, _ in filtered_obs)
        
        # Add the criterion
        def criterion(patient):
            return patient.get("id") in matching_patient_ids
            
        self.cohort_criteria.append({"name": name, "condition": criterion})
        return self
        
    def build(self) -> List[Dict]:
        """
        Build the cohort based on the defined criteria.
        
        Returns:
            List[Dict]: Patient resources in the cohort
        """
        if not self.cohort_criteria:
            return self.patients
            
        cohort = []
        for patient in self.patients:
            # Check if the patient meets all criteria
            meets_criteria = True
            for criterion in self.cohort_criteria:
                if not criterion["condition"](patient):
                    meets_criteria = False
                    break
                    
            if meets_criteria:
                cohort.append(patient)
                
        return cohort
        
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the cohort to a pandas DataFrame.
        
        Returns:
            pd.DataFrame: DataFrame containing patient data
        """
        cohort = self.build()
        
        # Extract basic patient information
        data = []
        for patient in cohort:
            patient_id = patient.get("id")
            record = {
                "patient_id": patient_id,
                "gender": patient.get("gender"),
                "birth_date": patient.get("birthDate"),
            }
            
            # Extract name
            if "name" in patient and patient["name"]:
                name = patient["name"][0]
                record["family_name"] = name.get("family")
                record["given_name"] = name.get("given", [""])[0] if name.get("given") else ""
                
            # Add to data
            data.append(record)
            
        return pd.DataFrame(data)


class FHIRDatasetBuilder:
    """
    Builder for creating datasets from FHIR resources.
    """
    
    def __init__(self):
        """
        Initialize a FHIR dataset builder.
        """
        if not FHIR_PYRATE_AVAILABLE:
            raise ImportError(
                "FHIR-PYrate is not available. Install it with 'pip install fhir-pyrate>=0.8.0'"
            )
            
        self.resources_by_type = {}
        self.column_configs = []
        self.index_column = "patient_id"
        self.use_point_in_time = False
        self.reference_date = None
        self.reference_column = None
        
    def add_resources(self, resource_type: str, resources: List[Dict]) -> "FHIRDatasetBuilder":
        """
        Add FHIR resources to the builder.
        
        Args:
            resource_type: Type of resource (e.g., "Patient", "Observation")
            resources: List of FHIR resources
            
        Returns:
            FHIRDatasetBuilder: Self for method chaining
        """
        if resource_type not in self.resources_by_type:
            self.resources_by_type[resource_type] = []
            
        self.resources_by_type[resource_type].extend(resources)
        return self
        
    def set_index(self, column_name: str) -> "FHIRDatasetBuilder":
        """
        Set the index column for the dataset.
        
        Args:
            column_name: Name of the column to use as index
            
        Returns:
            FHIRDatasetBuilder: Self for method chaining
        """
        self.index_column = column_name
        return self
        
    def add_column(self, 
                  name: str, 
                  resource_type: str, 
                  fhirpath: str, 
                  default_value: Any = None) -> "FHIRDatasetBuilder":
        """
        Add a column to the dataset.
        
        Args:
            name: Name of the column
            resource_type: Type of resource to extract from
            fhirpath: FHIRPath expression to extract data
            default_value: Default value if data is missing
            
        Returns:
            FHIRDatasetBuilder: Self for method chaining
        """
        config = {
            "name": name,
            "resource_type": resource_type,
            "fhirpath": fhirpath,
            "default_value": default_value,
        }
        self.column_configs.append(config)
        return self
        
    def use_point_in_time_analysis(self, 
                                  reference_date: Union[str, datetime] = None,
                                  reference_column: str = None) -> "FHIRDatasetBuilder":
        """
        Enable point-in-time analysis.
        
        Args:
            reference_date: Reference date for point-in-time analysis
            reference_column: Column to use as reference date
            
        Returns:
            FHIRDatasetBuilder: Self for method chaining
        """
        self.use_point_in_time = True
        self.reference_date = reference_date
        self.reference_column = reference_column
        return self
        
    def build(self) -> FHIRDataset:
        """
        Build the dataset.
        
        Returns:
            FHIRDataset: Built dataset
        """
        # Create a FHIR-PYrate dataset
        fhir_dataset = FHIRPyrateDataset()
        
        # Add resources to the dataset
        for resource_type, resources in self.resources_by_type.items():
            fhir_dataset.add_resources(resource_type, resources)
            
        # Create resource column data configurations
        column_data = []
        for config in self.column_configs:
            column = ResourceColumnData(
                resource_type=config["resource_type"],
                column_name=config["name"],
                fhirpath=config["fhirpath"],
                default_value=config["default_value"]
            )
            column_data.append(column)
            
        # Build the dataset
        if self.use_point_in_time:
            # Perform point-in-time analysis
            pit_analysis = perform_pit_analysis(
                fhir_dataset,
                column_data,
                reference_date=self.reference_date,
                reference_date_column=self.reference_column
            )
            dataframe = generate_pit_df(pit_analysis)
        else:
            # Extract data without point-in-time analysis
            dataframe = pd.DataFrame()
            for config in self.column_configs:
                values = []
                for resource in self.resources_by_type.get(config["resource_type"], []):
                    # Use FHIR-PYrate's FHIRPath evaluation
                    result = fhir_pyrate.fhirpath_evaluate(resource, config["fhirpath"])
                    values.append(result[0] if result else config["default_value"])
                dataframe[config["name"]] = values
                
        # Set the index if needed
        if self.index_column in dataframe.columns:
            dataframe.set_index(self.index_column, inplace=True)
            
        return FHIRDataset(dataframe) 