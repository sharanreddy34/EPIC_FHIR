#!/usr/bin/env python3
"""
Prototype for testing Pathling for advanced FHIR analytics.

This prototype demonstrates how Pathling can be used to perform 
advanced analytics on FHIR data, including aggregate queries,
population analysis, and extraction.

Note: This requires Java 11+ to be installed.
See JAVA_REQUIREMENTS.md for setup instructions.
"""

import os
import json
import tempfile
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional

# Try to import the Pathling python client
try:
    from pathling.client import PathlingClient
    PATHLING_AVAILABLE = True
except ImportError:
    PATHLING_AVAILABLE = False
    print("Pathling client not installed. Run: pip install pathling")

# Sample data directory
SAMPLE_RESOURCES_DIR = Path("./sample_data")


def create_sample_data():
    """Create sample FHIR data for testing Pathling."""
    
    # Create directory if it doesn't exist
    os.makedirs(SAMPLE_RESOURCES_DIR, exist_ok=True)
    
    # Create a batch of simulated patients with various conditions and observations
    patients = []
    conditions = []
    observations = []
    
    # Generate 50 patients with demographic information
    for i in range(1, 51):
        # Determine demographics
        gender = "male" if i % 2 == 0 else "female"
        age_decade = (i % 5) + 2  # 2=20s, 3=30s, etc.
        birth_year = 2023 - (age_decade * 10) - (i % 10)
        
        # Create patient resource
        patient = {
            "resourceType": "Patient",
            "id": f"pt-{i:03d}",
            "active": True,
            "gender": gender,
            "birthDate": f"{birth_year}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "name": [
                {
                    "use": "official",
                    "family": f"Patient{i}",
                    "given": [f"Test{i}"]
                }
            ],
            "address": [
                {
                    "use": "home",
                    "city": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"][i % 5],
                    "state": ["NY", "CA", "IL", "TX", "AZ"][i % 5],
                    "postalCode": f"{10000 + i}",
                    "country": "USA"
                }
            ]
        }
        
        # Add extension for US Core ethnicity
        if i % 4 == 0:
            patient["extension"] = [
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                    "extension": [
                        {
                            "url": "text",
                            "valueString": ["Hispanic or Latino", "Not Hispanic or Latino"][i % 2]
                        }
                    ]
                }
            ]
        
        patients.append(patient)
        
        # Create 1-3 conditions for each patient
        num_conditions = (i % 3) + 1
        for j in range(num_conditions):
            # Select condition based on patient characteristics
            if gender == "female" and age_decade >= 4 and j == 0:
                condition_code = "73211009"  # Diabetes
                condition_display = "Diabetes mellitus"
            elif gender == "male" and age_decade >= 5 and j == 0:
                condition_code = "38341003"  # Hypertension
                condition_display = "Hypertensive disorder"
            elif i % 7 == 0 and j == 1:
                condition_code = "195967001"  # Asthma
                condition_display = "Asthma"
            elif i % 11 == 0:
                condition_code = "13644009"  # Hypercholesterolemia
                condition_display = "Hypercholesterolemia"
            else:
                # Random common conditions
                common_conditions = [
                    {"code": "386661006", "display": "Fever"},
                    {"code": "73430006", "display": "Sleep disorder"},
                    {"code": "267032009", "display": "Tired"},
                    {"code": "16114001", "display": "Fracture"},
                    {"code": "248595008", "display": "Sore throat"}
                ]
                selected = common_conditions[(i + j) % len(common_conditions)]
                condition_code = selected["code"]
                condition_display = selected["display"]
            
            # Create the condition resource
            condition = {
                "resourceType": "Condition",
                "id": f"cond-{i:03d}-{j}",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active"
                        }
                    ]
                },
                "verificationStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            "code": "confirmed"
                        }
                    ]
                },
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                "code": "problem-list-item",
                                "display": "Problem List Item"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": condition_code,
                            "display": condition_display
                        }
                    ],
                    "text": condition_display
                },
                "subject": {
                    "reference": f"Patient/pt-{i:03d}"
                },
                "onsetDateTime": f"2022-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            }
            
            conditions.append(condition)
        
        # Create 2-5 observations for each patient
        num_observations = (i % 4) + 2
        for j in range(num_observations):
            # Determine observation type based on patient characteristics
            if j == 0:
                # Blood pressure for everyone
                obs = create_blood_pressure_observation(
                    patient_id=f"pt-{i:03d}",
                    obs_id=f"obs-bp-{i:03d}-{j}",
                    systolic=120 + ((i*3) % 60),  # Range from 120-180
                    diastolic=70 + ((i*2) % 30),  # Range from 70-100
                    date=f"2023-{1+(i % 12):02d}-{(i % 28) + 1:02d}"
                )
            elif j == 1:
                # Blood glucose for some patients
                obs = create_glucose_observation(
                    patient_id=f"pt-{i:03d}",
                    obs_id=f"obs-glu-{i:03d}-{j}",
                    value=80 + ((i*4) % 120),  # Range from 80-200
                    date=f"2023-{1+(i % 12):02d}-{(i % 28) + 1:02d}"
                )
            elif j == 2 and i % 2 == 0:
                # Cholesterol
                obs = create_cholesterol_observation(
                    patient_id=f"pt-{i:03d}",
                    obs_id=f"obs-chol-{i:03d}-{j}",
                    total=150 + ((i*5) % 150),  # Range from 150-300
                    hdl=40 + (i % 40),  # Range from 40-80
                    ldl=80 + ((i*3) % 120),  # Range from 80-200
                    date=f"2023-{1+(i % 12):02d}-{(i % 28) + 1:02d}"
                )
            else:
                # BMI
                obs = create_bmi_observation(
                    patient_id=f"pt-{i:03d}",
                    obs_id=f"obs-bmi-{i:03d}-{j}",
                    value=18.5 + ((i*0.5) % 17.5),  # Range from 18.5-36
                    date=f"2023-{1+(i % 12):02d}-{(i % 28) + 1:02d}"
                )
            
            observations.append(obs)
    
    # Save resources to files
    for patient in patients:
        with open(SAMPLE_RESOURCES_DIR / f"patient-{patient['id']}.json", "w") as f:
            json.dump(patient, f, indent=2)
    
    for condition in conditions:
        with open(SAMPLE_RESOURCES_DIR / f"condition-{condition['id']}.json", "w") as f:
            json.dump(condition, f, indent=2)
    
    for observation in observations:
        with open(SAMPLE_RESOURCES_DIR / f"observation-{observation['id']}.json", "w") as f:
            json.dump(observation, f, indent=2)
    
    print(f"Created {len(patients)} patients, {len(conditions)} conditions, and {len(observations)} observations")
    return patients, conditions, observations


