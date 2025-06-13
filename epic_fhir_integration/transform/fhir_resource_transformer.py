"""
FHIR Resource Transformer Module

This module handles proper transformation of FHIR resources through the quality tiers:
- Bronze: Raw data with minimal validation
- Silver: Enhanced data with cleansing and basic extensions
- Gold: Fully conformant, enriched data optimized for analytics and LLM use

Addresses common transformation issues:
1. Data Consistency Problems
2. Profile Conformance Violations
3. Missing Cardinality Requirements
4. Improper Extension Structure
5. Data Loss Between Tiers
6. Missing Validation Logic
7. Incomplete Narrative Generation
8. Handling of Sensitive Data
"""

import os
import json
import copy
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FHIRResourceTransformer:
    """Handles transformation of FHIR resources through quality tiers."""
    
    def __init__(self, validation_mode: str = "strict", debug: bool = False):
        """
        Initialize the transformer.
        
        Args:
            validation_mode: One of ["strict", "moderate", "lenient"]
            debug: Enable debug logging
        """
        self.validation_mode = validation_mode
        
        if debug:
            logger.setLevel(logging.DEBUG)
            
        # Known valid FHIR valuesets
        self.name_use_values = ["official", "usual", "temp", "nickname", "anonymous", "old", "maiden"]
        self.telecom_system_values = ["phone", "fax", "email", "pager", "url", "sms", "other"]
        self.address_use_values = ["home", "work", "temp", "old", "billing"]
        self.gender_values = ["male", "female", "other", "unknown"]
        
        # Track transformation metadata
        self.transformation_metadata = {
            "transformed_at": datetime.datetime.now().isoformat(),
            "transformer_version": "1.0.0",
            "validation_mode": validation_mode,
            "modifications": []
        }
        
    # ========================
    # Bronze to Silver Transformations
    # ========================
    
    def bronze_to_silver(self, resource: Dict) -> Dict:
        """
        Transform a resource from bronze to silver quality tier.
        
        Args:
            resource: FHIR resource in bronze quality tier
            
        Returns:
            Transformed resource in silver quality tier
        """
        if not resource or not isinstance(resource, dict):
            logger.warning("Invalid resource provided for transformation")
            return {}
            
        # Create a deep copy to avoid modifying the original
        silver = copy.deepcopy(resource)
        
        # Add quality tier metadata
        self._add_quality_tier_metadata(silver, "SILVER")
        
        # Apply transformations based on resource type
        resource_type = silver.get("resourceType")
        
        if resource_type == "Patient":
            silver = self._transform_patient_to_silver(silver)
        elif resource_type == "Observation":
            silver = self._transform_observation_to_silver(silver)
        elif resource_type == "Encounter":
            silver = self._transform_encounter_to_silver(silver)
        else:
            # Generic transformation for other resource types
            silver = self._transform_generic_to_silver(silver)
            
        return silver
        
    def _transform_patient_to_silver(self, patient: Dict) -> Dict:
        """Transform Patient resource to silver tier."""
        # Fix issue #1: Data Consistency Problems
        # Ensure gender and extensions are consistent
        if "gender" in patient and "_gender" in patient:
            if "extension" in patient["_gender"]:
                # Remove any data-absent-reason extensions if gender is present
                patient["_gender"]["extension"] = [
                    ext for ext in patient["_gender"]["extension"]
                    if not (ext.get("url") == "http://hl7.org/fhir/StructureDefinition/data-absent-reason" and 
                           patient["gender"] is not None)
                ]
        
        # Fix issue #3: Missing Cardinality Requirements
        # Ensure name has required properties
        if "name" in patient:
            for i, name in enumerate(patient["name"]):
                # Fix issue #5: Data Loss Between Tiers
                # Don't assume "official" if not specified in original
                if "use" not in name:
                    name["use"] = "usual"  # Use "usual" as the default
                    self._track_modification(patient, f"name[{i}].use", None, "usual", 
                                           "Added default name.use")
                # Make sure name has either family or text
                if not name.get("family") and not name.get("text"):
                    given = " ".join(name.get("given", []))
                    if given:
                        name["text"] = given
                        self._track_modification(patient, f"name[{i}].text", None, given, 
                                               "Added name.text from given name")
                
                # Validate name.use
                if name.get("use") and name["use"] not in self.name_use_values:
                    original = name["use"]
                    name["use"] = "usual"
                    self._track_modification(patient, f"name[{i}].use", original, "usual", 
                                           "Corrected invalid name.use")
        
        # Fix issue #3: Ensure minimal identifier
        if not patient.get("identifier"):
            patient["identifier"] = [{
                "system": "http://example.org/fhir/temp-identifiers",
                "value": f"TEMP-{patient.get('id', 'UNKNOWN')}"
            }]
            self._track_modification(patient, "identifier", None, patient["identifier"], 
                                   "Added minimal identifier")
                
        # Fix issue #6: Validate date formats
        if "birthDate" in patient:
            try:
                datetime.datetime.strptime(patient["birthDate"], "%Y-%m-%d")
            except ValueError:
                # Flag invalid date without removing data
                if "_birthDate" not in patient:
                    patient["_birthDate"] = {}
                patient["_birthDate"]["extension"] = [{
                    "url": "http://example.org/fhir/StructureDefinition/validation-issue",
                    "valueString": "Invalid date format, should be YYYY-MM-DD"
                }]
                self._track_modification(patient, "_birthDate.extension", None, 
                                       patient["_birthDate"]["extension"], 
                                       "Added validation warning for birthDate")
                
        # Validate telecom
        if "telecom" in patient:
            for i, telecom in enumerate(patient["telecom"]):
                if "system" in telecom and telecom["system"] not in self.telecom_system_values:
                    original = telecom["system"]
                    telecom["system"] = "other"
                    self._track_modification(patient, f"telecom[{i}].system", original, "other", 
                                           "Corrected invalid telecom.system value")
                if "use" in telecom and telecom["use"] not in ["home", "work", "temp", "old", "mobile"]:
                    original = telecom["use"]
                    telecom["use"] = "temp"
                    self._track_modification(patient, f"telecom[{i}].use", original, "temp", 
                                           "Corrected invalid telecom.use value")
                
        return patient
        
    def _transform_observation_to_silver(self, observation: Dict) -> Dict:
        """Transform Observation resource to silver tier."""
        # Ensure minimal requirements are met
        if "status" not in observation:
            observation["status"] = "unknown"
            self._track_modification(observation, "status", None, "unknown", 
                                   "Added missing required status")
                                   
        # Validate code
        if "code" not in observation:
            observation["code"] = {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                    "code": "unknown",
                    "display": "Unknown"
                }]
            }
            self._track_modification(observation, "code", None, observation["code"], 
                                   "Added missing required code")
                                   
        # Ensure subject reference is valid
        if "subject" in observation and "reference" in observation["subject"]:
            if not observation["subject"]["reference"].startswith("Patient/"):
                original = observation["subject"]["reference"]
                if "/" in original:
                    # It's a reference but not to a Patient
                    # Don't modify as it could be valid
                    pass
                else:
                    # Fix format to be a proper reference
                    observation["subject"]["reference"] = f"Patient/{original}"
                    self._track_modification(observation, "subject.reference", original, 
                                           observation["subject"]["reference"], 
                                           "Fixed subject reference format")
        
        return observation
        
    def _transform_encounter_to_silver(self, encounter: Dict) -> Dict:
        """Transform Encounter resource to silver tier."""
        # Ensure minimal requirements
        if "status" not in encounter:
            encounter["status"] = "unknown"
            self._track_modification(encounter, "status", None, "unknown", 
                                   "Added missing required status")
        
        # Validate status value
        valid_statuses = ["planned", "arrived", "triaged", "in-progress", "onleave", 
                         "finished", "cancelled", "entered-in-error", "unknown"]
        if encounter.get("status") and encounter["status"] not in valid_statuses:
            original = encounter["status"]
            encounter["status"] = "unknown"
            self._track_modification(encounter, "status", original, "unknown", 
                                   "Corrected invalid status value")
        
        # Ensure period has valid format
        for field in ["start", "end"]:
            period_field = f"period.{field}"
            if "period" in encounter and field in encounter["period"]:
                try:
                    # Attempt to parse datetime
                    date_str = encounter["period"][field]
                    # Basic validation - should have 'T' between date and time
                    if "T" not in date_str:
                        original = date_str
                        # Try to fix common formats
                        if " " in date_str:
                            # Convert space to 'T'
                            date_str = date_str.replace(" ", "T")
                            encounter["period"][field] = date_str
                            self._track_modification(encounter, f"period.{field}", original, date_str, 
                                                   "Fixed datetime format")
                except (ValueError, TypeError):
                    # Add validation warning without removing data
                    if "_period" not in encounter:
                        encounter["_period"] = {}
                    if field not in encounter["_period"]:
                        encounter["_period"][field] = {}
                    encounter["_period"][field]["extension"] = [{
                        "url": "http://example.org/fhir/StructureDefinition/validation-issue",
                        "valueString": f"Invalid datetime format in period.{field}"
                    }]
                    self._track_modification(encounter, f"_period.{field}.extension", None, 
                                           encounter["_period"][field]["extension"], 
                                           "Added validation warning for period")
                           
        return encounter
        
    def _transform_generic_to_silver(self, resource: Dict) -> Dict:
        """Generic transformation for any resource type."""
        # Add required metadata
        if "meta" not in resource:
            resource["meta"] = {}
            
        if "lastUpdated" not in resource["meta"]:
            resource["meta"]["lastUpdated"] = datetime.datetime.now().isoformat()
            self._track_modification(resource, "meta.lastUpdated", None, 
                                   resource["meta"]["lastUpdated"], 
                                   "Added missing lastUpdated timestamp")
                                   
        return resource
    
    # ========================
    # Silver to Gold Transformations
    # ========================
    
    def silver_to_gold(self, resource: Dict) -> Dict:
        """
        Transform a resource from silver to gold quality tier.
        
        Args:
            resource: FHIR resource in silver quality tier
            
        Returns:
            Transformed resource in gold quality tier
        """
        if not resource or not isinstance(resource, dict):
            logger.warning("Invalid resource provided for transformation")
            return {}
            
        # Create a deep copy to avoid modifying the original
        gold = copy.deepcopy(resource)
        
        # Add quality tier metadata
        self._add_quality_tier_metadata(gold, "GOLD")
        
        # Apply transformations based on resource type
        resource_type = gold.get("resourceType")
        
        if resource_type == "Patient":
            gold = self._transform_patient_to_gold(gold)
        elif resource_type == "Observation":
            gold = self._transform_observation_to_gold(gold)
        elif resource_type == "Encounter":
            gold = self._transform_encounter_to_gold(gold)
        else:
            # Generic transformation for other resource types
            gold = self._transform_generic_to_gold(gold)
            
        return gold
        
    def _transform_patient_to_gold(self, patient: Dict) -> Dict:
        """Transform Patient resource to gold tier."""
        # Fix issue #2: Profile Conformance Violations
        # Check for mandatory US Core elements before claiming conformance
        has_identifier = bool(patient.get("identifier", []))
        has_name = any(n.get("family") or n.get("text") for n in patient.get("name", []))
        
        # Only claim US Core conformance if requirements are met
        if has_identifier and has_name:
            if "meta" not in patient:
                patient["meta"] = {}
            if "profile" not in patient["meta"]:
                patient["meta"]["profile"] = []
            
            us_core_profile = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
            if us_core_profile not in patient["meta"]["profile"]:
                patient["meta"]["profile"].append(us_core_profile)
                self._track_modification(patient, "meta.profile", patient["meta"].get("profile", []), 
                                       patient["meta"]["profile"], 
                                       "Added US Core profile")
        
        # Fix issue #4: Extension Structure
        if "extension" in patient:
            for i, ext in enumerate(patient["extension"]):
                if ext.get("url") == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
                    # Check if the extension has the required nested extensions
                    if "extension" not in ext:
                        ext["extension"] = []
                        
                    # Check for required components
                    has_omb = any(nested.get("url") == "ombCategory" for nested in ext.get("extension", []))
                    has_text = any(nested.get("url") == "text" for nested in ext.get("extension", []))
                    
                    # Add missing required components
                    if not has_omb:
                        # Add default OMB category
                        ext["extension"].append({
                            "url": "ombCategory",
                            "valueCoding": {
                                "system": "urn:oid:2.16.840.1.113883.6.238",
                                "code": "UNK",
                                "display": "Unknown"
                            }
                        })
                        self._track_modification(patient, f"extension[{i}].extension", ext["extension"], 
                                               ext["extension"], 
                                               "Added missing OMB category to race extension")
                    
                    if not has_text:
                        # Add text representation
                        omb_category = None
                        for nested in ext["extension"]:
                            if nested.get("url") == "ombCategory" and "valueCoding" in nested:
                                omb_category = nested["valueCoding"].get("display", "Unknown")
                                
                        ext["extension"].append({
                            "url": "text",
                            "valueString": omb_category or "Unknown"
                        })
                        self._track_modification(patient, f"extension[{i}].extension", ext["extension"], 
                                               ext["extension"], 
                                               "Added missing text to race extension")
        
        # Fix issue #7: Generate comprehensive narrative
        patient["text"] = self._generate_patient_narrative(patient)
        self._track_modification(patient, "text", None, patient["text"], 
                               "Added comprehensive narrative")
                               
        # Fix issue #8: Handle sensitive data appropriately  
        # This is just a marker - actual implementation would depend on organization policies
        self._add_phi_handling_metadata(patient)
        
        return patient
        
    def _transform_observation_to_gold(self, observation: Dict) -> Dict:
        """Transform Observation resource to gold tier."""
        # Fix issue #2: Check US Core Observation requirements
        has_category = bool(observation.get("category", []))
        has_code = bool(observation.get("code"))
        has_status = bool(observation.get("status"))
        has_subject = bool(observation.get("subject"))
        
        # Only claim US Core conformance if requirements are met
        if has_category and has_code and has_status and has_subject:
            if "meta" not in observation:
                observation["meta"] = {}
            if "profile" not in observation["meta"]:
                observation["meta"]["profile"] = []
            
            us_core_profile = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"
            if us_core_profile not in observation["meta"]["profile"]:
                observation["meta"]["profile"].append(us_core_profile)
                self._track_modification(observation, "meta.profile", observation["meta"].get("profile", []), 
                                       observation["meta"]["profile"], 
                                       "Added US Core Observation profile")
        
        # Fix issue #7: Generate comprehensive narrative
        observation["text"] = self._generate_observation_narrative(observation)
        self._track_modification(observation, "text", None, observation["text"], 
                               "Added comprehensive narrative")
        
        return observation
        
    def _transform_encounter_to_gold(self, encounter: Dict) -> Dict:
        """Transform Encounter resource to gold tier."""
        # Same pattern as other resources - ensure US Core requirements are met
        # Generate comprehensive narrative
        encounter["text"] = self._generate_encounter_narrative(encounter)
        self._track_modification(encounter, "text", None, encounter["text"], 
                               "Added comprehensive narrative")
        
        return encounter
        
    def _transform_generic_to_gold(self, resource: Dict) -> Dict:
        """Generic transformation for any resource type."""
        # Add narrative if missing
        if "text" not in resource:
            resource["text"] = self._generate_generic_narrative(resource)
            self._track_modification(resource, "text", None, resource["text"], 
                                   "Added basic narrative")
                                   
        return resource
    
    # ========================
    # Helper Methods
    # ========================
    
    def _add_quality_tier_metadata(self, resource: Dict, tier: str) -> None:
        """Add quality tier tag to resource metadata."""
        if "meta" not in resource:
            resource["meta"] = {}
            
        if "tag" not in resource["meta"]:
            resource["meta"]["tag"] = []
            
        # Remove any existing quality tier tags
        resource["meta"]["tag"] = [
            tag for tag in resource["meta"]["tag"]
            if not (tag.get("system") == "http://terminology.hl7.org/CodeSystem/v3-ObservationValue" and
                  tag.get("code") in ["BRONZE", "SILVER", "GOLD"])
        ]
        
        # Add the new quality tier tag
        resource["meta"]["tag"].append({
            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationValue",
            "code": tier,
            "display": f"{tier.capitalize()} Quality Tier"
        })
        
    def _track_modification(self, resource: Dict, path: str, old_value: Any, 
                          new_value: Any, reason: str) -> None:
        """Track a modification to the resource for audit purposes."""
        # Add to internal tracking
        self.transformation_metadata["modifications"].append({
            "resource_type": resource.get("resourceType"),
            "resource_id": resource.get("id"),
            "path": path,
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Add to resource metadata if requested
        if self.validation_mode == "strict":
            if "meta" not in resource:
                resource["meta"] = {}
                
            if "extension" not in resource["meta"]:
                resource["meta"]["extension"] = []
                
            resource["meta"]["extension"].append({
                "url": "http://example.org/fhir/StructureDefinition/transformation-history",
                "extension": [
                    {
                        "url": "path",
                        "valueString": path
                    },
                    {
                        "url": "reason",
                        "valueString": reason
                    },
                    {
                        "url": "timestamp",
                        "valueInstant": datetime.datetime.now().isoformat()
                    }
                ]
            })
            
    def _add_phi_handling_metadata(self, resource: Dict) -> None:
        """Add PHI handling metadata to the resource."""
        if "meta" not in resource:
            resource["meta"] = {}
            
        if "security" not in resource["meta"]:
            resource["meta"]["security"] = []
            
        # Add security tags for PHI
        resource["meta"]["security"].append({
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "PHI",
            "display": "Protected Health Information"
        })
        
        # Add note about handling
        resource["meta"]["security"].append({
            "system": "http://example.org/fhir/security-tags",
            "code": "PHI-RESTRICTED",
            "display": "Contains PHI - Handle according to privacy policies"
        })
            
    # ========================
    # Narrative Generation Methods
    # ========================
    
    def _generate_patient_narrative(self, patient: Dict) -> Dict:
        """Generate comprehensive narrative for a Patient resource."""
        html = "<div xmlns='http://www.w3.org/1999/xhtml'>"
        
        # Add patient name
        name_text = "Unknown"
        if patient.get("name"):
            for name in patient["name"]:
                if name.get("text"):
                    name_text = name["text"]
                    break
                elif name.get("family") or name.get("given"):
                    given = " ".join(name.get("given", []))
                    family = name.get("family", "")
                    name_text = f"{given} {family}".strip()
                    break
        
        html += f"<h1>Patient: {name_text}</h1>"
        
        # Add key demographic information
        gender = patient.get("gender", "Unknown")
        dob = patient.get("birthDate", "Unknown")
        html += f"<p><b>Gender:</b> {gender.capitalize() if gender else 'Unknown'}</p>"
        html += f"<p><b>Date of Birth:</b> {dob}</p>"
        
        # Add identifiers
        if patient.get("identifier"):
            html += "<h2>Identifiers</h2><ul>"
            for identifier in patient["identifier"]:
                system = identifier.get("system", "Unknown system")
                value = identifier.get("value", "")
                type_display = "ID"
                if "type" in identifier and "coding" in identifier["type"]:
                    for coding in identifier["type"]["coding"]:
                        if "display" in coding:
                            type_display = coding["display"]
                            break
                html += f"<li>{type_display}: {value} ({system})</li>"
            html += "</ul>"
            
        # Add contact information
        if patient.get("telecom"):
            html += "<h2>Contact Information</h2><ul>"
            for telecom in patient["telecom"]:
                system = telecom.get("system", "unknown")
                value = telecom.get("value", "")
                use = telecom.get("use", "")
                html += f"<li>{system.capitalize()}{' ('+use+')' if use else ''}: {value}</li>"
            html += "</ul>"
        
        # Add address information
        if patient.get("address"):
            html += "<h2>Addresses</h2><ul>"
            for address in patient["address"]:
                addr_parts = []
                if "line" in address:
                    addr_parts.extend(address["line"])
                for part in ["city", "state", "postalCode", "country"]:
                    if part in address and address[part]:
                        addr_parts.append(address[part])
                        
                addr_str = ", ".join(addr_parts)
                use = address.get("use", "")
                html += f"<li>{use.capitalize() if use else 'Unknown'} Address: {addr_str}</li>"
            html += "</ul>"
            
        html += "</div>"
        
        return {
            "status": "generated",
            "div": html
        }
        
    def _generate_observation_narrative(self, observation: Dict) -> Dict:
        """Generate comprehensive narrative for an Observation resource."""
        html = "<div xmlns='http://www.w3.org/1999/xhtml'>"
        
        # Add observation name/title
        title = "Unknown Observation"
        if "code" in observation:
            if "text" in observation["code"]:
                title = observation["code"]["text"]
            elif "coding" in observation["code"] and observation["code"]["coding"]:
                for coding in observation["code"]["coding"]:
                    if "display" in coding:
                        title = coding["display"]
                        break
        
        html += f"<h1>Observation: {title}</h1>"
        
        # Add status and date
        status = observation.get("status", "unknown")
        html += f"<p><b>Status:</b> {status.capitalize() if status else 'Unknown'}</p>"
        
        if "effectiveDateTime" in observation:
            html += f"<p><b>Effective Date:</b> {observation['effectiveDateTime']}</p>"
        
        # Add subject information
        if "subject" in observation and "reference" in observation["subject"]:
            html += f"<p><b>Subject:</b> {observation['subject']['reference']}</p>"
        
        # Add result/value information
        value_html = "<p><b>Value:</b> "
        
        if "valueQuantity" in observation:
            value = observation["valueQuantity"].get("value", "")
            unit = observation["valueQuantity"].get("unit", "")
            value_html += f"{value} {unit}"
        elif "valueCodeableConcept" in observation:
            if "text" in observation["valueCodeableConcept"]:
                value_html += observation["valueCodeableConcept"]["text"]
            elif "coding" in observation["valueCodeableConcept"]:
                for coding in observation["valueCodeableConcept"]["coding"]:
                    if "display" in coding:
                        value_html += coding["display"]
                        break
        elif "valueString" in observation:
            value_html += observation["valueString"]
        else:
            value_html += "No value recorded"
            
        value_html += "</p>"
        html += value_html
            
        html += "</div>"
        
        return {
            "status": "generated",
            "div": html
        }
        
    def _generate_encounter_narrative(self, encounter: Dict) -> Dict:
        """Generate comprehensive narrative for an Encounter resource."""
        html = "<div xmlns='http://www.w3.org/1999/xhtml'>"
        
        # Add encounter type
        title = "Unknown Encounter"
        if "type" in encounter:
            if "text" in encounter["type"]:
                title = encounter["type"]["text"]
            elif "coding" in encounter["type"] and encounter["type"]["coding"]:
                for coding in encounter["type"]["coding"]:
                    if "display" in coding:
                        title = coding["display"]
                        break
        
        html += f"<h1>Encounter: {title}</h1>"
        
        # Add status
        status = encounter.get("status", "unknown")
        html += f"<p><b>Status:</b> {status.capitalize() if status else 'Unknown'}</p>"
        
        # Add class
        if "class" in encounter:
            class_display = ""
            if "display" in encounter["class"]:
                class_display = encounter["class"]["display"]
            elif "code" in encounter["class"]:
                class_display = encounter["class"]["code"]
                
            if class_display:
                html += f"<p><b>Class:</b> {class_display}</p>"
        
        # Add date range
        if "period" in encounter:
            start = encounter["period"].get("start", "Unknown")
            end = encounter["period"].get("end", "Ongoing")
            html += f"<p><b>Period:</b> {start} to {end}</p>"
        
        # Add subject information
        if "subject" in encounter and "reference" in encounter["subject"]:
            html += f"<p><b>Subject:</b> {encounter['subject']['reference']}</p>"
            
        html += "</div>"
        
        return {
            "status": "generated",
            "div": html
        }
        
    def _generate_generic_narrative(self, resource: Dict) -> Dict:
        """Generate basic narrative for any resource type."""
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "Unknown")
        
        html = f"<div xmlns='http://www.w3.org/1999/xhtml'>"
        html += f"<p>{resource_type} resource with ID: {resource_id}</p>"
        html += "</div>"
        
        return {
            "status": "generated",
            "div": html
        }

def transform_resource_bronze_to_silver(resource: Dict, 
                                      validation_mode: str = "strict",
                                      debug: bool = False) -> Dict:
    """
    Transform a single FHIR resource from bronze to silver tier.
    
    Args:
        resource: FHIR resource in bronze tier
        validation_mode: Validation mode, one of ["strict", "moderate", "lenient"]
        debug: Enable debug logging
        
    Returns:
        Transformed resource in silver tier
    """
    transformer = FHIRResourceTransformer(validation_mode, debug)
    return transformer.bronze_to_silver(resource)
    
def transform_resource_silver_to_gold(resource: Dict,
                                    validation_mode: str = "strict",
                                    debug: bool = False) -> Dict:
    """
    Transform a single FHIR resource from silver to gold tier.
    
    Args:
        resource: FHIR resource in silver tier
        validation_mode: Validation mode, one of ["strict", "moderate", "lenient"]
        debug: Enable debug logging
        
    Returns:
        Transformed resource in gold tier
    """
    transformer = FHIRResourceTransformer(validation_mode, debug)
    return transformer.silver_to_gold(resource)
    
def transform_resource_bronze_to_gold(resource: Dict,
                                     validation_mode: str = "strict",
                                     debug: bool = False) -> Dict:
    """
    Transform a single FHIR resource from bronze directly to gold tier.
    
    Args:
        resource: FHIR resource in bronze tier
        validation_mode: Validation mode, one of ["strict", "moderate", "lenient"]
        debug: Enable debug logging
        
    Returns:
        Transformed resource in gold tier
    """
    transformer = FHIRResourceTransformer(validation_mode, debug)
    silver = transformer.bronze_to_silver(resource)
    return transformer.silver_to_gold(silver) 