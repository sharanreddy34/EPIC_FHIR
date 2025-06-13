"""
Patient narrative generator for LLM ingestion.

This module provides functionality to create comprehensive patient narratives
by consolidating data from multiple FHIR resources related to a patient.
These narratives are structured for optimal LLM processing.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from epic_fhir_integration.utils.logging import get_logger

# Lazy import to avoid hard dependency on FHIRClient
# This lets this module be used without the full Foundry stack
FHIRClient = Any  # Type alias for static type checking

logger = get_logger(__name__)


def fetch_patient_complete(
    client: Any,  # Use Any instead of FHIRClient to avoid hard dependency
    patient_id: str,
    include_resources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Fetch a comprehensive view of a patient including related resources.
    
    This function fetches a Patient resource and all related resources
    specified in include_resources, using _include and _revinclude parameters
    to optimize the number of API calls.
    
    Args:
        client: The FHIR client to use
        patient_id: The patient ID to fetch
        include_resources: List of resource types to include. If None, defaults
                          to a comprehensive set of clinically relevant resources
        
    Returns:
        Dictionary with patient data and all related resources
    """
    if include_resources is None:
        include_resources = [
            "Observation", 
            "Condition", 
            "MedicationRequest", 
            "DiagnosticReport", 
            "Procedure", 
            "Encounter", 
            "DocumentReference",
            "AllergyIntolerance",
            "Immunization"
        ]
    
    # Get the patient resource first
    patient = client.get_resource("Patient", patient_id)
    
    # Build _revinclude parameters for each resource type
    # These tell the server to include resources that reference this patient
    revinclude_params = [f"{resource}:subject" for resource in include_resources]
    revinclude_params.extend([f"{resource}:patient" for resource in include_resources])
    
    # Now fetch the patient again with _revinclude to get related resources
    # This is more efficient than separate queries for each resource type
    params = {
        "_id": patient_id,
        "_revinclude": revinclude_params
    }
    
    # Get the bundle with all related resources
    bundle = client.get_resource("Patient", params=params)
    
    # Extract resources by type
    resources_by_type = {
        "Patient": [patient]
    }
    
    if "entry" in bundle:
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            
            # Skip the patient resource (we already have it)
            if resource_type == "Patient" and resource.get("id") == patient_id:
                continue
                
            # Add to resources by type
            if resource_type not in resources_by_type:
                resources_by_type[resource_type] = []
            resources_by_type[resource_type].append(resource)
    
    # For certain resource types, we may need to do additional queries
    # DiagnosticReport may have results that weren't included
    if "DiagnosticReport" in resources_by_type:
        _fetch_diagnostic_report_results(client, resources_by_type)
    
    # DocumentReference may have content that wasn't included
    if "DocumentReference" in resources_by_type:
        _fetch_document_content(client, resources_by_type)
    
    return resources_by_type


def _fetch_diagnostic_report_results(client: Any, resources_by_type: Dict[str, List[Dict[str, Any]]]):
    """Fetch results referenced by DiagnosticReport resources."""
    # Find all result references
    result_refs = set()
    for report in resources_by_type.get("DiagnosticReport", []):
        for result in report.get("result", []):
            ref = result.get("reference")
            if ref and ref.startswith("Observation/"):
                result_refs.add(ref.split("/")[1])  # Extract the ID
    
    # Check which ones we already have
    existing_obs_ids = {obs.get("id") for obs in resources_by_type.get("Observation", [])}
    missing_obs_ids = result_refs - existing_obs_ids
    
    # Fetch missing observations
    if missing_obs_ids:
        logger.info(f"Fetching {len(missing_obs_ids)} additional Observations referenced by DiagnosticReports")
        observations = client.batch_get_resources("Observation", list(missing_obs_ids))
        
        # Add to resources_by_type
        if "Observation" not in resources_by_type:
            resources_by_type["Observation"] = []
        resources_by_type["Observation"].extend(observations.values())


def _fetch_document_content(client: Any, resources_by_type: Dict[str, List[Dict[str, Any]]]):
    """Fetch content referenced by DocumentReference resources."""
    # This would handle fetching Binary resources or other content
    # Not implemented in this version as it depends on the specific FHIR server
    pass