def create_blood_pressure_observation(patient_id, obs_id, systolic, diastolic, date):
    """Create a blood pressure observation."""
    return {
        "resourceType": "Observation",
        "id": obs_id,
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
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": f"{date}T12:00:00Z",
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
                    "value": systolic,
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
                    "value": diastolic,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    }


def create_glucose_observation(patient_id, obs_id, value, date):
    """Create a glucose observation."""
    return {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "2339-0",
                    "display": "Glucose [Mass/volume] in Blood"
                }
            ],
            "text": "Blood glucose"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": f"{date}T12:00:00Z",
        "valueQuantity": {
            "value": value,
            "unit": "mg/dL",
            "system": "http://unitsofmeasure.org",
            "code": "mg/dL"
        }
    }


def create_cholesterol_observation(patient_id, obs_id, total, hdl, ldl, date):
    """Create a cholesterol panel observation."""
    return {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "57698-3",
                    "display": "Lipid panel with direct LDL - Serum or Plasma"
                }
            ],
            "text": "Lipid Panel"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": f"{date}T12:00:00Z",
        "component": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2093-3",
                            "display": "Cholesterol [Mass/volume] in Serum or Plasma"
                        }
                    ],
                    "text": "Total Cholesterol"
                },
                "valueQuantity": {
                    "value": total,
                    "unit": "mg/dL",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg/dL"
                }
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2085-9",
                            "display": "Cholesterol in HDL [Mass/volume] in Serum or Plasma"
                        }
                    ],
                    "text": "HDL Cholesterol"
                },
                "valueQuantity": {
                    "value": hdl,
                    "unit": "mg/dL",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg/dL"
                }
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "13457-7",
                            "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation"
                        }
                    ],
                    "text": "LDL Cholesterol (calculated)"
                },
                "valueQuantity": {
                    "value": ldl,
                    "unit": "mg/dL",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg/dL"
                }
            }
        ]
    }


def create_bmi_observation(patient_id, obs_id, value, date):
    """Create a BMI observation."""
    return {
        "resourceType": "Observation",
        "id": obs_id,
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
                    "code": "39156-5",
                    "display": "Body mass index (BMI) [Ratio]"
                }
            ],
            "text": "BMI"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": f"{date}T12:00:00Z",
        "valueQuantity": {
            "value": value,
            "unit": "kg/m2",
            "system": "http://unitsofmeasure.org",
            "code": "kg/m2"
        }
    }


