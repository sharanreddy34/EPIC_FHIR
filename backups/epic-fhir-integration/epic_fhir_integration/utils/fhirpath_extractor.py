"""
FHIRPath utilities for extracting data from FHIR resources.

This module provides utilities for using FHIRPath expressions to extract
data from FHIR resources, particularly for complex nested structures.
"""

import logging
from typing import Any, Dict, List, Optional, Union

try:
    # Try to import the new adapter first
    from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
    USE_NEW_ADAPTER = True
except ImportError:
    # Fall back to fhirpathpy if adapter not available
    import fhirpathpy
    USE_NEW_ADAPTER = False

logger = logging.getLogger(__name__)

class FHIRPathExtractor:
    """Extract data from FHIR resources using FHIRPath expressions."""
    
    @staticmethod
    def extract(resource: Any, path: str) -> List[Any]:
        """
        Extract data from a FHIR resource using a FHIRPath expression.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            List of values matching the FHIRPath expression
        """
        try:
            # Convert FHIR resource model to dictionary if needed
            if hasattr(resource, "model_dump"):
                resource_dict = resource.model_dump()
            elif hasattr(resource, "dict"):
                resource_dict = resource.dict()
            else:
                resource_dict = resource
                
            # Use the new adapter if available, otherwise use fhirpathpy directly
            if USE_NEW_ADAPTER:
                return FHIRPathAdapter.extract(resource_dict, path)
            else:
                # Evaluate the FHIRPath expression with fhirpathpy
                result = fhirpathpy.evaluate(resource_dict, path)
                return result
            
        except Exception as e:
            logger.error(f"Error evaluating FHIRPath '{path}': {e}")
            return []
    
    @staticmethod
    def extract_first(resource: Any, path: str, default: Any = None) -> Any:
        """
        Extract the first matching value from a FHIR resource using a FHIRPath expression.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            default: Default value to return if no matches are found
            
        Returns:
            First value matching the FHIRPath expression, or default if none
        """
        if USE_NEW_ADAPTER:
            return FHIRPathAdapter.extract_first(resource, path, default)
        else:
            results = FHIRPathExtractor.extract(resource, path)
            if results and len(results) > 0:
                return results[0]
            return default
    
    @staticmethod
    def exists(resource: Any, path: str) -> bool:
        """
        Check if a FHIRPath expression has any matches in a FHIR resource.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            True if the expression has matches, False otherwise
        """
        if USE_NEW_ADAPTER:
            return FHIRPathAdapter.exists(resource, path)
        else:
            results = FHIRPathExtractor.extract(resource, path)
            return bool(results)
    
    @classmethod
    def extract_with_paths(cls, resource: Any, paths: List[str], default: Any = None) -> Any:
        """
        Try multiple FHIRPath expressions in order until one returns a value.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            paths: List of FHIRPath expressions to try
            default: Default value to return if no matches are found
            
        Returns:
            First value from the first path that has matches, or default if none
        """
        if USE_NEW_ADAPTER:
            return FHIRPathAdapter.extract_with_paths(resource, paths, default)
        else:
            for path in paths:
                value = cls.extract_first(resource, path)
                if value is not None:
                    return value
            return default


