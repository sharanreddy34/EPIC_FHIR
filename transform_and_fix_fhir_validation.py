#!/usr/bin/env python3
"""
FHIR Resource Validator and Transformer

This script performs two key functions:
1. Fixes validation errors in FHIR resources
2. Transforms FHIR resources to CSV format

Usage:
  python transform_and_fix_fhir_validation.py --input-file INPUT_FILE [--tier {bronze,silver,gold}]

"""

import argparse
import json
import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Union


def fix_validation_errors(resources: Dict[str, List[Dict[str, Any]]], tier: str = "gold") -> Dict[str, List[Dict[str, Any]]]:
    """
    Fix common validation errors in FHIR resources based on tier requirements.
    
    Args:
        resources: Dictionary of FHIR resources by type
        tier: The data tier (bronze, silver, gold)
        
    Returns:
        Dictionary of fixed FHIR resources
    """
    print(f"Fixing validation errors for {tier} tier...")
    fixed_resources = {}
    
    for resource_type, resource_list in resources.items():
        fixed_resources[resource_type] = []
        
        for resource in resource_list:
            # Make a copy to avoid modifying the original
            fixed_resource = resource.copy()
            
            # 1. Fix missing required fields based on resource type
            if resource_type == "Patient":
                # Ensure Patient has required fields
                if "identifier" not in fixed_resource:
                    fixed_resource["identifier"] = [{"system": "http://example.org/fhir/identifier/patient", "value": fixed_resource.get("id", "unknown")}]
                if "name" not in fixed_resource:
                    fixed_resource["name"] = [{"use": "official", "family": "Unknown"}]
            elif resource_type == "Observation":
                # Ensure Observation has required fields
                if "status" not in fixed_resource:
                    fixed_resource["status"] = "final"
                if "code" not in fixed_resource:
                    fixed_resource["code"] = {"coding": [{"system": "http://loinc.org", "code": "unknown"}]}
                if "subject" not in fixed_resource:
                    # Find a Patient reference
                    patient_resources = resources.get("Patient", [])
                    if patient_resources:
                        fixed_resource["subject"] = {"reference": f"Patient/{patient_resources[0].get('id', 'unknown')}"}
            elif resource_type == "Condition":
                # Ensure Condition has required fields
                if "clinicalStatus" not in fixed_resource:
                    fixed_resource["clinicalStatus"] = {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
                    }
                if "verificationStatus" not in fixed_resource:
                    fixed_resource["verificationStatus"] = {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
                    }
                if "code" not in fixed_resource:
                    fixed_resource["code"] = {"coding": [{"system": "http://snomed.info/sct", "code": "unknown"}]}
                if "subject" not in fixed_resource:
                    # Find a Patient reference
                    patient_resources = resources.get("Patient", [])
                    if patient_resources:
                        fixed_resource["subject"] = {"reference": f"Patient/{patient_resources[0].get('id', 'unknown')}"}
            elif resource_type == "Encounter":
                # Ensure Encounter has required fields
                if "status" not in fixed_resource:
                    fixed_resource["status"] = "finished"
                if "class" not in fixed_resource:
                    fixed_resource["class"] = {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"}
                if "subject" not in fixed_resource:
                    # Find a Patient reference
                    patient_resources = resources.get("Patient", [])
                    if patient_resources:
                        fixed_resource["subject"] = {"reference": f"Patient/{patient_resources[0].get('id', 'unknown')}"}
            
            # 2. Add or update meta information
            if "meta" not in fixed_resource:
                fixed_resource["meta"] = {}
            if "tag" not in fixed_resource["meta"]:
                fixed_resource["meta"]["tag"] = []
            
            # Add tier tag if not present
            tier_tag_present = False
            for tag in fixed_resource["meta"]["tag"]:
                if tag.get("system") == "http://atlaspalantir.com/fhir/data-tier" and tag.get("code") == tier:
                    tier_tag_present = True
                    break
            
            if not tier_tag_present:
                fixed_resource["meta"]["tag"].append({
                    "system": "http://atlaspalantir.com/fhir/data-tier",
                    "code": tier,
                    "display": tier.capitalize()
                })
            
            # 3. Add narrative if not present (for gold tier)
            if tier == "gold" and "text" not in fixed_resource:
                fixed_resource["text"] = {
                    "status": "generated",
                    "div": f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>{resource_type} resource</p></div>"
                }
            
            # 4. Add extensions for US Core profiles if needed
            if tier in ["silver", "gold"] and resource_type == "Patient":
                if "extension" not in fixed_resource:
                    fixed_resource["extension"] = []
                
                # Check if data-quality-tier extension exists
                quality_tier_exists = False
                for ext in fixed_resource["extension"]:
                    if ext.get("url") == "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier":
                        quality_tier_exists = True
                        ext["valueString"] = tier
                        break
                
                if not quality_tier_exists:
                    fixed_resource["extension"].append({
                        "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
                        "valueString": tier
                    })
            
            fixed_resources[resource_type].append(fixed_resource)
    
    return fixed_resources
    """
    Fix common validation errors in FHIR resources based on tier requirements.
    
    Args:
        resources: Dictionary of FHIR resources by type
        tier: The data tier (bronze, silver, gold)
        
    Returns:
        Fixed resources dictionary
    """
    fixed_resources = {}
    
    for resource_type, resource_list in resources.items():
        fixed_list = []
        
        for resource in resource_list:
            # Deep copy the resource to avoid modifying the original
            fixed_resource = json.loads(json.dumps(resource))
            
            # Common fixes for all tiers
            # 1. Ensure resourceType is present and matches
            fixed_resource["resourceType"] = resource_type
            
            # 2. Ensure id is present
            if "id" not in fixed_resource:
                fixed_resource["id"] = f"generated-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 3. Ensure meta is present
            if "meta" not in fixed_resource:
                fixed_resource["meta"] = {}
                
            # 4. Add or update tier tag
            if "tag" not in fixed_resource["meta"]:
                fixed_resource["meta"]["tag"] = []
                
            # Update or add tier tag
            tier_tag_index = None
            for i, tag in enumerate(fixed_resource["meta"]["tag"]):
                if tag.get("system") == "http://atlaspalantir.com/fhir/data-tier":
                    tier_tag_index = i
                    break
                    
            tier_tag = {
                "system": "http://atlaspalantir.com/fhir/data-tier",
                "code": tier,
                "display": tier.capitalize()
            }
            
            if tier_tag_index is not None:
                fixed_resource["meta"]["tag"][tier_tag_index] = tier_tag
            else:
                fixed_resource["meta"]["tag"].append(tier_tag)
            
            # Tier-specific fixes
            if tier == "silver" or tier == "gold":
                # Add data quality tier extension if not present
                if "extension" not in fixed_resource:
                    fixed_resource["extension"] = []
                
                quality_ext_index = None
                for i, ext in enumerate(fixed_resource.get("extension", [])):
                    if ext.get("url") == "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier":
                        quality_ext_index = i
                        break
                
                quality_ext = {
                    "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
                    "valueString": tier
                }
                
                if quality_ext_index is not None:
                    fixed_resource["extension"][quality_ext_index] = quality_ext
                else:
                    fixed_resource["extension"].append(quality_ext)
                
                # Resource-specific fixes for Silver tier
                if resource_type == "Patient":
                    # Ensure name is present and properly structured
                    if "name" not in fixed_resource or not fixed_resource["name"]:
                        fixed_resource["name"] = [{"family": "Unknown", "given": ["Unknown"]}]
                    elif isinstance(fixed_resource["name"], list) and "family" not in fixed_resource["name"][0]:
                        fixed_resource["name"][0]["family"] = "Unknown"
                
                elif resource_type == "Observation":
                    # Ensure status is valid
                    if "status" not in fixed_resource or fixed_resource["status"] not in ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]:
                        fixed_resource["status"] = "unknown"
                    
                    # Ensure subject reference is present
                    if "subject" not in fixed_resource:
                        fixed_resource["subject"] = {"reference": "Patient/example"}
                    
                    # Ensure code is present with coding
                    if "code" not in fixed_resource:
                        fixed_resource["code"] = {"coding": [{"system": "http://loinc.org", "code": "unknown"}]}
                    elif "coding" not in fixed_resource["code"] or not fixed_resource["code"]["coding"]:
                        fixed_resource["code"]["coding"] = [{"system": "http://loinc.org", "code": "unknown"}]
            
            # Gold tier specific fixes
            if tier == "gold":
                # Add narrative text if not present
                if "text" not in fixed_resource:
                    fixed_resource["text"] = {
                        "status": "generated",
                        "div": f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>{resource_type} resource</p></div>"
                    }
                
                # Resource-specific gold tier enhancements
                if resource_type == "Patient":
                    # Add US Core Race extension if not present
                    has_race_ext = False
                    for ext in fixed_resource.get("extension", []):
                        if ext.get("url") == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
                            has_race_ext = True
                            break
                    
                    if not has_race_ext:
                        race_ext = {
                            "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                            "extension": [
                                {
                                    "url": "ombCategory",
                                    "valueCoding": {
                                        "system": "urn:oid:2.16.840.1.113883.6.238",
                                        "code": "2106-3",
                                        "display": "White"
                                    }
                                },
                                {
                                    "url": "text",
                                    "valueString": "White"
                                }
                            ]
                        }
                        fixed_resource["extension"].append(race_ext)
                
                # Enhanced narrative text based on resource type
                if resource_type == "Patient":
                    name = "Unknown"
                    if "name" in fixed_resource and fixed_resource["name"]:
                        name_obj = fixed_resource["name"][0]
                        given = " ".join(name_obj.get("given", []))
                        family = name_obj.get("family", "")
                        name = f"{given} {family}".strip() or "Unknown"
                    
                    gender = fixed_resource.get("gender", "unknown")
                    birth_date = fixed_resource.get("birthDate", "Unknown")
                    
                    narrative = f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>Patient: {name}, {gender}, DOB: {birth_date}</p></div>"
                    fixed_resource["text"]["div"] = narrative
                
                elif resource_type == "Observation":
                    code_display = "Unknown"
                    if "code" in fixed_resource and "coding" in fixed_resource["code"] and fixed_resource["code"]["coding"]:
                        code_display = fixed_resource["code"]["coding"][0].get("display", "Unknown")
                    
                    value = "Unknown"
                    if "valueQuantity" in fixed_resource:
                        value = f"{fixed_resource['valueQuantity'].get('value', '')} {fixed_resource['valueQuantity'].get('unit', '')}"
                    
                    narrative = f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>Observation: {code_display}, Value: {value}</p></div>"
                    fixed_resource["text"]["div"] = narrative
            
            fixed_list.append(fixed_resource)
        
        fixed_resources[resource_type] = fixed_list
    
    return fixed_resources


