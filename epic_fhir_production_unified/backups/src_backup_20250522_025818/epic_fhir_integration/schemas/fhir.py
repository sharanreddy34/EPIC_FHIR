"""
FHIR resource schemas for data validation.

This module defines schemas for FHIR resources to ensure data quality
and consistent transformation. These schemas can be used for validation
before CSV generation and for implementing schema-based mapping.
"""

from typing import Any, Dict, List, Optional, Union

# Base field types for FHIR resources
FIELD_TYPES = {
    "string": str,
    "integer": int,
    "decimal": float,
    "boolean": bool,
    "date": str,  # ISO 8601 date format
    "dateTime": str,  # ISO 8601 dateTime format
    "code": str,  # String representing a coded value
    "reference": str,  # Reference to another resource
    "quantity": dict,  # A quantity with value and unit
    "codeableConcept": dict,  # A coded concept
    "identifier": dict,  # An identifier
}

# Common validation rules
VALIDATION_RULES = {
    "date": {
        "regex": r"^\d{4}-\d{2}-\d{2}$",
        "min_value": "1900-01-01",
        "max_value": "2099-12-31",
    },
    "dateTime": {
        "regex": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$",
    },
    "gender": {
        "allowed_values": ["male", "female", "other", "unknown"],
    },
    "boolean": {
        "allowed_values": [True, False],
    },
    "status": {
        "allowed_values": ["active", "inactive", "entered-in-error", "draft", "completed"],
    },
    "encounter_status": {
        "allowed_values": ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled"],
    },
    "medication_status": {
        "allowed_values": ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"],
    },
    "condition_status": {
        "allowed_values": ["active", "recurrence", "relapse", "inactive", "remission", "resolved"],
    },
    "verification_status": {
        "allowed_values": ["unconfirmed", "provisional", "differential", "confirmed", "refuted", "entered-in-error"],
    },
    "allergy_status": {
        "allowed_values": ["active", "inactive", "resolved"],
    },
    "procedure_status": {
        "allowed_values": ["preparation", "in-progress", "not-done", "on-hold", "stopped", "completed", "entered-in-error", "unknown"],
    },
    "immunization_status": {
        "allowed_values": ["completed", "entered-in-error", "not-done"],
    },
    "document_status": {
        "allowed_values": ["current", "superseded", "entered-in-error"],
    },
    "careplan_status": {
        "allowed_values": ["active", "completed", "draft", "entered-in-error", "on-hold", "revoked", "unknown"],
    },
    "codeableConcept": {
        "validator": "validate_codeable_concept",
    },
    "reference": {
        "validator": "validate_fhir_reference",
    },
    "polymorphic": {
        "validator": "validate_polymorphic_field",
    },
}