# Common FHIRPath expressions for FHIR resources
COMMON_FHIRPATH_EXPRESSIONS = {
    "Patient": {
        "id": "Patient.id",
        "active": "Patient.active",
        "gender": "Patient.gender",
        "birthDate": "Patient.birthDate",
        "deceased": "Patient.deceasedBoolean | Patient.deceasedDateTime",
        "maritalStatus": "Patient.maritalStatus.coding.where(system = 'http://terminology.hl7.org/CodeSystem/v3-MaritalStatus').code",
        "familyName": "Patient.name.where(use = 'official').family | Patient.name.family",
        "givenNames": "Patient.name.where(use = 'official').given | Patient.name.given",
        "telecom": {
            "phone": "Patient.telecom.where(system = 'phone' and use = 'home').value | Patient.telecom.where(system = 'phone').value",
            "email": "Patient.telecom.where(system = 'email').value",
            "mobile": "Patient.telecom.where(system = 'phone' and use = 'mobile').value",
        },
        "address": {
            "line": "Patient.address.where(use = 'home').line | Patient.address.line",
            "city": "Patient.address.where(use = 'home').city | Patient.address.city",
            "state": "Patient.address.where(use = 'home').state | Patient.address.state",
            "postalCode": "Patient.address.where(use = 'home').postalCode | Patient.address.postalCode",
            "country": "Patient.address.where(use = 'home').country | Patient.address.country",
        },
        "language": "Patient.communication.where(preferred = true).language.coding.code | Patient.communication.language.coding.code",
        "identifiers": {
            "mrn": "Patient.identifier.where(type.coding.code = 'MR').value",
            "ssn": "Patient.identifier.where(system = 'http://hl7.org/fhir/sid/us-ssn').value",
        },
        # US Core race and ethnicity
        "race": "Patient.extension.where(url = 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url = 'text').valueString",
        "ethnicity": "Patient.extension.where(url = 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity').extension.where(url = 'text').valueString",
    },
    "Observation": {
        "id": "Observation.id",
        "status": "Observation.status",
        "category": "Observation.category.coding.code",
        "code": "Observation.code.coding.code",
        "codeDisplay": "Observation.code.coding.display | Observation.code.text",
        "effectiveDateTime": "Observation.effectiveDateTime | Observation.effectivePeriod.start",
        "valueQuantity": {
            "value": "Observation.valueQuantity.value",
            "unit": "Observation.valueQuantity.unit | Observation.valueQuantity.code",
            "system": "Observation.valueQuantity.system",
        },
        "valueCodeableConcept": "Observation.valueCodeableConcept.coding.code",
        "valueString": "Observation.valueString",
        "valueBoolean": "Observation.valueBoolean",
        "valueDateTime": "Observation.valueDateTime",
        "valueQuantityString": "Observation.valueQuantity.value & ' ' & (Observation.valueQuantity.unit | Observation.valueQuantity.code)",
        "patientId": "Observation.subject.where(type = 'Patient').reference",
        "components": {
            "codes": "Observation.component.code.coding.code",
            "values": "Observation.component.value",
        }
    },
    "Encounter": {
        "id": "Encounter.id",
        "status": "Encounter.status",
        "class": "Encounter.class.code",
        "type": "Encounter.type.coding.code",
        "typeDisplay": "Encounter.type.coding.display | Encounter.type.text",
        "serviceType": "Encounter.serviceType.coding.code",
        "priority": "Encounter.priority.coding.code",
        "subject": "Encounter.subject.reference",
        "participantTypes": "Encounter.participant.type.coding.code",
        "period": {
            "start": "Encounter.period.start",
            "end": "Encounter.period.end",
        },
        "length": "Encounter.length.value & ' ' & Encounter.length.unit",
        "diagnosis": {
            "condition": "Encounter.diagnosis.condition.reference",
            "role": "Encounter.diagnosis.role.coding.code",
            "rank": "Encounter.diagnosis.rank",
        },
        "location": "Encounter.location.location.reference",
        "serviceProvider": "Encounter.serviceProvider.reference",
    },
}


def extract_patient_demographics(patient: Any) -> Dict[str, Any]:
    """
    Extract comprehensive demographic information from a Patient resource using FHIRPath.
    
    Args:
        patient: Patient resource (dictionary or FHIR resource model)
        
    Returns:
        Dictionary with demographic information
    """
    extractor = FHIRPathExtractor()
    expressions = COMMON_FHIRPATH_EXPRESSIONS["Patient"]
    
    # Extract basic demographics
    demographics = {
        "id": extractor.extract_first(patient, expressions["id"]),
        "gender": extractor.extract_first(patient, expressions["gender"]),
        "birthDate": extractor.extract_first(patient, expressions["birthDate"]),
        "active": extractor.extract_first(patient, expressions["active"], True),
        "deceased": extractor.extract_first(patient, expressions["deceased"], False),
        "maritalStatus": extractor.extract_first(patient, expressions["maritalStatus"]),
    }
    
    # Extract name components
    demographics["name"] = {
        "family": extractor.extract_first(patient, expressions["familyName"]),
        "given": extractor.extract(patient, expressions["givenNames"]),
    }
    
    if demographics["name"]["given"]:
        demographics["name"]["first"] = demographics["name"]["given"][0]
        if len(demographics["name"]["given"]) > 1:
            demographics["name"]["middle"] = demographics["name"]["given"][1:]
    
    # Extract contact information
    demographics["telecom"] = {
        "phone": extractor.extract_first(patient, expressions["telecom"]["phone"]),
        "email": extractor.extract_first(patient, expressions["telecom"]["email"]),
        "mobile": extractor.extract_first(patient, expressions["telecom"]["mobile"]),
    }
    
    # Extract address
    demographics["address"] = {
        "line": extractor.extract(patient, expressions["address"]["line"]),
        "city": extractor.extract_first(patient, expressions["address"]["city"]),
        "state": extractor.extract_first(patient, expressions["address"]["state"]),
        "postalCode": extractor.extract_first(patient, expressions["address"]["postalCode"]),
        "country": extractor.extract_first(patient, expressions["address"]["country"]),
    }
    
    # Extract identifiers
    demographics["identifiers"] = {
        "mrn": extractor.extract_first(patient, expressions["identifiers"]["mrn"]),
        "ssn": extractor.extract_first(patient, expressions["identifiers"]["ssn"]),
    }
    
    # Extract language, race, and ethnicity
    demographics["language"] = extractor.extract_first(patient, expressions["language"])
    demographics["race"] = extractor.extract_first(patient, expressions["race"])
    demographics["ethnicity"] = extractor.extract_first(patient, expressions["ethnicity"])
    
    return demographics


