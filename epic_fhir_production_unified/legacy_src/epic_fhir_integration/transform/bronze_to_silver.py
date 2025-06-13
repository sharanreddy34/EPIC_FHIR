"""
Transform module for converting bronze FHIR resources to silver layer.

This module handles the transformation of FHIR resources from the bronze layer
(raw FHIR format) to the silver layer (flattened, standardized format).
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd

from epic_fhir_integration.analytics.pathling_service import PathlingService
from epic_fhir_integration.metrics.collector import MetricsCollector
from epic_fhir_integration.metrics.data_quality import (
    DataQualityAssessor,
    DataQualityDimension
)
from epic_fhir_integration.metrics.great_expectations_validator import (
    GreatExpectationsValidator,
    create_patient_expectations,
    create_observation_expectations,
    create_medication_request_expectations
)
from epic_fhir_integration.metrics.validation_metrics import (
    ValidationMetricsRecorder,
    ValidationType
)
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Added for typing in flatten_bundle and other spark helpers
from pathlib import Path

# Spark types are optional; imported lazily to avoid heavy dependency if Spark unused in runtime
try:
    from pyspark.sql import SparkSession, DataFrame
except ImportError:  # pragma: no cover
    SparkSession = Any  # type: ignore
    DataFrame = Any  # type: ignore

logger = logging.getLogger(__name__)

class BronzeToSilverTransformer:
    """Transformer for bronze to silver layer conversion."""
    
    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        pathling_service: Optional[PathlingService] = None,
        expectation_suite_dir: Optional[str] = None
    ):
        """Initialize the transformer.
        
        Args:
            metrics_collector: Optional metrics collector for recording metrics
            pathling_service: Optional Pathling service for complex transformations
            expectation_suite_dir: Optional directory containing expectation suites
        """
        self.metrics_collector = metrics_collector
        self.pathling_service = pathling_service
        
        # Initialize FHIRPath adapter
        self.fhirpath = FHIRPathAdapter()
        
        # Initialize data quality tools
        self.data_quality_assessor = DataQualityAssessor(metrics_collector)
        
        # Initialize validation tools
        self.validation_metrics_recorder = ValidationMetricsRecorder(metrics_collector)
        
        # Initialize Great Expectations validator
        self.ge_validator = GreatExpectationsValidator(
            validation_metrics_recorder=self.validation_metrics_recorder,
            expectation_suite_dir=expectation_suite_dir
        )
        
        # Ensure expectation suites exist
        self._ensure_expectation_suites()
        
        # Track performance metrics
        self.performance_metrics = {
            "fhirpath_operations": 0,
            "fhirpath_time": 0,
            "pathling_operations": 0,
            "pathling_time": 0
        }
    
    def transform_resource(
        self,
        resource: Dict[str, Any],
        resource_type: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Transform a single FHIR resource to silver format.
        
        Args:
            resource: FHIR resource as a dictionary
            resource_type: Optional resource type to override the one in the resource
            validate: Whether to validate the resource before transformation
            
        Returns:
            Transformed resource in silver format
        """
        # Extract resource type if not provided
        if not resource_type:
            resource_type = resource.get("resourceType")
            
        if not resource_type:
            logger.warning("Resource missing resourceType")
            return {}
        
        # Record start time for metrics
        start_time = time.time()
        
        # Validate resource if requested
        if validate:
            self._validate_resource(resource, resource_type)
        
        # Transform based on resource type
        if resource_type == "Patient":
            transformed = self._transform_patient(resource)
        elif resource_type == "Observation":
            transformed = self._transform_observation(resource)
        elif resource_type == "MedicationRequest":
            transformed = self._transform_medication_request(resource)
        elif resource_type == "Condition":
            transformed = self._transform_condition(resource)
        elif resource_type == "Encounter":
            transformed = self._transform_encounter(resource)
        else:
            # Default transformation for other resource types
            transformed = self._transform_generic(resource)
        
        # Add metadata
        transformed["_source"] = {
            "resourceType": resource_type,
            "id": resource.get("id", "unknown"),
            "transformedAt": datetime.utcnow().isoformat()
        }
        
        # Record metrics
        if self.metrics_collector:
            self.metrics_collector.record_metric(
                f"transform.{resource_type}.time",
                time.time() - start_time,
                {"resource_type": resource_type}
            )
        
        return transformed
    
    def transform_resources(
        self,
        resources: List[Dict[str, Any]],
        validate: bool = True,
        use_pathling: bool = False
    ) -> List[Dict[str, Any]]:
        """Transform multiple FHIR resources to silver format.
        
        Args:
            resources: List of FHIR resources as dictionaries
            validate: Whether to validate resources before transformation
            use_pathling: Whether to use Pathling for transformation
            
        Returns:
            List of transformed resources in silver format
        """
        if not resources:
            return []
        
        # Record start time for metrics
        start_time = time.time()
        
        # Group resources by type
        resource_groups = {}
        for resource in resources:
            resource_type = resource.get("resourceType")
            if not resource_type:
                logger.warning("Resource missing resourceType, skipping")
                continue
                
            if resource_type not in resource_groups:
                resource_groups[resource_type] = []
                
            resource_groups[resource_type].append(resource)
        
        # Validate resources by type if requested
        if validate:
            for resource_type, group in resource_groups.items():
                self._validate_resources(group, resource_type)
        
        # Transform using Pathling if requested
        if use_pathling and self.pathling_service:
            transformed = self._transform_with_pathling(resources)
        else:
            # Transform one by one
            transformed = []
            for resource in resources:
                transformed.append(self.transform_resource(resource, validate=False))
        
        # Record metrics
        if self.metrics_collector:
            self.metrics_collector.record_metric(
                "transform.batch.time",
                time.time() - start_time,
                {"resource_count": len(resources)}
            )
            
            # Record performance metrics
            for metric_name, value in self.performance_metrics.items():
                self.metrics_collector.record_metric(
                    f"transform.performance.{metric_name}",
                    value,
                    {"batch_size": len(resources)}
                )
        
        return transformed
    
    def _transform_patient(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a Patient resource to silver format.
        
        Args:
            resource: Patient resource as a dictionary
            
        Returns:
            Transformed Patient resource
        """
        # Extract key fields using FHIRPath
        start_time = time.time()
        
        patient_id = self.fhirpath.extract_first(resource, "id")
        family_name = self.fhirpath.extract_first(resource, "name.where(use='official').family")
        if not family_name:
            family_name = self.fhirpath.extract_first(resource, "name.family")
            
        given_names = self.fhirpath.extract(resource, "name.where(use='official').given")
        if not given_names:
            given_names = self.fhirpath.extract(resource, "name.given")
            
        gender = self.fhirpath.extract_first(resource, "gender")
        birth_date = self.fhirpath.extract_first(resource, "birthDate")
        
        # Extract address
        address = self.fhirpath.extract_first(resource, "address.where(use='home')")
        if not address:
            address = self.fhirpath.extract_first(resource, "address")
            
        street = self.fhirpath.extract(address, "line") if address else []
        city = self.fhirpath.extract_first(address, "city") if address else None
        state = self.fhirpath.extract_first(address, "state") if address else None
        postal_code = self.fhirpath.extract_first(address, "postalCode") if address else None
        
        # Extract contact info
        email = self.fhirpath.extract_first(resource, "telecom.where(system='email').value")
        phone = self.fhirpath.extract_first(resource, "telecom.where(system='phone').value")
        
        # Extract identifiers
        mrn = self.fhirpath.extract_first(
            resource, 
            "identifier.where(system.contains('MRN')).value"
        )
        
        # Update performance metrics
        self.performance_metrics["fhirpath_operations"] += 10  # Approximate count
        self.performance_metrics["fhirpath_time"] += time.time() - start_time
        
        # Create silver format
        return {
            "id": patient_id,
            "name": {
                "family": family_name,
                "given": given_names[0] if given_names else None,
                "middle": given_names[1] if len(given_names) > 1 else None,
                "full": f"{given_names[0] if given_names else ''} {family_name}"
            },
            "gender": gender,
            "birthDate": birth_date,
            "address": {
                "street": street[0] if street else None,
                "city": city,
                "state": state,
                "postalCode": postal_code
            },
            "contact": {
                "email": email,
                "phone": phone
            },
            "identifiers": {
                "mrn": mrn
            },
            "resourceType": "Patient"
        }
    
    def _transform_observation(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Transform an Observation resource to silver format.
        
        Args:
            resource: Observation resource as a dictionary
            
        Returns:
            Transformed Observation resource
        """
        # Extract key fields using FHIRPath
        start_time = time.time()
        
        observation_id = self.fhirpath.extract_first(resource, "id")
        status = self.fhirpath.extract_first(resource, "status")
        
        # Extract codes
        coding = self.fhirpath.extract(resource, "code.coding")
        code = self.fhirpath.extract_first(coding, "$this.code") if coding else None
        system = self.fhirpath.extract_first(coding, "$this.system") if coding else None
        display = self.fhirpath.extract_first(coding, "$this.display") if coding else None
        
        # Extract values
        value_quantity = self.fhirpath.extract_first(resource, "valueQuantity")
        value_string = self.fhirpath.extract_first(resource, "valueString")
        value_codeable_concept = self.fhirpath.extract_first(resource, "valueCodeableConcept")
        
        # Determine value type and extract accordingly
        value = None
        value_unit = None
        value_type = None
        
        if value_quantity:
            value_type = "Quantity"
            value = self.fhirpath.extract_first(value_quantity, "value")
            value_unit = self.fhirpath.extract_first(value_quantity, "unit")
        elif value_string:
            value_type = "String"
            value = value_string
        elif value_codeable_concept:
            value_type = "CodeableConcept"
            value_codings = self.fhirpath.extract(value_codeable_concept, "coding")
            if value_codings:
                value = self.fhirpath.extract_first(value_codings, "$this.code")
                value_unit = self.fhirpath.extract_first(value_codings, "$this.display")
        
        # Extract subject reference
        subject_reference = self.fhirpath.extract_first(resource, "subject.reference")
        
        # Extract dates
        effective_date_time = self.fhirpath.extract_first(resource, "effectiveDateTime")
        issued = self.fhirpath.extract_first(resource, "issued")
        
        # Update performance metrics
        self.performance_metrics["fhirpath_operations"] += 15  # Approximate count
        self.performance_metrics["fhirpath_time"] += time.time() - start_time
        
        # Create silver format
        return {
            "id": observation_id,
            "status": status,
            "code": {
                "code": code,
                "system": system,
                "display": display
            },
            "value": {
                "type": value_type,
                "value": value,
                "unit": value_unit
            },
            "subject": self._extract_reference_id(subject_reference),
            "effective": effective_date_time,
            "issued": issued,
            "resourceType": "Observation"
        }
    
    def _transform_medication_request(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a MedicationRequest resource to silver format.
        
        Args:
            resource: MedicationRequest resource as a dictionary
            
        Returns:
            Transformed MedicationRequest resource
        """
        # Extract key fields using FHIRPath
        start_time = time.time()
        
        request_id = self.fhirpath.extract_first(resource, "id")
        status = self.fhirpath.extract_first(resource, "status")
        intent = self.fhirpath.extract_first(resource, "intent")
        
        # Extract medication
        medication_reference = self.fhirpath.extract_first(resource, "medicationReference.reference")
        medication_codeable_concept = self.fhirpath.extract_first(resource, "medicationCodeableConcept")
        
        medication_code = None
        medication_display = None
        medication_id = None
        
        if medication_codeable_concept:
            coding = self.fhirpath.extract_first(medication_codeable_concept, "coding")
            if coding:
                medication_code = self.fhirpath.extract_first(coding, "code")
                medication_display = self.fhirpath.extract_first(coding, "display")
        elif medication_reference:
            medication_id = self._extract_reference_id(medication_reference)
        
        # Extract subject reference
        subject_reference = self.fhirpath.extract_first(resource, "subject.reference")
        
        # Extract encounter reference
        encounter_reference = self.fhirpath.extract_first(resource, "encounter.reference")
        
        # Extract authored date
        authored_on = self.fhirpath.extract_first(resource, "authoredOn")
        
        # Extract dosage instructions
        dosage_instructions = self.fhirpath.extract(resource, "dosageInstruction")
        
        dosage_text = None
        dosage_quantity = None
        dosage_unit = None
        dosage_frequency = None
        
        if dosage_instructions:
            first_dosage = dosage_instructions[0] if dosage_instructions else None
            if first_dosage:
                dosage_text = self.fhirpath.extract_first(first_dosage, "text")
                
                dose_quantity = self.fhirpath.extract_first(first_dosage, "doseAndRate.doseQuantity")
                if dose_quantity:
                    dosage_quantity = self.fhirpath.extract_first(dose_quantity, "value")
                    dosage_unit = self.fhirpath.extract_first(dose_quantity, "unit")
                
                timing = self.fhirpath.extract_first(first_dosage, "timing")
                if timing:
                    frequency = self.fhirpath.extract_first(timing, "repeat.frequency")
                    period = self.fhirpath.extract_first(timing, "repeat.period")
                    period_unit = self.fhirpath.extract_first(timing, "repeat.periodUnit")
                    
                    if frequency and period and period_unit:
                        dosage_frequency = f"{frequency} times per {period} {period_unit}"
        
        # Update performance metrics
        self.performance_metrics["fhirpath_operations"] += 20  # Approximate count
        self.performance_metrics["fhirpath_time"] += time.time() - start_time
        
        # Create silver format
        return {
            "id": request_id,
            "status": status,
            "intent": intent,
            "medication": {
                "id": medication_id,
                "code": medication_code,
                "display": medication_display
            },
            "subject": self._extract_reference_id(subject_reference),
            "encounter": self._extract_reference_id(encounter_reference),
            "authoredOn": authored_on,
            "dosage": {
                "text": dosage_text,
                "quantity": dosage_quantity,
                "unit": dosage_unit,
                "frequency": dosage_frequency
            },
            "resourceType": "MedicationRequest"
        }
    
    def _transform_condition(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a Condition resource to silver format.
        
        Args:
            resource: Condition resource as a dictionary
            
        Returns:
            Transformed Condition resource
        """
        # Extract key fields using FHIRPath
        start_time = time.time()
        
        condition_id = self.fhirpath.extract_first(resource, "id")
        
        # Extract clinical status
        clinical_status = self.fhirpath.extract_first(resource, "clinicalStatus.coding.code")
        
        # Extract verification status
        verification_status = self.fhirpath.extract_first(resource, "verificationStatus.coding.code")
        
        # Extract category
        category_codings = self.fhirpath.extract(resource, "category.coding")
        categories = []
        
        if category_codings:
            for coding in category_codings:
                code = self.fhirpath.extract_first(coding, "code")
                system = self.fhirpath.extract_first(coding, "system")
                display = self.fhirpath.extract_first(coding, "display")
                
                if code:
                    categories.append({
                        "code": code,
                        "system": system,
                        "display": display
                    })
        
        # Extract code
        code_codings = self.fhirpath.extract(resource, "code.coding")
        code = None
        system = None
        display = None
        
        if code_codings:
            code = self.fhirpath.extract_first(code_codings[0], "code")
            system = self.fhirpath.extract_first(code_codings[0], "system")
            display = self.fhirpath.extract_first(code_codings[0], "display")
        
        # Extract subject reference
        subject_reference = self.fhirpath.extract_first(resource, "subject.reference")
        
        # Extract encounter reference
        encounter_reference = self.fhirpath.extract_first(resource, "encounter.reference")
        
        # Extract onset date
        onset_date_time = self.fhirpath.extract_first(resource, "onsetDateTime")
        
        # Extract recorded date
        recorded_date = self.fhirpath.extract_first(resource, "recordedDate")
        
        # Update performance metrics
        self.performance_metrics["fhirpath_operations"] += 15  # Approximate count
        self.performance_metrics["fhirpath_time"] += time.time() - start_time
        
        # Create silver format
        return {
            "id": condition_id,
            "clinicalStatus": clinical_status,
            "verificationStatus": verification_status,
            "categories": categories,
            "code": {
                "code": code,
                "system": system,
                "display": display
            },
            "subject": self._extract_reference_id(subject_reference),
            "encounter": self._extract_reference_id(encounter_reference),
            "onsetDateTime": onset_date_time,
            "recordedDate": recorded_date,
            "resourceType": "Condition"
        }
    
    def _transform_encounter(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Transform an Encounter resource to silver format.
        
        Args:
            resource: Encounter resource as a dictionary
            
        Returns:
            Transformed Encounter resource
        """
        # Extract key fields using FHIRPath
        start_time = time.time()
        
        encounter_id = self.fhirpath.extract_first(resource, "id")
        status = self.fhirpath.extract_first(resource, "status")
        
        # Extract class
        class_code = self.fhirpath.extract_first(resource, "class.code")
        class_display = self.fhirpath.extract_first(resource, "class.display")
        
        # Extract type
        type_codings = self.fhirpath.extract(resource, "type.coding")
        type_code = None
        type_system = None
        type_display = None
        
        if type_codings:
            type_code = self.fhirpath.extract_first(type_codings[0], "code")
            type_system = self.fhirpath.extract_first(type_codings[0], "system")
            type_display = self.fhirpath.extract_first(type_codings[0], "display")
        
        # Extract subject reference
        subject_reference = self.fhirpath.extract_first(resource, "subject.reference")
        
        # Extract participant references
        participants = self.fhirpath.extract(resource, "participant")
        participant_references = []
        
        if participants:
            for participant in participants:
                reference = self.fhirpath.extract_first(participant, "individual.reference")
                type_codings = self.fhirpath.extract(participant, "type.coding")
                
                participant_type = None
                if type_codings:
                    participant_type = self.fhirpath.extract_first(type_codings[0], "code")
                
                if reference:
                    participant_references.append({
                        "reference": self._extract_reference_id(reference),
                        "type": participant_type
                    })
        
        # Extract period
        period = self.fhirpath.extract_first(resource, "period")
        period_start = None
        period_end = None
        
        if period:
            period_start = self.fhirpath.extract_first(period, "start")
            period_end = self.fhirpath.extract_first(period, "end")
        
        # Extract service provider
        service_provider_reference = self.fhirpath.extract_first(resource, "serviceProvider.reference")
        
        # Update performance metrics
        self.performance_metrics["fhirpath_operations"] += 15  # Approximate count
        self.performance_metrics["fhirpath_time"] += time.time() - start_time
        
        # Create silver format
        return {
            "id": encounter_id,
            "status": status,
            "class": {
                "code": class_code,
                "display": class_display
            },
            "type": {
                "code": type_code,
                "system": type_system,
                "display": type_display
            },
            "subject": self._extract_reference_id(subject_reference),
            "participants": participant_references,
            "period": {
                "start": period_start,
                "end": period_end
            },
            "serviceProvider": self._extract_reference_id(service_provider_reference),
            "resourceType": "Encounter"
        }
    
    def _transform_generic(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a generic FHIR resource to silver format.
        
        Args:
            resource: FHIR resource as a dictionary
            
        Returns:
            Transformed resource
        """
        # Extract basic fields
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")
        
        # Extract metadata
        meta = resource.get("meta", {})
        last_updated = meta.get("lastUpdated")
        
        # Create a simplified representation
        transformed = {
            "id": resource_id,
            "resourceType": resource_type,
            "lastUpdated": last_updated
        }
        
        # Copy other top-level fields
        for key, value in resource.items():
            if key not in ["resourceType", "id", "meta"] and not isinstance(value, (dict, list)):
                transformed[key] = value
        
        return transformed
    
    def _transform_with_pathling(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform resources using Pathling.
        
        Args:
            resources: List of FHIR resources to transform
            
        Returns:
            List of transformed resources
        """
        if not self.pathling_service:
            logger.warning("Pathling service not available")
            return [self.transform_resource(r, validate=False) for r in resources]
        
        # Record start time for metrics
        start_time = time.time()
        
        try:
            # Import resources into Pathling
            self.pathling_service.import_resources(resources)
            
            # Group resources by type
            resource_types = set(r.get("resourceType") for r in resources if r.get("resourceType"))
            
            # Extract datasets for each resource type
            transformed_resources = []
            
            for resource_type in resource_types:
                # Define extraction columns based on resource type
                columns = self._get_pathling_columns(resource_type)
                
                # Extract dataset
                dataset = self.pathling_service.extract_dataset(
                    subject=resource_type,
                    columns=columns
                )
                
                # Convert each dataset row to a transformed resource
                for _, row in dataset.iterrows():
                    transformed = {col: row[col] for col in dataset.columns if not pd.isna(row[col])}
                    transformed["resourceType"] = resource_type
                    transformed_resources.append(transformed)
            
            # Update performance metrics
            self.performance_metrics["pathling_operations"] += len(resource_types)
            self.performance_metrics["pathling_time"] += time.time() - start_time
            
            return transformed_resources
        except Exception as e:
            logger.error(f"Error transforming with Pathling: {str(e)}")
            logger.warning("Falling back to standard transformation")
            return [self.transform_resource(r, validate=False) for r in resources]
    
    def _get_pathling_columns(self, resource_type: str) -> List[Dict[str, str]]:
        """Get Pathling extraction columns for a resource type.
        
        Args:
            resource_type: FHIR resource type
            
        Returns:
            List of column specifications for Pathling extraction
        """
        if resource_type == "Patient":
            return [
                {"path": "id", "alias": "id"},
                {"path": "name.where(use='official').family", "alias": "family"},
                {"path": "name.where(use='official').given", "alias": "given"},
                {"path": "gender", "alias": "gender"},
                {"path": "birthDate", "alias": "birthDate"},
                {"path": "address.where(use='home').line", "alias": "street"},
                {"path": "address.where(use='home').city", "alias": "city"},
                {"path": "address.where(use='home').state", "alias": "state"},
                {"path": "address.where(use='home').postalCode", "alias": "postalCode"},
                {"path": "telecom.where(system='email').value", "alias": "email"},
                {"path": "telecom.where(system='phone').value", "alias": "phone"}
            ]
        elif resource_type == "Observation":
            return [
                {"path": "id", "alias": "id"},
                {"path": "status", "alias": "status"},
                {"path": "code.coding.code", "alias": "code"},
                {"path": "code.coding.system", "alias": "system"},
                {"path": "code.coding.display", "alias": "display"},
                {"path": "valueQuantity.value", "alias": "value"},
                {"path": "valueQuantity.unit", "alias": "unit"},
                {"path": "subject.reference", "alias": "subject"},
                {"path": "effectiveDateTime", "alias": "effective"},
                {"path": "issued", "alias": "issued"}
            ]
        elif resource_type == "MedicationRequest":
            return [
                {"path": "id", "alias": "id"},
                {"path": "status", "alias": "status"},
                {"path": "intent", "alias": "intent"},
                {"path": "medicationCodeableConcept.coding.code", "alias": "medicationCode"},
                {"path": "medicationCodeableConcept.coding.display", "alias": "medicationDisplay"},
                {"path": "subject.reference", "alias": "subject"},
                {"path": "authoredOn", "alias": "authoredOn"},
                {"path": "dosageInstruction.text", "alias": "dosageText"}
            ]
        else:
            # Generic columns for any resource type
            return [
                {"path": "id", "alias": "id"},
                {"path": "meta.lastUpdated", "alias": "lastUpdated"}
            ]
    
    def _extract_reference_id(self, reference: Optional[str]) -> Optional[str]:
        """Extract the ID part from a FHIR reference.
        
        Args:
            reference: FHIR reference string (e.g., "Patient/123")
            
        Returns:
            ID part of the reference or None
        """
        if not reference:
            return None
            
        # Handle absolute URLs
        if reference.startswith(("http://", "https://")):
            # Extract the path part
            path = reference.split("/")[-1]
            return path
            
        # Handle relative references (e.g., "Patient/123")
        parts = reference.split("/")
        if len(parts) == 2:
            return parts[1]
            
        return reference
    
    def _ensure_expectation_suites(self) -> None:
        """Ensure that expectation suites exist for common resource types."""
        # Create patient expectations if needed
        if not self.ge_validator.get_expectation_suite("patient"):
            create_patient_expectations(self.ge_validator, "patient")
            self.ge_validator.save_expectation_suite("patient")
            
        # Create observation expectations if needed
        if not self.ge_validator.get_expectation_suite("observation"):
            create_observation_expectations(self.ge_validator, "observation")
            self.ge_validator.save_expectation_suite("observation")
            
        # Create medication request expectations if needed
        if not self.ge_validator.get_expectation_suite("medication_request"):
            create_medication_request_expectations(self.ge_validator, "medication_request")
            self.ge_validator.save_expectation_suite("medication_request")
    
    def _validate_resource(self, resource: Dict[str, Any], resource_type: str) -> bool:
        """Validate a single FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary
            resource_type: Resource type
            
        Returns:
            True if valid, False otherwise
        """
        # Skip validation if resource type is unknown
        if not resource_type:
            return False
            
        # Determine which expectation suite to use
        suite_name = resource_type.lower()
        if resource_type == "MedicationRequest":
            suite_name = "medication_request"
            
        # Validate using Great Expectations
        result = self.ge_validator.validate_resource(
            resource=resource,
            expectation_suite_name=suite_name,
            pipeline_stage="bronze"
        )
        
        # Assess data quality
        quality_result = self._assess_resource_quality(resource, resource_type)
        
        # Return overall validity
        return result.get("is_valid", False) and quality_result.get("overall_quality_score", 0) > 0.7
    
    def _validate_resources(self, resources: List[Dict[str, Any]], resource_type: str) -> bool:
        """Validate multiple FHIR resources of the same type.
        
        Args:
            resources: List of FHIR resources as dictionaries
            resource_type: Resource type
            
        Returns:
            True if all are valid, False otherwise
        """
        # Skip validation if resource type is unknown
        if not resource_type:
            return False
            
        # Determine which expectation suite to use
        suite_name = resource_type.lower()
        if resource_type == "MedicationRequest":
            suite_name = "medication_request"
            
        # Validate using Great Expectations
        result = self.ge_validator.validate_resources(
            resources=resources,
            expectation_suite_name=suite_name,
            pipeline_stage="bronze"
        )
        
        # Assess data quality for the batch
        quality_results = [
            self._assess_resource_quality(resource, resource_type)
            for resource in resources
        ]
        
        # Calculate average quality score
        quality_scores = [r.get("overall_quality_score", 0) for r in quality_results]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Return overall validity
        return result.get("validation_rate", 0) > 0.7 and avg_quality_score > 0.7
    
    def _assess_resource_quality(self, resource: Dict[str, Any], resource_type: str) -> Dict[str, Any]:
        """Assess the quality of a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary
            resource_type: Resource type
            
        Returns:
            Dictionary with quality assessment results
        """
        # Define required paths based on resource type
        required_paths = []
        consistency_rules = []
        
        if resource_type == "Patient":
            required_paths = [
                "id",
                "name.where(use='official').family",
                "gender",
                "birthDate"
            ]
            
            consistency_rules = [
                {
                    "name": "Gender is valid",
                    "condition": "gender.exists() implies gender.matches('male|female|other|unknown')"
                },
                {
                    "name": "Name has family",
                    "condition": "name.exists() implies name.family.exists()"
                }
            ]
        elif resource_type == "Observation":
            required_paths = [
                "id",
                "status",
                "code",
                "subject"
            ]
            
            consistency_rules = [
                {
                    "name": "Status is valid",
                    "condition": "status.exists() implies status.matches('registered|preliminary|final|amended|corrected|cancelled|entered-in-error|unknown')"
                },
                {
                    "name": "Code has coding",
                    "condition": "code.exists() implies code.coding.exists()"
                }
            ]
        elif resource_type == "MedicationRequest":
            required_paths = [
                "id",
                "status",
                "intent",
                "subject"
            ]
            
            consistency_rules = [
                {
                    "name": "Status is valid",
                    "condition": "status.exists() implies status.matches('active|on-hold|cancelled|completed|entered-in-error|stopped|draft|unknown')"
                },
                {
                    "name": "Intent is valid",
                    "condition": "intent.exists() implies intent.matches('proposal|plan|order|original-order|reflex-order|filler-order|instance-order|option')"
                }
            ]
        
        # Assess overall quality
        result = self.data_quality_assessor.assess_overall_quality(
            resource=resource,
            required_paths=required_paths,
            consistency_rules=consistency_rules
        )
        
        return result


def flatten_bundle(path: Union[str, Path], spark: SparkSession) -> DataFrame:
    """Flatten a FHIR bundle into a Spark DataFrame.
    
    Args:
        path: Path to the FHIR bundle JSON file.
        spark: Spark session.
        
    Returns:
        Spark DataFrame with flattened FHIR resources.
    """
    if isinstance(path, str):
        path = Path(path)
    
    logger.info(f"Flattening FHIR bundle: {path}")
    
    # Read the JSON file
    with open(path, "r") as f:
        bundle_data = json.load(f)
    
    # Parse the bundle using FHIR resources model
    try:
        bundle = Bundle.model_validate(bundle_data)
    except Exception as e:
        logger.warning(f"Failed to parse bundle as FHIR Bundle model: {e}")
        # Fall back to dictionary approach
        resources = []
        for entry in bundle_data.get("entry", []):
            if "resource" in entry:
                resources.append(entry["resource"])
    else:
        # Use the parsed Bundle model
        resources = []
        if bundle.entry:
            for entry in bundle.entry:
                if entry.resource:
                    # Convert the resource model to a dictionary
                    resources.append(resource_model_to_dict(entry.resource))
    
    if not resources:
        logger.warning(f"No resources found in bundle: {path}")
        # Return an empty DataFrame with some common FHIR columns
        return spark.createDataFrame(
            [], 
            "resourceType STRING, id STRING, meta STRUCT<versionId: STRING, lastUpdated: STRING>"
        )
    
    # Create a DataFrame from the resources
    df = spark.read.json(
        spark.sparkContext.parallelize([json.dumps(resource) for resource in resources])
    )
    
    logger.info(f"Flattened {len(resources)} resources from {path}")
    return df


def transform_bronze_to_silver(
    resource_type: str, 
    bronze_path: Union[str, Path],
    silver_path: Union[str, Path],
    spark: SparkSession,
) -> Path:
    """Transform a bronze FHIR resource bundle into a silver Parquet file.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation").
        bronze_path: Path to the bronze JSON file or directory.
        silver_path: Base path for the silver output.
        spark: Spark session.
        
    Returns:
        Path to the silver output directory.
    """
    if isinstance(bronze_path, str):
        bronze_path = Path(bronze_path)
    
    if isinstance(silver_path, str):
        silver_path = Path(silver_path)
    
    # Determine bronze input path(s)
    bronze_files = []
    if bronze_path.is_dir():
        # If a directory is provided, look for files matching the resource type
        pattern = f"{resource_type.lower()}_*.json"
        bronze_files = list(bronze_path.glob(pattern))
        if not bronze_files:
            raise ValueError(f"No bronze files found for {resource_type} in {bronze_path}")
    else:
        # If a single file is provided
        bronze_files = [bronze_path]
    
    # Create output directory
    output_dir = silver_path / resource_type.lower()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each bronze file
    dfs = []
    for bronze_file in bronze_files:
        df = flatten_bundle(bronze_file, spark)
        dfs.append(df)
    
    # Union all DataFrames if there are multiple
    if len(dfs) > 1:
        result_df = dfs[0]
        for df in dfs[1:]:
            result_df = result_df.unionByName(df, allowMissingColumns=True)
    else:
        result_df = dfs[0]
    
    # Write to Parquet
    logger.info(f"Writing {resource_type} silver layer to {output_dir}")
    result_df.write.mode("overwrite").parquet(str(output_dir))
    
    return output_dir


def transform_all_bronze_to_silver(
    resource_types: List[str],
    bronze_base_path: Union[str, Path],
    silver_base_path: Union[str, Path],
    spark: Optional[SparkSession] = None,
) -> Dict[str, Path]:
    """Transform multiple resource types from bronze to silver.
    
    Args:
        resource_types: List of FHIR resource types to transform.
        bronze_base_path: Base path for bronze input.
        silver_base_path: Base path for silver output.
        spark: Optional Spark session. If not provided, a new one will be created.
        
    Returns:
        Dictionary mapping resource types to silver output paths.
    """
    if isinstance(bronze_base_path, str):
        bronze_base_path = Path(bronze_base_path)
    
    if isinstance(silver_base_path, str):
        silver_base_path = Path(silver_base_path)
    
    # Create Spark session if not provided
    if spark is None:
        spark = SparkSession.builder \
            .appName("FHIR Bronze to Silver") \
            .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
            .getOrCreate()
    
    # Transform each resource type
    output_paths = {}
    for resource_type in resource_types:
        bronze_path = bronze_base_path / "bronze" / resource_type.lower()
        
        try:
            output_path = transform_bronze_to_silver(
                resource_type, bronze_path, silver_base_path, spark
            )
            output_paths[resource_type] = output_path
        except Exception as e:
            logger.error(f"Error transforming {resource_type} from bronze to silver: {e}")
            # Continue with the next resource type
    
    return output_paths


def main():
    """Main entry point for bronze to silver transformation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform FHIR bronze to silver")
    parser.add_argument(
        "--resources", nargs="+", help="FHIR resource types to transform"
    )
    parser.add_argument(
        "--bronze-dir", help="Base directory for bronze input", default="output"
    )
    parser.add_argument(
        "--silver-dir", help="Base directory for silver output", default="output"
    )
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("FHIR Bronze to Silver") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()
    
    # Default resource types if not specified
    resource_types = args.resources or ["Patient", "Observation", "Encounter"]
    
    # Transform resources
    output_paths = transform_all_bronze_to_silver(
        resource_types, args.bronze_dir, args.silver_dir, spark
    )
    
    for resource_type, path in output_paths.items():
        logger.info(f"Transformed {resource_type} to silver: {path}")


if __name__ == "__main__":
    main() 