# Schema for Patient resource
PATIENT_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "Patient",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "text": {
        "type": "object",
        "required": False,
        "description": "Text summary of the resource",
    },
    "identifier": {
        "type": "array",
        "required": False,
        "description": "Business identifiers for the patient",
        "items": {
            "type": "object",
            "properties": {
                "system": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
    "active": {
        "type": "boolean",
        "required": False,
        "default": True,
        "description": "Whether the patient's record is active",
    },
    "name": {
        "type": "array",
        "required": False,
        "description": "Patient names",
        "items": {
            "type": "object",
            "properties": {
                "use": {"type": "string"},
                "text": {"type": "string"},
                "family": {"type": "string"},
                "given": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "telecom": {
        "type": "array",
        "required": False,
        "description": "Patient contact details",
        "items": {
            "type": "object",
            "properties": {
                "system": {"type": "string"},
                "value": {"type": "string"},
                "use": {"type": "string"},
            },
        },
    },
    "gender": {
        "type": "string",
        "required": False,
        "description": "Patient gender",
        "validation": "gender",
    },
    "birthDate": {
        "type": "string",
        "required": False,
        "description": "Patient birth date",
        "validation": "date",
    },
    "address": {
        "type": "array",
        "required": False,
        "description": "Patient addresses",
        "items": {
            "type": "object",
            "properties": {
                "use": {"type": "string"},
                "type": {"type": "string"},
                "text": {"type": "string"},
                "line": {"type": "array", "items": {"type": "string"}},
                "city": {"type": "string"},
                "district": {"type": "string"},
                "state": {"type": "string"},
                "postalCode": {"type": "string"},
                "country": {"type": "string"},
            },
        },
    },
    "communication": {
        "type": "array",
        "required": False,
        "description": "Patient languages",
        "items": {
            "type": "object",
            "properties": {
                "language": {"type": "object"},
                "preferred": {"type": "boolean"},
            },
        },
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {
            "type": "object",
        },
    },
    "maritalStatus": {
        "type": "object",
        "required": False,
        "description": "Patient marital status",
        "properties": {
            "coding": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "system": {"type": "string"},
                        "code": {"type": "string"},
                        "display": {"type": "string"},
                    },
                },
            },
            "text": {"type": "string"},
        },
    },
}

# Schema for Observation resource
OBSERVATION_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "Observation",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "text": {
        "type": "object",
        "required": False,
        "description": "Text summary of the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "validation": "status",
        "description": "Observation status",
    },
    "category": {
        "type": "array",
        "required": False,
        "description": "Classification of observation",
        "items": {
            "type": "object",
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "system": {"type": "string"},
                            "code": {"type": "string"},
                            "display": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
    "code": {
        "type": "object",
        "required": True,
        "description": "Type of observation",
        "properties": {
            "coding": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "system": {"type": "string"},
                        "code": {"type": "string"},
                        "display": {"type": "string"},
                    },
                },
            },
            "text": {"type": "string"},
        },
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "effectiveDateTime": {
        "type": "string",
        "required": False,
        "description": "Date/time of observation",
        "validation": "dateTime",
    },
    "effectivePeriod": {
        "type": "object",
        "required": False,
        "description": "Period of observation",
        "properties": {
            "start": {"type": "string", "validation": "dateTime"},
            "end": {"type": "string", "validation": "dateTime"},
        },
    },
    "issued": {
        "type": "string",
        "required": False,
        "description": "Date/time issued",
        "validation": "dateTime",
    },
    "valueQuantity": {
        "type": "object",
        "required": False,
        "description": "Observation value as quantity",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string"},
            "system": {"type": "string"},
            "code": {"type": "string"},
        },
    },
    "valueString": {
        "type": "string",
        "required": False,
        "description": "Observation value as string",
    },
    "valueBoolean": {
        "type": "boolean",
        "required": False,
        "description": "Observation value as boolean",
    },
    "valueDateTime": {
        "type": "string",
        "required": False,
        "description": "Observation value as dateTime",
        "validation": "dateTime",
    },
    "valueCodeableConcept": {
        "type": "object",
        "required": False,
        "description": "Observation value as codeable concept",
        "properties": {
            "coding": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "system": {"type": "string"},
                        "code": {"type": "string"},
                        "display": {"type": "string"},
                    },
                },
            },
            "text": {"type": "string"},
        },
    },
    "interpretation": {
        "type": "array",
        "required": False,
        "description": "High, low, normal, etc.",
        "items": {
            "type": "object",
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "system": {"type": "string"},
                            "code": {"type": "string"},
                            "display": {"type": "string"},
                        },
                    },
                },
                "text": {"type": "string"},
            },
        },
    },
    "referenceRange": {
        "type": "array",
        "required": False,
        "description": "Reference ranges for the observation",
        "items": {
            "type": "object",
            "properties": {
                "low": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                        "system": {"type": "string"},
                        "code": {"type": "string"},
                    },
                },
                "high": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                        "system": {"type": "string"},
                        "code": {"type": "string"},
                    },
                },
                "text": {"type": "string"},
            },
        },
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {
            "type": "object",
        },
    },
}