def generate_patient_narrative(resources_by_type: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Generate a comprehensive patient narrative suitable for LLM ingestion.
    
    Args:
        resources_by_type: Dictionary mapping resource types to lists of resources
        
    Returns:
        Structured text narrative about the patient
    """
    narrative = []
    
    # Patient demographics
    patients = resources_by_type.get("Patient", [])
    if not patients:
        return "No patient data available."
    
    patient = patients[0]  # Take the first patient
    
    # Basic demographics
    narrative.append("# PATIENT SUMMARY")
    narrative.append("")
    
    # Name
    name = patient.get("name", [{}])[0]
    given = " ".join(name.get("given", ["Unknown"]))
    family = name.get("family", "Unknown")
    narrative.append(f"Name: {given} {family}")
    
    # Other demographics
    narrative.append(f"Gender: {patient.get('gender', 'Unknown')}")
    narrative.append(f"Birth Date: {patient.get('birthDate', 'Unknown')}")
    
    # Calculate age if birth date is available
    if "birthDate" in patient:
        try:
            birth_date = datetime.strptime(patient["birthDate"], "%Y-%m-%d")
            age = (datetime.now() - birth_date).days // 365
            narrative.append(f"Age: {age} years")
        except (ValueError, TypeError):
            pass
    
    narrative.append("")
    
    # Conditions (Problems)
    conditions = resources_by_type.get("Condition", [])
    if conditions:
        narrative.append("## PROBLEMS")
        narrative.append("")
        
        for condition in sorted(
            conditions, 
            key=lambda c: c.get("recordedDate", ""), 
            reverse=True
        ):
            status = condition.get("clinicalStatus", {}).get("coding", [{}])[0].get("display", "Unknown")
            code_display = condition.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Condition")
            onset = condition.get("onsetDateTime", condition.get("recordedDate", "Unknown"))
            narrative.append(f"- {code_display} (Status: {status}, Onset: {onset})")
        
        narrative.append("")
    
    # Allergies
    allergies = resources_by_type.get("AllergyIntolerance", [])
    if allergies:
        narrative.append("## ALLERGIES")
        narrative.append("")
        
        for allergy in allergies:
            substance = allergy.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Substance")
            severity = allergy.get("reaction", [{}])[0].get("severity", "Unknown")
            manifestation = allergy.get("reaction", [{}])[0].get("manifestation", [{}])[0].get("coding", [{}])[0].get("display", "Unknown")
            narrative.append(f"- {substance} (Severity: {severity}, Manifestation: {manifestation})")
        
        narrative.append("")
    
    # Medications
    medications = resources_by_type.get("MedicationRequest", [])
    if medications:
        narrative.append("## MEDICATIONS")
        narrative.append("")
        
        for med in sorted(
            medications, 
            key=lambda m: m.get("authoredOn", ""), 
            reverse=True
        ):
            med_display = med.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Unknown Medication")
            status = med.get("status", "Unknown")
            dosage = med.get("dosageInstruction", [{}])[0].get("text", "No dosage information")
            date = med.get("authoredOn", "Unknown date")
            narrative.append(f"- {med_display} ({status}, {dosage}, Prescribed: {date})")
        
        narrative.append("")
    
    # Diagnostic Reports (including Echo/Ultrasound)
    reports = resources_by_type.get("DiagnosticReport", [])
    if reports:
        # Separate echo/ultrasound reports from others
        echo_reports = []
        other_reports = []
        
        for report in reports:
            category_codings = report.get("category", [{}])[0].get("coding", [])
            code_codings = report.get("code", {}).get("coding", [])
            
            # Check if this is an echo/ultrasound report
            is_echo = False
            for coding in category_codings + code_codings:
                code = coding.get("code", "")
                system = coding.get("system", "")
                display = coding.get("display", "").lower()
                
                if (
                    "echo" in display or 
                    "ultrasound" in display or 
                    "ultrasonography" in display or
                    (system == "http://loinc.org" and code in ["45030-7", "34140-4", "34141-2"])
                ):
                    is_echo = True
                    break
            
            if is_echo:
                echo_reports.append(report)
            else:
                other_reports.append(report)
        
        # Add echo/ultrasound section if relevant
        if echo_reports:
            narrative.append("## ECHOCARDIOGRAPHY / ULTRASOUND REPORTS")
            narrative.append("")
            
            for report in sorted(
                echo_reports, 
                key=lambda r: r.get("effectiveDateTime", ""), 
                reverse=True
            ):
                code_display = report.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Report")
                date = report.get("effectiveDateTime", "Unknown date")
                status = report.get("status", "Unknown")
                
                narrative.append(f"### {code_display} ({date}, Status: {status})")
                narrative.append("")
                
                # Add conclusion if available
                conclusion = report.get("conclusion", "")
                if conclusion:
                    narrative.append("Conclusion:")
                    narrative.append(conclusion)
                    narrative.append("")
                
                # Add any observations associated with this report
                if "result" in report:
                    result_refs = report.get("result", [])
                    if result_refs:
                        narrative.append("Results:")
                        
                        for ref in result_refs:
                            ref_id = ref.get("reference", "").split("/")[1] if "/" in ref.get("reference", "") else ""
                            
                            # Find the observation
                            for obs in resources_by_type.get("Observation", []):
                                if obs.get("id") == ref_id:
                                    value = None
                                    if "valueQuantity" in obs:
                                        value = f"{obs['valueQuantity'].get('value', '')} {obs['valueQuantity'].get('unit', '')}"
                                    elif "valueString" in obs:
                                        value = obs["valueString"]
                                    elif "valueCodeableConcept" in obs:
                                        value = obs["valueCodeableConcept"].get("coding", [{}])[0].get("display", "")
                                    
                                    if value:
                                        code_display = obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                                        narrative.append(f"- {code_display}: {value}")
                        
                        narrative.append("")
                
                # Add presented form if available
                if "presentedForm" in report:
                    for form in report.get("presentedForm", []):
                        content_type = form.get("contentType", "")
                        if content_type == "text/plain" and "data" in form:
                            try:
                                import base64
                                text = base64.b64decode(form["data"]).decode("utf-8")
                                narrative.append("Report Text:")
                                narrative.append("```")
                                narrative.append(text)
                                narrative.append("```")
                                narrative.append("")
                            except Exception as e:
                                narrative.append(f"Error decoding report text: {str(e)}")
                                narrative.append("")
        
        # Add other diagnostic reports
        if other_reports:
            narrative.append("## OTHER DIAGNOSTIC REPORTS")
            narrative.append("")
            
            for report in sorted(
                other_reports, 
                key=lambda r: r.get("effectiveDateTime", ""), 
                reverse=True
            ):
                code_display = report.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Report")
                date = report.get("effectiveDateTime", "Unknown date")
                status = report.get("status", "Unknown")
                
                narrative.append(f"- {code_display} ({date}, Status: {status})")
                
                # Add brief conclusion if available
                conclusion = report.get("conclusion", "")
                if conclusion and len(conclusion) < 100:
                    narrative.append(f"  Conclusion: {conclusion}")
            
            narrative.append("")
    
    # Labs and vital signs
    observations = resources_by_type.get("Observation", [])
    if observations:
        # Split into vitals and labs
        vitals = []
        labs = []
        
        for obs in observations:
            category = obs.get("category", [{}])[0].get("coding", [{}])[0].get("code", "")
            
            if category == "vital-signs":
                vitals.append(obs)
            elif category == "laboratory":
                labs.append(obs)
        
        # Add vitals section
        if vitals:
            narrative.append("## VITAL SIGNS")
            narrative.append("")
            
            # Group by date
            vitals_by_date = {}
            for vital in vitals:
                date = vital.get("effectiveDateTime", "Unknown")
                if date not in vitals_by_date:
                    vitals_by_date[date] = []
                vitals_by_date[date].append(vital)
            
            # Output vitals by date
            for date in sorted(vitals_by_date.keys(), reverse=True)[:5]:  # Show last 5 dates
                narrative.append(f"### {date}")
                
                for vital in vitals_by_date[date]:
                    code_display = vital.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                    
                    value = None
                    if "valueQuantity" in vital:
                        value = f"{vital['valueQuantity'].get('value', '')} {vital['valueQuantity'].get('unit', '')}"
                    elif "valueString" in vital:
                        value = vital["valueString"]
                    elif "valueCodeableConcept" in vital:
                        value = vital["valueCodeableConcept"].get("coding", [{}])[0].get("display", "")
                    
                    if value:
                        narrative.append(f"- {code_display}: {value}")
                
                narrative.append("")
        
        # Add labs section
        if labs:
            narrative.append("## LABORATORY RESULTS")
            narrative.append("")
            
            # Group by date
            labs_by_date = {}
            for lab in labs:
                date = lab.get("effectiveDateTime", "Unknown")
                if date not in labs_by_date:
                    labs_by_date[date] = []
                labs_by_date[date].append(lab)
            
            # Output labs by date
            for date in sorted(labs_by_date.keys(), reverse=True)[:10]:  # Show last 10 dates
                narrative.append(f"### {date}")
                
                for lab in labs_by_date[date]:
                    code_display = lab.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                    
                    value = None
                    if "valueQuantity" in lab:
                        value = f"{lab['valueQuantity'].get('value', '')} {lab['valueQuantity'].get('unit', '')}"
                    elif "valueString" in lab:
                        value = lab["valueString"]
                    elif "valueCodeableConcept" in lab:
                        value = lab["valueCodeableConcept"].get("coding", [{}])[0].get("display", "")
                    
                    reference_range = lab.get("referenceRange", [{}])[0]
                    ref_range_text = ""
                    if "low" in reference_range and "high" in reference_range:
                        ref_range_text = f" (Reference: {reference_range['low'].get('value', '')}-{reference_range['high'].get('value', '')} {reference_range['high'].get('unit', '')})"
                    
                    if value:
                        narrative.append(f"- {code_display}: {value}{ref_range_text}")
                
                narrative.append("")
    
    # Clinical notes from DocumentReference
    documents = resources_by_type.get("DocumentReference", [])
    if documents:
        # Filter for clinical notes
        clinical_notes = []
        
        for doc in documents:
            doc_type = doc.get("type", {}).get("coding", [{}])[0].get("display", "").lower()
            if "note" in doc_type or "summary" in doc_type or "report" in doc_type:
                clinical_notes.append(doc)
        
        if clinical_notes:
            narrative.append("## CLINICAL NOTES")
            narrative.append("")
            
            for note in sorted(
                clinical_notes, 
                key=lambda d: d.get("date", ""), 
                reverse=True
            )[:5]:  # Show last 5 notes
                type_display = note.get("type", {}).get("coding", [{}])[0].get("display", "Unknown Note")
                date = note.get("date", "Unknown date")
                
                narrative.append(f"### {type_display} ({date})")
                narrative.append("")
                
                # Extract content
                content_found = False
                for content in note.get("content", []):
                    attachment = content.get("attachment", {})
                    if attachment.get("contentType") == "text/plain" and "data" in attachment:
                        try:
                            import base64
                            text = base64.b64decode(attachment["data"]).decode("utf-8")
                            narrative.append(text)
                            content_found = True
                        except Exception as e:
                            narrative.append(f"Error decoding note content: {str(e)}")
                
                if not content_found:
                    narrative.append("Content not available in this format.")
                
                narrative.append("")
    
    return "\n".join(narrative)


def generate_patient_narratives_spark(
    spark: SparkSession,
    patient_dataset_path: str,
    output_dataset_path: str,
    max_patients: int = 100,
    client=None
) -> None:
    """
    Generate patient narratives for multiple patients using Spark.
    
    This function reads patient data from a Bronze dataset, generates
    comprehensive narratives for each patient, and writes the results
    to a new dataset.
    
    Args:
        spark: Spark session
        patient_dataset_path: Path to the patient dataset
        output_dataset_path: Path to write the narratives
        max_patients: Maximum number of patients to process
        client: Optional FHIR client. If None, one will be created
    """
    # Read patient dataset
    patients_df = spark.read.format("delta").load(patient_dataset_path)
    
    # Limit to a subset of patients for processing
    limited_df = patients_df.limit(max_patients)
    
    # Extract patient IDs
    patient_ids = [row.resource_id for row in limited_df.select("resource_id").collect()]
    
    # Define a UDF to generate narrative for each patient
    def generate_narrative_udf(patient_id, json_data):
        try:
            # Import inside the function to avoid hard dependency
            if client is None:
                from epic_fhir_integration.api_clients.fhir_client import create_fhir_client
                local_client = create_fhir_client()
            else:
                local_client = client
            
            # Parse patient data
            patient_data = json.loads(json_data)
            
            # Get comprehensive patient data
            resources_by_type = fetch_patient_complete(local_client, patient_id)
            
            # Generate narrative
            narrative = generate_patient_narrative(resources_by_type)
            
            return narrative
        except Exception as e:
            logger.error(f"Error generating narrative for patient {patient_id}: {str(e)}")
            return f"Error generating narrative: {str(e)}"
    
    # Register the UDF
    generate_narrative = F.udf(generate_narrative_udf)
    
    # Apply the UDF
    narrative_df = limited_df.withColumn(
        "narrative",
        generate_narrative(F.col("resource_id"), F.col("json_data"))
    )
    
    # Select relevant columns
    result_df = narrative_df.select(
        "resource_id",
        "narrative",
        F.current_timestamp().alias("generated_at")
    )
    
    # Write results
    result_df.write.format("delta").mode("overwrite").save(output_dataset_path)
    
    logger.info(f"Generated narratives for {result_df.count()} patients") 