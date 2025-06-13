"""
FHIR Dataset and Cohort Builder Module.

This module provides tools for building datasets from FHIR resources
and defining patient cohorts for data science workflows.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import pandas as pd
from pyspark.sql import DataFrame, SparkSession

# Import the FHIRPathAdapter for extracting data from FHIR resources
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

logger = logging.getLogger(__name__)


class FHIRDataset:
    """A dataset of FHIR resources.
    
    This class represents a dataset of FHIR resources, providing methods
    for filtering, transformation, and conversion to pandas DataFrames.
    """
    
    def __init__(self, data: List[Dict[str, Any]], index_by: Optional[str] = None):
        """Initialize the dataset.
        
        Args:
            data: List of dictionaries representing the dataset rows.
            index_by: Field to use as the index.
        """
        self.data = data
        self.index_by = index_by
    
    def filter(self, condition: Callable[[Dict[str, Any]], bool]) -> "FHIRDataset":
        """Filter the dataset.
        
        Args:
            condition: Function that takes a row and returns True if it should be kept.
            
        Returns:
            Filtered dataset.
        """
        filtered_data = [row for row in self.data if condition(row)]
        return FHIRDataset(filtered_data, self.index_by)
    
    def map(self, transform: Callable[[Dict[str, Any]], Dict[str, Any]]) -> "FHIRDataset":
        """Transform each row in the dataset.
        
        Args:
            transform: Function that takes a row and returns a transformed row.
            
        Returns:
            Transformed dataset.
        """
        transformed_data = [transform(row) for row in self.data]
        return FHIRDataset(transformed_data, self.index_by)
    
    def to_pandas(self) -> pd.DataFrame:
        """Convert the dataset to a pandas DataFrame.
        
        Returns:
            Pandas DataFrame.
        """
        df = pd.DataFrame(self.data)
        
        if self.index_by and self.index_by in df.columns:
            df.set_index(self.index_by, inplace=True)
            
        return df
    
    def to_spark(self, spark: SparkSession) -> DataFrame:
        """Convert the dataset to a Spark DataFrame.
        
        Args:
            spark: Spark session.
            
        Returns:
            Spark DataFrame.
        """
        return spark.createDataFrame(self.data)
    
    def __len__(self) -> int:
        """Get the number of rows in the dataset.
        
        Returns:
            Number of rows.
        """
        return len(self.data)


class FHIRDatasetBuilder:
    """Builder for creating datasets from FHIR resources.
    
    This class provides methods for adding resources, defining columns,
    and building datasets.
    """
    
    def __init__(self, adapter: Optional[FHIRPathAdapter] = None):
        """Initialize the builder.
        
        Args:
            adapter: FHIRPathAdapter instance for extracting data from resources.
        """
        self.resources = defaultdict(list)
        self.adapter = adapter or FHIRPathAdapter()
    
    def add_resources(self, resource_type: str, resources: List[Dict[str, Any]]) -> "FHIRDatasetBuilder":
        """Add resources to the builder.
        
        Args:
            resource_type: FHIR resource type.
            resources: List of FHIR resources.
            
        Returns:
            Self for chaining.
        """
        # Ensure all resources have a resourceType field
        for resource in resources:
            if "resourceType" not in resource:
                resource["resourceType"] = resource_type
                
        self.resources[resource_type].extend(resources)
        logger.info(f"Added {len(resources)} {resource_type} resources")
        
        return self
    
    def build_dataset(
        self,
        index_by: str,
        columns: List[Dict[str, Any]],
    ) -> FHIRDataset:
        """Build a dataset from the resources.
        
        Args:
            index_by: Resource type to use as the index.
            columns: List of column definitions.
                Each definition is a dict with keys:
                - resource: Resource type (defaults to index_by)
                - path: FHIRPath expression
                - name: Column name
                - code: Optional code for Observation/Condition resources
                
        Returns:
            Dataset containing the extracted data.
        """
        if index_by not in self.resources:
            raise ValueError(f"Resource type '{index_by}' not found in builder")
            
        # Get the resources to use as the index
        index_resources = self.resources[index_by]
        
        # Create a row for each index resource
        rows = []
        for resource in index_resources:
            row = {}
            
            # Process each column
            for column in columns:
                resource_type = column.get("resource", index_by)
                path = column["path"]
                name = column["name"]
                code = column.get("code")
                
                if resource_type == index_by:
                    # Extract from the index resource directly
                    row[name] = self._extract_from_resource(resource, path)
                else:
                    # Extract from related resources
                    related_resources = self._find_related_resources(resource, resource_type)
                    
                    if code:
                        # Filter by code if specified
                        related_resources = [
                            r for r in related_resources
                            if self._matches_code(r, code)
                        ]
                        
                    if len(related_resources) == 1:
                        # Single related resource
                        row[name] = self._extract_from_resource(related_resources[0], path)
                    elif len(related_resources) > 1:
                        # Multiple related resources, use a list
                        row[name] = [
                            self._extract_from_resource(r, path)
                            for r in related_resources
                        ]
                    else:
                        # No related resources
                        row[name] = None
            
            rows.append(row)
            
        return FHIRDataset(rows, None)
    
    def _extract_from_resource(self, resource: Dict[str, Any], path: str) -> Any:
        """Extract a value from a resource using FHIRPath.
        
        Args:
            resource: FHIR resource.
            path: FHIRPath expression.
            
        Returns:
            Extracted value.
        """
        try:
            return self.adapter.extract_first(resource, path)
        except Exception as e:
            logger.error(f"Error extracting path '{path}': {str(e)}")
            return None
    
    def _find_related_resources(
        self,
        resource: Dict[str, Any],
        resource_type: str,
    ) -> List[Dict[str, Any]]:
        """Find resources related to the given resource.
        
        Args:
            resource: FHIR resource.
            resource_type: Type of resources to find.
            
        Returns:
            List of related resources.
        """
        if resource_type not in self.resources:
            return []
            
        resource_id = resource.get("id")
        if not resource_id:
            return []
            
        # Find resources that reference this resource
        related = []
        for r in self.resources[resource_type]:
            # Check if the resource references the given resource
            if self._references_resource(r, resource):
                related.append(r)
                
        return related
    
    def _references_resource(self, resource: Dict[str, Any], target: Dict[str, Any]) -> bool:
        """Check if a resource references another resource.
        
        Args:
            resource: FHIR resource to check.
            target: Target resource to look for.
            
        Returns:
            True if resource references target, False otherwise.
        """
        target_id = target.get("id")
        target_type = target.get("resourceType")
        
        if not target_id or not target_type:
            return False
            
        # Check for subject reference
        subject = resource.get("subject", {})
        if isinstance(subject, dict):
            reference = subject.get("reference")
            if reference and reference.endswith(f"/{target_id}"):
                return True
                
        # Check for patient reference
        patient = resource.get("patient", {})
        if isinstance(patient, dict):
            reference = patient.get("reference")
            if reference and reference.endswith(f"/{target_id}"):
                return True
                
        return False
    
    def _matches_code(self, resource: Dict[str, Any], code: str) -> bool:
        """Check if a resource matches a code.
        
        Args:
            resource: FHIR resource to check.
            code: Code to match.
            
        Returns:
            True if resource matches code, False otherwise.
        """
        try:
            # Check for code in Observation
            if resource.get("resourceType") == "Observation":
                resource_code = self.adapter.extract_first(resource, "code.coding.where(system='http://loinc.org').code")
                return resource_code == code
                
            # Check for code in Condition
            if resource.get("resourceType") == "Condition":
                resource_code = self.adapter.extract_first(resource, "code.coding.where(system='http://snomed.info/sct').code")
                return resource_code == code
                
            return False
            
        except Exception as e:
            logger.error(f"Error matching code: {str(e)}")
            return False


class CohortBuilder:
    """Builder for defining patient cohorts.
    
    This class provides methods for defining cohorts based on clinical criteria
    such as conditions, observations, and demographics.
    """
    
    def __init__(
        self,
        patients: List[Dict[str, Any]],
        observations: Optional[List[Dict[str, Any]]] = None,
        conditions: Optional[List[Dict[str, Any]]] = None,
        adapter: Optional[FHIRPathAdapter] = None,
    ):
        """Initialize the cohort builder.
        
        Args:
            patients: List of Patient resources.
            observations: List of Observation resources.
            conditions: List of Condition resources.
            adapter: FHIRPathAdapter instance for extracting data from resources.
        """
        self.patients = patients
        self.observations = observations or []
        self.conditions = conditions or []
        self.adapter = adapter or FHIRPathAdapter()
        
        # Patient IDs included in the cohort
        self.patient_ids = set(p.get("id") for p in patients if p.get("id"))
    
    def with_condition(
        self,
        system: str,
        code: str,
    ) -> "CohortBuilder":
        """Filter the cohort to patients with a specific condition.
        
        Args:
            system: Coding system (e.g., "http://snomed.info/sct").
            code: Condition code.
            
        Returns:
            New cohort builder with the filtered cohort.
        """
        # Find patients with the condition
        condition_patient_ids = set()
        
        for condition in self.conditions:
            # Check if the condition matches the code
            condition_codes = self.adapter.extract(
                condition,
                f"code.coding.where(system='{system}').code"
            )
            
            if code in condition_codes:
                # Extract the patient ID from the subject reference
                patient_ref = self.adapter.extract_first(condition, "subject.reference")
                if patient_ref:
                    patient_id = patient_ref.split("/")[-1]
                    condition_patient_ids.add(patient_id)
        
        # Intersect with current cohort
        new_patient_ids = self.patient_ids.intersection(condition_patient_ids)
        
        # Create a new cohort builder with the filtered patients
        return self._create_filtered_cohort(new_patient_ids)
    
    def with_observation(
        self,
        system: str = "http://loinc.org",
        code: str = None,
        value_comparison: Optional[Callable[[float], bool]] = None,
    ) -> "CohortBuilder":
        """Filter the cohort to patients with a specific observation.
        
        Args:
            system: Coding system (e.g., "http://loinc.org").
            code: Observation code.
            value_comparison: Function that takes a value and returns True
                if it meets the criteria.
            
        Returns:
            New cohort builder with the filtered cohort.
        """
        # Find patients with the observation
        observation_patient_ids = set()
        
        for observation in self.observations:
            # Check if the observation matches the code
            observation_codes = self.adapter.extract(
                observation,
                f"code.coding.where(system='{system}').code"
            )
            
            if code in observation_codes:
                # Extract the value
                value = self.adapter.extract_first(observation, "valueQuantity.value")
                
                # Apply value comparison if specified
                if value_comparison and value is not None:
                    if not value_comparison(float(value)):
                        continue
                
                # Extract the patient ID from the subject reference
                patient_ref = self.adapter.extract_first(observation, "subject.reference")
                if patient_ref:
                    patient_id = patient_ref.split("/")[-1]
                    observation_patient_ids.add(patient_id)
        
        # Intersect with current cohort
        new_patient_ids = self.patient_ids.intersection(observation_patient_ids)
        
        # Create a new cohort builder with the filtered patients
        return self._create_filtered_cohort(new_patient_ids)
    
    def with_demographics(
        self,
        gender: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
    ) -> "CohortBuilder":
        """Filter the cohort based on demographics.
        
        Args:
            gender: Gender to filter by.
            min_age: Minimum age in years.
            max_age: Maximum age in years.
            
        Returns:
            New cohort builder with the filtered cohort.
        """
        # Calculate ages and filter
        demographic_patient_ids = set()
        
        for patient in self.patients:
            patient_id = patient.get("id")
            if not patient_id:
                continue
                
            # Check gender if specified
            if gender:
                patient_gender = self.adapter.extract_first(patient, "gender")
                if patient_gender != gender:
                    continue
            
            # Check age if specified
            if min_age is not None or max_age is not None:
                birth_date_str = self.adapter.extract_first(patient, "birthDate")
                if not birth_date_str:
                    continue
                    
                try:
                    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
                    age = datetime.now().year - birth_date.year
                    
                    if min_age is not None and age < min_age:
                        continue
                        
                    if max_age is not None and age > max_age:
                        continue
                        
                except ValueError:
                    continue
            
            demographic_patient_ids.add(patient_id)
        
        # Intersect with current cohort
        new_patient_ids = self.patient_ids.intersection(demographic_patient_ids)
        
        # Create a new cohort builder with the filtered patients
        return self._create_filtered_cohort(new_patient_ids)
    
    def _create_filtered_cohort(self, patient_ids: Set[str]) -> "CohortBuilder":
        """Create a new cohort builder with filtered patients.
        
        Args:
            patient_ids: Set of patient IDs to include.
            
        Returns:
            New cohort builder.
        """
        # Filter patients
        filtered_patients = [
            p for p in self.patients
            if p.get("id") in patient_ids
        ]
        
        # Create a new cohort builder
        new_builder = CohortBuilder(
            patients=filtered_patients,
            observations=self.observations,
            conditions=self.conditions,
            adapter=self.adapter,
        )
        
        # Set the patient IDs directly
        new_builder.patient_ids = patient_ids
        
        return new_builder
    
    def get_patient_ids(self) -> List[str]:
        """Get the IDs of patients in the cohort.
        
        Returns:
            List of patient IDs.
        """
        return list(self.patient_ids)
    
    def get_patients(self) -> List[Dict[str, Any]]:
        """Get the patients in the cohort.
        
        Returns:
            List of Patient resources.
        """
        return [
            p for p in self.patients
            if p.get("id") in self.patient_ids
        ]
    
    def to_dataset(self) -> FHIRDataset:
        """Convert the cohort to a dataset.
        
        Returns:
            Dataset containing the patients in the cohort.
        """
        return FHIRDataset(self.get_patients(), "id")
    
    def __len__(self) -> int:
        """Get the number of patients in the cohort.
        
        Returns:
            Number of patients.
        """
        return len(self.patient_ids) 