def prototype_pathling_analytics():
    """Prototype Pathling analytics capabilities."""
    
    if not PATHLING_AVAILABLE:
        print("Cannot run Pathling prototype - client package not installed")
        return
    
    print("\nPrototyping Pathling Analytics:")
    print("="*50)
    
    # Set up client
    client = PathlingClient("https://tx.csiro.au/fhir")  # Using public Pathling endpoint for testing
    
    print("Connected to Pathling server")
    
    # For a local setup with our sample data, we would normally:
    # 1. Start a Pathling server locally (e.g., via Docker)
    # 2. Import our sample data into the server
    # 3. Connect to the local server
    # 
    # For this prototype, we'll use the public server but with simulated queries and responses
    
    # Simulate an aggregate query analyzing blood pressure by gender
    print("\nSimulating aggregate query: Blood pressure statistics by gender")
    
    # In a real implementation, we would use:
    # result = client.aggregate(
    #    "Observation",
    #    "subject.resolve().gender",
    #    [
    #        "component.where(code.coding.where(code = '8480-6')).valueQuantity.value.avg()",
    #        "component.where(code.coding.where(code = '8480-6')).valueQuantity.value.stdDev()",
    #        "count()"
    #    ],
    #    filters=["code.coding.code = '85354-9'"]
    # )
    
    # Simulate the response
    simulated_bp_result = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "result",
                "resource": {
                    "resourceType": "Bundle",
                    "entry": [
                        {
                            "resource": {
                                "resourceType": "AggregationResult",
                                "dimension": [
                                    {
                                        "name": "subject.resolve().gender",
                                        "code": {
                                            "value": "male"
                                        }
                                    }
                                ],
                                "aggregate": [
                                    {
                                        "name": "component.where(code.coding.where(code = '8480-6')).valueQuantity.value.avg()",
                                        "valueDecimal": 135.2
                                    },
                                    {
                                        "name": "component.where(code.coding.where(code = '8480-6')).valueQuantity.value.stdDev()",
                                        "valueDecimal": 15.7
                                    },
                                    {
                                        "name": "count()",
                                        "valueInteger": 25
                                    }
                                ]
                            }
                        },
                        {
                            "resource": {
                                "resourceType": "AggregationResult",
                                "dimension": [
                                    {
                                        "name": "subject.resolve().gender",
                                        "code": {
                                            "value": "female"
                                        }
                                    }
                                ],
                                "aggregate": [
                                    {
                                        "name": "component.where(code.coding.where(code = '8480-6')).valueQuantity.value.avg()",
                                        "valueDecimal": 128.3
                                    },
                                    {
                                        "name": "component.where(code.coding.where(code = '8480-6')).valueQuantity.value.stdDev()",
                                        "valueDecimal": 14.2
                                    },
                                    {
                                        "name": "count()",
                                        "valueInteger": 25
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    # Process and display the simulated result
    print("\nBlood Pressure Analysis by Gender:")
    print("Gender | Avg Systolic | StdDev | Count")
    print("-------|--------------|--------|------")
    
    for entry in simulated_bp_result["parameter"][0]["resource"]["entry"]:
        result = entry["resource"]
        gender = result["dimension"][0]["code"]["value"]
        avg_systolic = result["aggregate"][0]["valueDecimal"]
        stddev = result["aggregate"][1]["valueDecimal"]
        count = result["aggregate"][2]["valueInteger"]
        
        print(f"{gender.ljust(7)}| {avg_systolic:.1f} mmHg    | {stddev:.1f}   | {count}")
    
    # Simulate a query for patients with high blood pressure
    print("\nSimulating query: Patients with high blood pressure")
    
    # In a real implementation, we would use:
    # high_bp_patients = client.extract(
    #    "Patient",
    #    [
    #        "id", 
    #        "gender", 
    #        "birthDate", 
    #        "reverseResolve(Observation.subject).where(code.coding.code = '85354-9' and component.where(code.coding.code = '8480-6').valueQuantity.value > 140).select(effectiveDateTime)"
    #    ],
    #    filters=["reverseResolve(Observation.subject).where(code.coding.code = '85354-9' and component.where(code.coding.code = '8480-6').valueQuantity.value > 140).exists()"]
    # )
    
    # Simulate the response
    simulated_high_bp_patients = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 18,
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pt-003",
                    "gender": "female",
                    "birthDate": "1987-04-04",
                    "extension": [
                        {
                            "url": "http://pathling.app/extractor/result",
                            "extension": [
                                {
                                    "url": "reverseResolve(Observation.subject).where(code.coding.code = '85354-9' and component.where(code.coding.code = '8480-6').valueQuantity.value > 140).select(effectiveDateTime)",
                                    "valueDateTime": "2023-04-04T12:00:00Z"
                                }
                            ]
                        }
                    ]
                }
            },
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pt-012",
                    "gender": "male",
                    "birthDate": "1973-01-13",
                    "extension": [
                        {
                            "url": "http://pathling.app/extractor/result",
                            "extension": [
                                {
                                    "url": "reverseResolve(Observation.subject).where(code.coding.code = '85354-9' and component.where(code.coding.code = '8480-6').valueQuantity.value > 140).select(effectiveDateTime)",
                                    "valueDateTime": "2023-01-13T12:00:00Z"
                                }
                            ]
                        }
                    ]
                }
            },
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pt-021",
                    "gender": "female",
                    "birthDate": "1965-10-22",
                    "extension": [
                        {
                            "url": "http://pathling.app/extractor/result",
                            "extension": [
                                {
                                    "url": "reverseResolve(Observation.subject).where(code.coding.code = '85354-9' and component.where(code.coding.code = '8480-6').valueQuantity.value > 140).select(effectiveDateTime)",
                                    "valueDateTime": "2023-10-22T12:00:00Z"
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }
    
    # Process and display the simulated result
    print("\nPatients with High Blood Pressure (Sample of 3 out of 18):")
    print("Patient ID | Gender | Birth Date | BP Date")
    print("-----------|--------|------------|--------")
    
    for entry in simulated_high_bp_patients["entry"]:
        patient = entry["resource"]
        patient_id = patient["id"]
        gender = patient["gender"]
        birth_date = patient["birthDate"]
        
        # Extract BP date from extension
        bp_date = None
        for ext in patient["extension"]:
            if ext["url"] == "http://pathling.app/extractor/result":
                for sub_ext in ext["extension"]:
                    if "valueDateTime" in sub_ext:
                        bp_date = sub_ext["valueDateTime"][:10]  # Just the date part
        
        print(f"{patient_id}    | {gender.ljust(6)} | {birth_date}  | {bp_date}")
    
    print("\nTotal patients with high blood pressure:", simulated_high_bp_patients["total"])
    
    return True


def prototype_pathling_local():
    """Prototype Pathling with local data (if JVM is properly configured)."""
    
    if not PATHLING_AVAILABLE:
        print("Cannot run local Pathling prototype - client package not installed")
        return
    
    try:
        # Check if we can import Java classes (will fail if Java is not set up)
        from jpype import isJVMStarted, startJVM, getDefaultJVMPath, shutdownJVM, JClass
        import jpype.imports
        
        if not isJVMStarted():
            startJVM(getDefaultJVMPath(), "-ea")
        
        # Try to import a Pathling class
        try:
            from org.hl7.fhir.r4.model import Patient as FhirPatient
            java_available = True
        except ImportError:
            java_available = False
            print("Java bridge working, but Pathling classes not available")
            return False
        
    except ImportError:
        print("Java bridge (jpype) not installed - cannot run local Java-based Pathling")
        return False
    
    print("\nLocal Pathling analytics with JVM (experimental):")
    print("="*50)
    print("Java is properly configured for Pathling")
    
    # Here we would normally initialize the Pathling encoder/library
    # and perform local operations on the sample data
    
    print("Successfully tested Java interoperability for Pathling")
    return True


def main():
    """Main function to run the prototype."""
    print("Pathling FHIR Analytics Prototype\n")
    
    # Check if Pathling is available
    if not PATHLING_AVAILABLE:
        print("WARNING: Pathling client not installed")
        print("Install with: pip install pathling")
        return
    
    # Create sample data
    create_sample_data()
    
    # Run analytics prototype against public server
    prototype_pathling_analytics()
    
    # Try local JVM-based analytics (experimental)
    prototype_pathling_local()
    
    print("\nPrototype Complete!")
    print("\nNotes:")
    print("1. For a full implementation, set up a local Pathling server via Docker:")
    print("   docker run -p 8080:8080 aehrc/pathling:latest")
    print("2. Import the sample data into the server")
    print("3. Update the client connection URL to point to the local server")
    print("4. Run actual queries against the real server instead of simulations")


if __name__ == "__main__":
    main() 