def extract_observation_values(observation: Any) -> Dict[str, Any]:
    """
    Extract values from an Observation resource using FHIRPath.
    
    Args:
        observation: Observation resource (dictionary or FHIR resource model)
        
    Returns:
        Dictionary with extracted values
    """
    extractor = FHIRPathExtractor()
    expressions = COMMON_FHIRPATH_EXPRESSIONS["Observation"]
    
    # Extract basic information
    result = {
        "id": extractor.extract_first(observation, expressions["id"]),
        "status": extractor.extract_first(observation, expressions["status"]),
        "category": extractor.extract(observation, expressions["category"]),
        "code": extractor.extract_first(observation, expressions["code"]),
        "codeDisplay": extractor.extract_first(observation, expressions["codeDisplay"]),
        "effectiveDateTime": extractor.extract_first(observation, expressions["effectiveDateTime"]),
        "patientId": extractor.extract_first(observation, expressions["patientId"]),
    }
    
    # Extract value based on type
    value_quantity = extractor.extract_first(observation, expressions["valueQuantity"]["value"])
    value_string = extractor.extract_first(observation, expressions["valueString"])
    value_boolean = extractor.extract_first(observation, expressions["valueBoolean"])
    value_datetime = extractor.extract_first(observation, expressions["valueDateTime"])
    value_codeable_concept = extractor.extract_first(observation, expressions["valueCodeableConcept"])
    
    if value_quantity is not None:
        result["value"] = value_quantity
        result["valueType"] = "Quantity"
        result["unit"] = extractor.extract_first(observation, expressions["valueQuantity"]["unit"])
        result["valueString"] = extractor.extract_first(observation, expressions["valueQuantityString"])
    elif value_string is not None:
        result["value"] = value_string
        result["valueType"] = "String"
        result["valueString"] = value_string
    elif value_boolean is not None:
        result["value"] = value_boolean
        result["valueType"] = "Boolean"
        result["valueString"] = "Yes" if value_boolean else "No"
    elif value_datetime is not None:
        result["value"] = value_datetime
        result["valueType"] = "DateTime"
        result["valueString"] = value_datetime
    elif value_codeable_concept is not None:
        result["value"] = value_codeable_concept
        result["valueType"] = "CodeableConcept"
        result["valueString"] = extractor.extract_first(observation, "Observation.valueCodeableConcept.coding.display | Observation.valueCodeableConcept.text")
    
    # Extract components for panel-type observations
    component_codes = extractor.extract(observation, expressions["components"]["codes"])
    if component_codes:
        result["components"] = []
        for i, code in enumerate(component_codes):
            component = {
                "code": code,
                "codeDisplay": extractor.extract_first(observation, f"Observation.component[{i}].code.coding.display | Observation.component[{i}].code.text"),
            }
            
            # Extract component value based on type
            if extractor.exists(observation, f"Observation.component[{i}].valueQuantity"):
                component["value"] = extractor.extract_first(observation, f"Observation.component[{i}].valueQuantity.value")
                component["unit"] = extractor.extract_first(observation, f"Observation.component[{i}].valueQuantity.unit | Observation.component[{i}].valueQuantity.code")
                component["valueType"] = "Quantity"
                component["valueString"] = f"{component['value']} {component['unit'] or ''}"
            elif extractor.exists(observation, f"Observation.component[{i}].valueString"):
                component["value"] = extractor.extract_first(observation, f"Observation.component[{i}].valueString")
                component["valueType"] = "String"
                component["valueString"] = component["value"]
            elif extractor.exists(observation, f"Observation.component[{i}].valueCodeableConcept"):
                component["value"] = extractor.extract_first(observation, f"Observation.component[{i}].valueCodeableConcept.coding.code")
                component["valueType"] = "CodeableConcept"
                component["valueString"] = extractor.extract_first(observation, f"Observation.component[{i}].valueCodeableConcept.coding.display | Observation.component[{i}].valueCodeableConcept.text")
            elif extractor.exists(observation, f"Observation.component[{i}].valueBoolean"):
                component["value"] = extractor.extract_first(observation, f"Observation.component[{i}].valueBoolean")
                component["valueType"] = "Boolean"
                component["valueString"] = "Yes" if component["value"] else "No"
            
            result["components"].append(component)
    
    return result 