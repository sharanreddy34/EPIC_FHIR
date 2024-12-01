#!/usr/bin/env python3
"""
Prototype for testing FHIR-PYrate for data science workflows.

This prototype demonstrates how FHIR-PYrate can be used to extract, transform, 
and analyze FHIR data for machine learning and data science applications.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import FHIR-PYrate (will fail if not installed)
try:
    from fhirpyrate import Dataset, FhirPyrateBuilder
    from fhirpyrate.transformers import Flatten, Standardize, Filter
    FHIR_PYRATE_AVAILABLE = True
except ImportError:
    FHIR_PYRATE_AVAILABLE = False
    print("FHIR-PYrate package not installed. Run: pip install fhir-pyrate")


# Example FHIR resources for testing
SAMPLE_RESOURCES_DIR = Path("./sample_data")


def create_sample_data():
    """Create sample FHIR data for testing."""
    
    # Create directory if it doesn't exist
    os.makedirs(SAMPLE_RESOURCES_DIR, exist_ok=True)
    
    # Sample Observation (BP measurement)
    sample_observation = {
        "resourceType": "Observation",
        "id": "blood-pressure-1",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel"
                }
            ],
            "text": "Blood pressure systolic & diastolic"
        },
        "subject": {
            "reference": "Patient/patient-1"
        },
        "effectiveDateTime": "2023-01-15T12:30:00Z",
        "component": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure"
                        }
                    ],
                    "text": "Systolic blood pressure"
                },
                "valueQuantity": {
                    "value": 120,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure"
                        }
                    ],
                    "text": "Diastolic blood pressure"
                },
                "valueQuantity": {
                    "value": 80,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    }
    
    # Generate multiple observations with different values
    for i in range(1, 11):
        obs = sample_observation.copy()
        obs["id"] = f"blood-pressure-{i}"
        obs["subject"]["reference"] = f"Patient/patient-{(i % 3) + 1}"  # Assign to 3 different patients
        
        # Vary the systolic and diastolic values
        if i % 3 == 0:
            # High BP
            obs["component"][0]["valueQuantity"]["value"] = 140 + (i % 10)
            obs["component"][1]["valueQuantity"]["value"] = 90 + (i % 5)
        elif i % 3 == 1:
            # Normal BP
            obs["component"][0]["valueQuantity"]["value"] = 120 + (i % 10)
            obs["component"][1]["valueQuantity"]["value"] = 80 + (i % 5)
        else:
            # Low BP
            obs["component"][0]["valueQuantity"]["value"] = 100 + (i % 10)
            obs["component"][1]["valueQuantity"]["value"] = 65 + (i % 5)
        
        # Save observation to file
        import json
        with open(SAMPLE_RESOURCES_DIR / f"observation-{i}.json", "w") as f:
            json.dump(obs, f, indent=2)
    
    # Create sample patients
    for i in range(1, 4):
        patient = {
            "resourceType": "Patient",
            "id": f"patient-{i}",
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": f"Patient{i}",
                    "given": [f"Test{i}"]
                }
            ],
            "gender": "male" if i % 2 == 0 else "female",
            "birthDate": f"19{70+i}-01-01",
        }
        
        # Save patient to file
        import json
        with open(SAMPLE_RESOURCES_DIR / f"patient-{i}.json", "w") as f:
            json.dump(patient, f, indent=2)
    
    print(f"Created sample data in {SAMPLE_RESOURCES_DIR}")


def prototype_fhir_pyrate_dataset():
    """Prototype FHIR-PYrate dataset functionality."""
    
    if not FHIR_PYRATE_AVAILABLE:
        print("Cannot run FHIR-PYrate prototype - package not installed")
        return
    
    print("\nPrototyping FHIR-PYrate Dataset functionality:")
    print("="*50)
    
    # Create a FHIR-PYrate dataset from the sample resources
    dataset_builder = FhirPyrateBuilder()
    
    # Load all FHIR resources from the sample directory
    dataset_builder.from_directory(SAMPLE_RESOURCES_DIR)
    
    # Build the dataset
    dataset = dataset_builder.build()
    
    # Print basic dataset information
    print(f"Dataset created with {len(dataset)} resources")
    print(f"Resource types: {dataset.resource_types}")
    
    # Extract all Patient resources
    patients = dataset.get_by_resource_type("Patient")
    print(f"Found {len(patients)} Patient resources")
    
    # Extract all Observation resources
    observations = dataset.get_by_resource_type("Observation")
    print(f"Found {len(observations)} Observation resources")
    
    # Extract observations for a specific patient
    patient_id = "patient-1"
    patient_observations = dataset.get_by_reference(f"Patient/{patient_id}", "subject")
    print(f"Found {len(patient_observations)} observations for Patient/{patient_id}")
    
    # Convert to DataFrame for analysis
    if len(observations) > 0:
        # Flatten the observations to create a tabular structure
        flatten_transformer = Flatten(
            columns=[
                "id",
                "subject.reference",
                "effectiveDateTime",
                "component[0].valueQuantity.value",  # Systolic
                "component[1].valueQuantity.value",  # Diastolic
            ]
        )
        observations_df = flatten_transformer.transform(observations)
        
        # Rename columns for clarity
        observations_df = observations_df.rename(columns={
            "component[0].valueQuantity.value": "systolic",
            "component[1].valueQuantity.value": "diastolic"
        })
        
        print("\nObservation Data Sample:")
        print(observations_df.head())
        
        # Calculate blood pressure category
        def bp_category(row):
            systolic = row["systolic"]
            diastolic = row["diastolic"]
            
            if systolic >= 140 or diastolic >= 90:
                return "High"
            elif systolic <= 90 or diastolic <= 60:
                return "Low"
            else:
                return "Normal"
        
        observations_df["bp_category"] = observations_df.apply(bp_category, axis=1)
        
        print("\nBlood Pressure Categories:")
        print(observations_df[["systolic", "diastolic", "bp_category"]].head())
        
        # Summary statistics
        print("\nSummary Statistics:")
        print(observations_df[["systolic", "diastolic"]].describe())
        
        # Patient-level aggregation
        patient_stats = observations_df.groupby("subject.reference").agg({
            "systolic": ["mean", "min", "max"],
            "diastolic": ["mean", "min", "max"],
            "bp_category": lambda x: x.value_counts().index[0]  # Most common category
        })
        
        print("\nPatient-level Blood Pressure Statistics:")
        print(patient_stats)
    
    return dataset


def prototype_fhir_pyrate_cohort():
    """Prototype FHIR-PYrate cohort building functionality."""
    
    if not FHIR_PYRATE_AVAILABLE:
        print("Cannot run FHIR-PYrate cohort prototype - package not installed")
        return
    
    print("\nPrototyping FHIR-PYrate Cohort functionality:")
    print("="*50)
    
    # Create a dataset builder and load sample data
    dataset_builder = FhirPyrateBuilder()
    dataset_builder.from_directory(SAMPLE_RESOURCES_DIR)
    
    # Build the dataset
    dataset = dataset_builder.build()
    
    # Define a cohort of patients with high blood pressure
    # 1. Get all observations
    observations = dataset.get_by_resource_type("Observation")
    
    # 2. Filter for high systolic blood pressure (>=140)
    filter_high_bp = Filter(
        filter_fn=lambda resource: (
            resource["component"][0]["valueQuantity"]["value"] >= 140
            if "component" in resource and len(resource["component"]) > 0
            else False
        )
    )
    high_bp_observations = filter_high_bp.transform(observations)
    
    print(f"Found {len(high_bp_observations)} observations with high systolic BP")
    
    # 3. Extract the patient references from these observations
    patients_with_high_bp = set()
    for obs in high_bp_observations:
        if "subject" in obs and "reference" in obs["subject"]:
            patients_with_high_bp.add(obs["subject"]["reference"])
    
    print(f"Found {len(patients_with_high_bp)} patients with high BP readings")
    print(f"Patient references: {patients_with_high_bp}")
    
    # 4. Get the patient resources for these patients
    high_bp_cohort = []
    for patient_ref in patients_with_high_bp:
        patient_id = patient_ref.split("/")[1] if "/" in patient_ref else patient_ref
        patient = dataset.get_by_id(patient_id, "Patient")
        if patient:
            high_bp_cohort.append(patient)
    
    print(f"High BP cohort size: {len(high_bp_cohort)} patients")
    
    # Display cohort demographics
    if high_bp_cohort:
        flatten_transformer = Flatten(
            columns=["id", "gender", "birthDate"]
        )
        cohort_df = flatten_transformer.transform(high_bp_cohort)
        
        print("\nCohort Demographics:")
        print(cohort_df)
        
        # Calculate age from birthDate
        from datetime import datetime
        current_year = datetime.now().year
        
        cohort_df["birth_year"] = cohort_df["birthDate"].str[:4].astype(int)
        cohort_df["age"] = current_year - cohort_df["birth_year"]
        
        print("\nAge Distribution:")
        print(cohort_df[["id", "gender", "age"]].sort_values("age"))
        
        print("\nGender Distribution:")
        print(cohort_df["gender"].value_counts())
    
    return high_bp_cohort


def main():
    """Main function to run the prototype."""
    print("FHIR-PYrate Data Science Workflow Prototype\n")
    
    if not FHIR_PYRATE_AVAILABLE:
        print("WARNING: FHIR-PYrate package not installed")
        print("Install with: pip install fhir-pyrate")
        return
    
    # Create sample data
    create_sample_data()
    
    # Run dataset prototype
    dataset = prototype_fhir_pyrate_dataset()
    
    # Run cohort building prototype
    cohort = prototype_fhir_pyrate_cohort()
    
    print("\nPrototype Complete!")


if __name__ == "__main__":
    main() 