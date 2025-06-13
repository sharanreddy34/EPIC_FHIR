#!/usr/bin/env python
"""
Prototype script to demonstrate using fhir.resources for FHIR data parsing and validation.
This script parses a sample Patient resource and accesses attributes to verify functionality.
"""

import json
import logging
from pathlib import Path

from fhir.resources.patient import Patient
from pydantic import ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample Patient resource as JSON
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "example",
    "meta": {
        "versionId": "1",
        "lastUpdated": "2022-01-01T12:00:00Z"
    },
    "text": {
        "status": "generated",
        "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">Sample Patient</div>"
    },
    "identifier": [
        {
            "use": "usual",
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MR"
                    }
                ]
            },
            "system": "urn:oid:1.2.36.146.595.217.0.1",
            "value": "12345",
            "period": {
                "start": "2001-05-06"
            },
            "assigner": {
                "display": "Epic Hospital"
            }
        }
    ],
    "active": True,
    "name": [
        {
            "use": "official",
            "family": "Smith",
            "given": ["John", "Jacob"]
        }
    ],
    "telecom": [
        {
            "system": "phone",
            "value": "555-555-5555",
            "use": "home"
        },
        {
            "system": "email",
            "value": "john.smith@example.com"
        }
    ],
    "gender": "male",
    "birthDate": "1974-12-25",
    "address": [
        {
            "use": "home",
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",
            "country": "USA"
        }
    ]
}

def test_patient_parsing():
    """Parse a sample Patient resource and access attributes."""
    try:
        # Parse JSON into a fhir.resources Patient object
        patient = Patient.model_validate(SAMPLE_PATIENT)
        
        # Access and log various attributes to verify functionality
        logger.info(f"Patient ID: {patient.id}")
        logger.info(f"Patient is active: {patient.active}")
        
        # Access nested attributes
        if patient.name and len(patient.name) > 0:
            logger.info(f"Patient name: {patient.name[0].family}, {' '.join(patient.name[0].given or [])}")
        
        if patient.birthDate:
            logger.info(f"Birth date: {patient.birthDate}")
        
        if patient.identifier and len(patient.identifier) > 0:
            logger.info(f"Medical record number: {patient.identifier[0].value}")
        
        # Test modifications
        patient.active = False
        logger.info(f"Modified - Patient is active: {patient.active}")
        
        # Convert back to dict/JSON using new model_dump method instead of dict
        patient_dict = patient.model_dump(exclude_none=True)
        logger.info(f"Conversion back to dict successful: {len(patient_dict) > 0}")

        # Generate JSON string using model_dump_json
        json_str = patient.model_dump_json(indent=2)
        logger.info(f"JSON string generated successfully: {len(json_str) > 0}")
        
        # Demonstrate validation error with invalid data
        invalid_patient = SAMPLE_PATIENT.copy()
        invalid_patient["gender"] = "invalid_gender"
        try:
            Patient.model_validate(invalid_patient)
        except ValidationError as e:
            logger.info(f"Validation correctly failed for invalid gender: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Patient resource: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting FHIR Resources prototype test")
    success = test_patient_parsing()
    logger.info(f"Prototype test {'succeeded' if success else 'failed'}") 