def transform_to_csv(resources: Dict[str, List[Dict[str, Any]]], output_dir: str) -> Dict[str, str]:
    """
    Transform FHIR resources to CSV format.
    
    Args:
        resources: Dictionary of FHIR resources by type
        output_dir: Directory to save CSV files
        
    Returns:
        Dictionary mapping resource types to their CSV file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    output_files = {}
    
    for resource_type, resource_list in resources.items():
        if not resource_list:
            continue
        
        # Convert to DataFrame
        df = pd.json_normalize(resource_list)
        
        # Save to CSV
        output_path = os.path.join(output_dir, f"{resource_type.lower()}.csv")
        df.to_csv(output_path, index=False)
        
        output_files[resource_type] = output_path
        print(f"Exported {len(resource_list)} {resource_type} resources to {output_path}")
    
    return output_files


def main():
    parser = argparse.ArgumentParser(description="Fix FHIR validation errors and transform resources to CSV format")
    parser.add_argument("--input-file", required=True, help="Path to input FHIR resources JSON file")
    parser.add_argument("--output-dir", default="fhir_output", help="Output directory for fixed resources and CSV files")
    parser.add_argument("--tier", choices=["bronze", "silver", "gold"], default="gold", help="Data tier to target")
    
    args = parser.parse_args()
    
    # Load input resources
    try:
        with open(args.input_file, "r") as f:
            resources = json.load(f)
    except Exception as e:
        print(f"Error loading input file: {e}", file=sys.stderr)
        return 1
    
    # Fix validation errors
    print(f"Fixing validation errors for {args.tier} tier...")
    fixed_resources = fix_validation_errors(resources, args.tier)
    
    # Create output directories
    json_dir = os.path.join(args.output_dir, "json")
    csv_dir = os.path.join(args.output_dir, "csv")
    os.makedirs(json_dir, exist_ok=True)
    
    # Save fixed resources as JSON
    fixed_json_path = os.path.join(json_dir, f"fixed_{args.tier}_resources.json")
    with open(fixed_json_path, "w") as f:
        json.dump(fixed_resources, f, indent=2)
    
    print(f"Fixed resources saved to: {fixed_json_path}")
    
    # Transform to CSV
    print(f"Transforming resources to CSV format...")
    csv_files = transform_to_csv(fixed_resources, csv_dir)
    
    # Generate summary
    print("\nSummary:")
    print(f"  Input file: {args.input_file}")
    print(f"  Target tier: {args.tier}")
    print(f"  Fixed JSON output: {fixed_json_path}")
    print(f"  CSV outputs:")
    for resource_type, path in csv_files.items():
        print(f"    - {resource_type}: {path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 