# Schema for Encounter resource
ENCOUNTER_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "Encounter",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "text": {
        "type": "object",
        "required": False,
        "description": "Text summary of the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "Status of the encounter",
        "allowed_values": ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled"],
    },
    "class": {
        "type": "object",
        "required": True,
        "description": "Classification of the encounter",
        "properties": {
            "system": {"type": "string"},
            "code": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "type": {
        "type": "array",
        "required": False,
        "description": "Type of the encounter",
        "items": {
            "type": "object",
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "system": {"type": "string"},
                            "code": {"type": "string"},
                            "display": {"type": "string"},
                        },
                    },
                },
                "text": {"type": "string"},
            },
        },
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "participant": {
        "type": "array",
        "required": False,
        "description": "Participants in the encounter",
        "items": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "coding": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "system": {"type": "string"},
                                        "code": {"type": "string"},
                                        "display": {"type": "string"},
                                    },
                                },
                            },
                            "text": {"type": "string"},
                        },
                    },
                },
                "individual": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string"},
                        "display": {"type": "string"},
                    },
                },
            },
        },
    },
    "period": {
        "type": "object",
        "required": False,
        "description": "Time of encounter",
        "properties": {
            "start": {"type": "string", "validation": "dateTime"},
            "end": {"type": "string", "validation": "dateTime"},
        },
    },
    "location": {
        "type": "array",
        "required": False,
        "description": "Locations of the encounter",
        "items": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string"},
                        "display": {"type": "string"},
                    },
                },
                "status": {"type": "string"},
                "period": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string", "validation": "dateTime"},
                        "end": {"type": "string", "validation": "dateTime"},
                    },
                },
            },
        },
    },
    "serviceProvider": {
        "type": "object",
        "required": False,
        "description": "Organization responsible for the encounter",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {
            "type": "object",
        },
    },
}

# Schema for CarePlan resource
CAREPLAN_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "CarePlan",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "CarePlan status (e.g., active, completed, draft)",
        "allowed_values": ["active", "completed", "draft", "entered-in-error", "on-hold", "revoked", "unknown"],
    },
    "intent": {
        "type": "string",
        "required": True,
        "description": "Proposal, plan, order, option, etc."
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "period": {
        "type": "object",
        "required": False,
        "description": "Time period of the CarePlan",
        "properties": {
            "start": {"type": "string", "validation": "dateTime"},
            "end": {"type": "string", "validation": "dateTime"},
        },
    },
    "category": {
        "type": "array",
        "required": False,
        "description": "Type of CarePlan",
        "items": {
            "type": "object", # CodeableConcept
        },
    },
    "description": {
        "type": "string",
        "required": False,
        "description": "Summary of CarePlan",
    },
    "activity": {
        "type": "array",
        "required": False,
        "description": "Action to be taken as part of the plan",
        "items": {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"}, # e.g. Appointment, MedicationRequest
                        "code": {"type": "object"}, # CodeableConcept
                        "status": {"type": "string"},
                        "description": {"type": "string"},
                    }
                }
            }
        }
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for MedicationRequest resource
MEDICATIONREQUEST_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "MedicationRequest",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "MedicationRequest status (e.g., active, completed)",
        "allowed_values": ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"],
    },
    "intent": {
        "type": "string",
        "required": True,
        "description": "Proposal, plan, order, option, etc."
    },
    "medicationCodeableConcept": {
        "type": "object",
        "required": False, # or medicationReference
        "description": "Medication to be administered",
    },
    "medicationReference": {
        "type": "object",
        "required": False, # or medicationCodeableConcept
        "description": "Reference to Medication resource",
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "authoredOn": {
        "type": "string",
        "required": False,
        "description": "When request was initially authored",
        "validation": "dateTime",
    },
    "requester": {
        "type": "object",
        "required": False,
        "description": "Who/what requested the medication"
    },
    "dosageInstruction": {
        "type": "array",
        "required": False,
        "items": {"type": "object"} # Dosage structure
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for Condition resource
CONDITION_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "Condition",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "clinicalStatus": {
        "type": "object", # CodeableConcept
        "required": False,
        "description": "active, recurrence, relapse, inactive, remission, resolved",
    },
    "verificationStatus": {
        "type": "object", # CodeableConcept
        "required": False,
        "description": "unconfirmed, provisional, differential, confirmed, refuted, entered-in-error",
    },
    "category": {
        "type": "array",
        "required": False,
        "description": "problem-list-item | encounter-diagnosis",
        "items": {"type": "object"}, # CodeableConcept
    },
    "code": {
        "type": "object", # CodeableConcept
        "required": False, # Though typically present
        "description": "Identification of the condition, problem or diagnosis.",
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "onsetDateTime": {
        "type": "string",
        "required": False,
        "validation": "dateTime",
    },
    "recordedDate": {
        "type": "string",
        "required": False,
        "validation": "dateTime",
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for DiagnosticReport resource
DIAGNOSTICREPORT_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "DiagnosticReport",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "Report status (e.g., final, preliminary)",
        "allowed_values": ["registered", "partial", "preliminary", "final", "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"],
    },
    "category": {
        "type": "array",
        "required": False,
        "description": "Service category of the report",
        "items": {"type": "object"}, # CodeableConcept
    },
    "code": { # CodeableConcept
        "type": "object",
        "required": True,
        "description": "Name/Code for this diagnostic report",
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "effectiveDateTime": {
        "type": "string",
        "required": False,
        "validation": "dateTime",
    },
    "effectivePeriod": {
        "type": "object",
        "required": False,
        "properties": {
            "start": {"type": "string", "validation": "dateTime"},
            "end": {"type": "string", "validation": "dateTime"},
        },
    },
    "issued": {
        "type": "string",
        "required": False,
        "description": "Date/time issued",
        "validation": "dateTime",
    },
    "result": { # Array of Reference(Observation)
        "type": "array",
        "required": False,
        "description": "Observations that are part of this report",
        "items": {"type": "object"}, # Reference to Observation
    },
    "conclusion": {
        "type": "string",
        "required": False,
        "description": "Clinical conclusion summary",
    },
    "presentedForm": { # Array of Attachment
        "type": "array",
        "required": False,
        "description": "Entire report as attachment",
        "items": {"type": "object"}, # Attachment
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for AllergyIntolerance resource
ALLERGYINTOLERANCE_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "AllergyIntolerance",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "clinicalStatus": { # CodeableConcept
        "type": "object",
        "required": False,
        "description": "active | inactive | resolved",
    },
    "verificationStatus": { # CodeableConcept
        "type": "object",
        "required": False,
        "description": "unconfirmed | provisional | differential | confirmed | refuted | entered-in-error",
    },
    "type": {
        "type": "string",
        "required": False,
        "description": "allergy | intolerance - Underlying mechanism (if known)",
        "allowed_values": ["allergy", "intolerance"]
    },
    "category": {
        "type": "array",
        "required": False,
        "description": "food | medication | environment | biologic",
        "items": {"type": "string"},
    },
    "criticality": {
        "type": "string",
        "required": False,
        "description": "low | high | unable-to-assess",
        "allowed_values": ["low", "high", "unable-to-assess"]
    },
    "code": { # CodeableConcept
        "type": "object",
        "required": False, # Substance, or manifestation, or code
        "description": "Code that identifies the allergy or intolerance.",
    },
    "patient": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "reaction": {
        "type": "array",
        "required": False,
        "items": {
            "type": "object",
            "properties": {
                "substance": {"type": "object"}, # CodeableConcept
                "manifestation": {"type": "array", "items": {"type": "object"}}, # CodeableConcept
                "description": {"type": "string"},
                "severity": {"type": "string", "allowed_values": ["mild", "moderate", "severe"]},
            }
        }
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for Procedure resource
PROCEDURE_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "Procedure",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "Procedure status (e.g., completed, in-progress)",
        "allowed_values": ["preparation", "in-progress", "not-done", "on-hold", "stopped", "completed", "entered-in-error", "unknown"],
    },
    "category": { # CodeableConcept
        "type": "object",
        "required": False,
        "description": "Classification of the procedure",
    },
    "code": { # CodeableConcept
        "type": "object",
        "required": True,
        "description": "Identification of the procedure.",
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "performedDateTime": {
        "type": "string",
        "required": False,
        "validation": "dateTime",
    },
    "performedPeriod": {
        "type": "object",
        "required": False,
        "properties": {
            "start": {"type": "string", "validation": "dateTime"},
            "end": {"type": "string", "validation": "dateTime"},
        },
    },
    "reasonCode": { # Array of CodeableConcept
        "type": "array",
        "required": False,
        "description": "Coded reason procedure performed",
        "items": {"type": "object"}
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for Immunization resource
IMMUNIZATION_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "Immunization",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "completed | entered-in-error | not-done",
        "allowed_values": ["completed", "entered-in-error", "not-done"],
    },
    "vaccineCode": { # CodeableConcept
        "type": "object",
        "required": True,
        "description": "Vaccine product administered",
    },
    "patient": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "occurrenceDateTime": {
        "type": "string",
        "required": True,
        "validation": "dateTime",
    },
    "primarySource": {
        "type": "boolean",
        "required": False,
        "description": "Indicates context the data was recorded in"
    },
    "lotNumber": {
        "type": "string",
        "required": False,
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for DocumentReference resource
DOCUMENTREFERENCE_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "DocumentReference",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "status": {
        "type": "string",
        "required": True,
        "description": "current | superseded | entered-in-error",
        "allowed_values": ["current", "superseded", "entered-in-error"],
    },
    "type": { # CodeableConcept
        "type": "object",
        "required": False, # Though often present
        "description": "Kind of document (LOINC if possible)",
    },
    "category": { # Array of CodeableConcept
        "type": "array",
        "required": False,
        "description": "Categorization of document (e.g. clinical-note)",
        "items": {"type": "object"},
    },
    "subject": {
        "type": "object",
        "required": True,
        "description": "Patient reference",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "date": { # instant
        "type": "string",
        "required": False,
        "description": "When this document reference was created",
        "validation": "dateTime", # Technically 'instant' but dateTime is close
    },
    "description": {
        "type": "string",
        "required": False,
        "description": "Human-readable description",
    },
    "content": { # Array of DocumentReference.content
        "type": "array",
        "required": True,
        "items": {
            "type": "object",
            "properties": {
                "attachment": { # Attachment
                    "type": "object",
                    "required": True,
                    "properties": {
                        "contentType": {"type": "string"},
                        "language": {"type": "string"},
                        "data": {"type": "string"}, # Base64
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                    }
                },
                "format": {"type": "object"} # Coding
            }
        }
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Schema for RelatedPerson resource
RELATEDPERSON_SCHEMA = {
    "resourceType": {
        "type": "string",
        "required": True,
        "default": "RelatedPerson",
        "description": "Type of FHIR resource",
    },
    "id": {
        "type": "string",
        "required": True,
        "description": "Logical ID of the resource",
    },
    "meta": {
        "type": "object",
        "required": False,
        "description": "Metadata about the resource",
    },
    "patient": {
        "type": "object",
        "required": True,
        "description": "The patient this person is related to",
        "properties": {
            "reference": {"type": "string"},
            "display": {"type": "string"},
        },
    },
    "relationship": { # Array of CodeableConcept
        "type": "array",
        "required": False,
        "description": "The nature of the relationship",
        "items": {"type": "object"},
    },
    "name": {
        "type": "array",
        "required": False,
        "description": "Name of the related person",
        "items": { # HumanName
            "type": "object",
        },
    },
    "telecom": { # Array of ContactPoint
        "type": "array",
        "required": False,
    },
    "gender": {
        "type": "string",
        "required": False,
        "validation": "gender",
    },
    "birthDate": {
        "type": "string",
        "required": False,
        "validation": "date",
    },
    "extension": {
        "type": "array",
        "required": False,
        "description": "FHIR extensions",
        "items": {"type": "object"},
    },
}

# Dictionary of available schemas
RESOURCE_SCHEMAS = {
    "Patient": PATIENT_SCHEMA,
    "Observation": OBSERVATION_SCHEMA,
    "Encounter": ENCOUNTER_SCHEMA,
    "CarePlan": CAREPLAN_SCHEMA,
    "MedicationRequest": MEDICATIONREQUEST_SCHEMA,
    "Condition": CONDITION_SCHEMA,
    "DiagnosticReport": DIAGNOSTICREPORT_SCHEMA,
    "AllergyIntolerance": ALLERGYINTOLERANCE_SCHEMA,
    "Procedure": PROCEDURE_SCHEMA,
    "Immunization": IMMUNIZATION_SCHEMA,
    "DocumentReference": DOCUMENTREFERENCE_SCHEMA,
    "RelatedPerson": RELATEDPERSON_SCHEMA,
    # Add other schemas as they are defined
}

# Define fallback paths for commonly missing fields
FALLBACK_PATHS = {
    "Patient": {
        "gender": [
            "gender",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-gender]",
        ],
        "birthDate": [
            "birthDate",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-birthDate]",
        ],
        "name.family": [
            "name[0].family",
            "name[use=official].family",
        ],
        "language": [
            "communication[0].language.coding[0].code",
            "communication[0].language.text",
            "communication[preferred=true].language.coding[0].code",
        ],
        "maritalStatus": [
            "maritalStatus.text",
            "maritalStatus.coding[0].display",
            "maritalStatus.coding[0].code",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-maritalStatus].valueCodeableConcept.text",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-maritalStatus].valueCodeableConcept.coding[0].display",
        ],
        "race": [
            "extension[url=http://hl7.org/fhir/us/core/StructureDefinition/us-core-race].extension[url=text].valueString",
            "extension[url=http://hl7.org/fhir/us/core/StructureDefinition/us-core-race].extension[url=ombCategory].valueCoding.display",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-race].valueCodeableConcept.text",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-race].valueCodeableConcept.coding[0].display",
        ],
        "ethnicity": [
            "extension[url=http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity].extension[url=text].valueString",
            "extension[url=http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity].extension[url=ombCategory].valueCoding.display",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-ethnicity].valueCodeableConcept.text",
            "extension[url=http://hl7.org/fhir/StructureDefinition/patient-ethnicity].valueCodeableConcept.coding[0].display",
        ],
    },
    "Observation": {
        "value": [
            "valueQuantity.value",
            "valueString",
            "valueBoolean",
            "valueDateTime",
            "valueCodeableConcept.text",
            "valueCodeableConcept.coding[0].display",
            "component[0].valueQuantity.value",
            "component[0].valueString",
            "component[0].valueCodeableConcept.text",
        ],
        "unit": [
            "valueQuantity.unit",
            "valueQuantity.code",
            "component[0].valueQuantity.unit",
            "component[0].valueQuantity.code",
        ],
        "date": [
            "effectiveDateTime",
            "effectivePeriod.start",
            "issued",
        ],
        "code": [
            "code.text",
            "code.coding[0].display",
            "code.coding[0].code",
        ],
        "category": [
            "category[0].text",
            "category[0].coding[0].display",
            "category[0].coding[0].code",
        ],
    },
    "Encounter": {
        "date": [
            "period.start",
            "period.end",
        ],
        "class": [
            "class.display",
            "class.code",
        ],
        "type": [
            "type[0].text",
            "type[0].coding[0].display",
            "type[0].coding[0].code",
        ],
        "status": [
            "status",
        ],
    },
    "MedicationRequest": {
        "medication": [
            "medicationCodeableConcept.text",
            "medicationCodeableConcept.coding[0].display",
            "medicationReference.display",
        ],
        "date": [
            "authoredOn",
        ],
        "dosage": [
            "dosageInstruction[0].text",
            "dosageInstruction[0].patientInstruction",
        ],
    },
    "Condition": {
        "code": [
            "code.text",
            "code.coding[0].display",
            "code.coding[0].code",
        ],
        "status": [
            "clinicalStatus.coding[0].code",
            "clinicalStatus.text",
            "verificationStatus.coding[0].code",
        ],
        "date": [
            "onsetDateTime",
            "recordedDate",
        ],
    },
    "DiagnosticReport": {
        "code": [
            "code.text",
            "code.coding[0].display",
            "code.coding[0].code",
        ],
        "date": [
            "effectiveDateTime",
            "effectivePeriod.start",
            "issued",
        ],
        "conclusion": [
            "conclusion",
            "presentedForm[0].title",
        ],
    },
    "AllergyIntolerance": {
        "substance": [
            "code.text",
            "code.coding[0].display",
            "code.coding[0].code",
        ],
        "reaction": [
            "reaction[0].manifestation[0].text",
            "reaction[0].manifestation[0].coding[0].display",
            "reaction[0].description",
        ],
        "severity": [
            "reaction[0].severity",
        ],
        "status": [
            "clinicalStatus.coding[0].code",
            "clinicalStatus.text",
            "verificationStatus.coding[0].code",
        ],
    },
    "Procedure": {
        "code": [
            "code.text",
            "code.coding[0].display",
            "code.coding[0].code",
        ],
        "date": [
            "performedDateTime",
            "performedPeriod.start",
        ],
        "reason": [
            "reasonCode[0].text",
            "reasonCode[0].coding[0].display",
        ],
    },
    "Immunization": {
        "vaccine": [
            "vaccineCode.text",
            "vaccineCode.coding[0].display",
            "vaccineCode.coding[0].code",
        ],
        "date": [
            "occurrenceDateTime",
        ],
    },
    "DocumentReference": {
        "type": [
            "type.text",
            "type.coding[0].display",
            "type.coding[0].code",
        ],
        "category": [
            "category[0].text",
            "category[0].coding[0].display",
            "category[0].coding[0].code",
        ],
        "content": [
            "content[0].attachment.data",
            "content[0].attachment.url",
        ],
        "date": [
            "date",
        ],
    },
    "RelatedPerson": {
        "relationship": [
            "relationship[0].text",
            "relationship[0].coding[0].display",
            "relationship[0].coding[0].code",
        ],
        "name": [
            "name[0].text",
            "name[0].family",
        ],
    },
    "CarePlan": {
        "activity": [
            "activity[0].detail.description",
            "activity[0].detail.status",
            "activity[0].detail.code.text",
            "activity[0].detail.code.coding[0].display",
        ],
        "date": [
            "period.start",
            "period.end",
        ],
    },
}

def get_schema_for_resource(resource_type: str) -> Dict[str, Any]:
    """
    Get the schema for a specific resource type.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        
    Returns:
        Schema definition for the resource type
        
    Raises:
        ValueError: If no schema is defined for the resource type
    """
    if resource_type not in RESOURCE_SCHEMAS:
        raise ValueError(f"No schema defined for resource type: {resource_type}")
        
    return RESOURCE_SCHEMAS[resource_type]

def get_fallback_paths(resource_type: str, field_path: str) -> List[str]:
    """
    Get fallback paths for a field in a resource type.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        field_path: Path to the field (e.g., "gender", "name.family")
        
    Returns:
        List of fallback paths for the field
    """
    if resource_type not in FALLBACK_PATHS:
        return [field_path]
        
    if field_path not in FALLBACK_PATHS[resource_type]:
        return [field_path]
        
    return FALLBACK_PATHS[resource_type][field_path] 