import pytest
import time
import json
import os
from pathlib import Path
import statistics
from typing import List, Dict, Any, Callable

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation

from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
from epic_fhir_integration.utils.fhirpath_extractor import FHIRPathExtractor

# Test data paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
LARGE_PATIENT_SET = FIXTURES_DIR / "large_patient_set.json"
LARGE_OBSERVATION_SET = FIXTURES_DIR / "large_observation_set.json"

# Number of iterations for each test
TEST_ITERATIONS = 5
# Minimum number of resources to test with
MIN_RESOURCES = 100

@pytest.fixture
def generate_test_data():
    """Generate test data if it doesn't exist already."""
    if not FIXTURES_DIR.exists():
        FIXTURES_DIR.mkdir(parents=True)
    
    # Generate large patient set if it doesn't exist
    if not LARGE_PATIENT_SET.exists():
        patients = []
        for i in range(MIN_RESOURCES):
            patient = Patient.construct(
                id=f"patient-{i}",
                identifier=[
                    {
                        "system": "http://example.org/fhir/identifier/mrn",
                        "value": f"{10000 + i}"
                    },
                    {
                        "system": "http://example.org/fhir/identifier/ssn",
                        "value": f"123-45-{6000 + i}"
                    }
                ],
                name=[
                    {
                        "use": "official",
                        "family": f"Family{i}",
                        "given": [f"Given{i}", f"Middle{i}"]
                    },
                    {
                        "use": "nickname",
                        "given": [f"Nickname{i}"]
                    }
                ],
                gender="male" if i % 2 == 0 else "female",
                birthDate=f"19{70 + i % 30}-{1 + i % 12}-{1 + i % 28}",
                address=[
                    {
                        "use": "home",
                        "line": [f"{1000 + i} Main St"],
                        "city": "Anytown",
                        "state": "CA",
                        "postalCode": f"9{1000 + i}"
                    }
                ],
                telecom=[
                    {
                        "system": "phone",
                        "value": f"555-{1000 + i}",
                        "use": "home"
                    },
                    {
                        "system": "email",
                        "value": f"patient{i}@example.com"
                    }
                ]
            )
            patients.append(patient.dict())
        
        LARGE_PATIENT_SET.write_text(json.dumps(patients))
    
    # Generate large observation set if it doesn't exist
    if not LARGE_OBSERVATION_SET.exists():
        observations = []
        for i in range(MIN_RESOURCES * 5):  # Multiple observations per patient
            patient_id = i % MIN_RESOURCES
            code_index = i % 5
            code_systems = [
                {"system": "http://loinc.org", "code": "8480-6", "display": "Blood Pressure"},
                {"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic BP"},
                {"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"},
                {"system": "http://loinc.org", "code": "2339-0", "display": "Glucose"},
                {"system": "http://loinc.org", "code": "2093-3", "display": "Cholesterol"}
            ]
            
            observation = Observation.construct(
                id=f"obs-{i}",
                status="final",
                code={
                    "coding": [code_systems[code_index]]
                },
                subject={"reference": f"Patient/patient-{patient_id}"},
                effectiveDateTime=f"2023-{1 + i % 12}-{1 + i % 28}",
                valueQuantity={
                    "value": 100 + i % 100,
                    "unit": "mmHg" if code_index <= 1 else "bpm" if code_index == 2 else "mg/dL",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]" if code_index <= 1 else "/min" if code_index == 2 else "mg/dL"
                }
            )
            observations.append(observation.dict())
        
        LARGE_OBSERVATION_SET.write_text(json.dumps(observations))
    
    # Load the data
    patients = [Patient.parse_obj(p) for p in json.loads(LARGE_PATIENT_SET.read_text())]
    observations = [Observation.parse_obj(o) for o in json.loads(LARGE_OBSERVATION_SET.read_text())]
    
    return {
        "patients": patients,
        "observations": observations
    }

def time_execution(func: Callable, *args, **kwargs) -> float:
    """Measure execution time of a function."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return (end_time - start_time) * 1000  # Convert to milliseconds

def benchmark_function(func: Callable, iterations: int, *args, **kwargs) -> Dict[str, float]:
    """Run benchmark on a function with multiple iterations."""
    times = []
    for _ in range(iterations):
        execution_time = time_execution(func, *args, **kwargs)
        times.append(execution_time)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0
    }

class TestFHIRPathPerformance:
    """Performance benchmarks for FHIRPath implementations."""
    
    def test_fhirpath_extraction_comparison(self, generate_test_data):
        """Compare performance between old and new FHIRPath implementations."""
        patients = generate_test_data["patients"]
        observations = generate_test_data["observations"]
        
        # Define test queries
        test_queries = [
            {"name": "Simple Path", "path": "Patient.name.given"},
            {"name": "Filter Expression", "path": "Patient.name.where(use='official').family"},
            {"name": "Complex Expression", "path": "Patient.telecom.where(system='phone' and use='home').value"},
        ]
        
        # Initialize adapters
        old_adapter = FHIRPathExtractor()
        new_adapter = FHIRPathAdapter()
        
        # Run benchmarks for each query
        results = {}
        
        for query in test_queries:
            # Test old implementation
            old_results = benchmark_function(
                lambda: [old_adapter.extract(p, query["path"]) for p in patients[:100]],
                TEST_ITERATIONS
            )
            
            # Test new implementation
            new_results = benchmark_function(
                lambda: [new_adapter.extract(p, query["path"]) for p in patients[:100]],
                TEST_ITERATIONS
            )
            
            # Calculate improvement
            if old_results["mean"] > 0:
                improvement = ((old_results["mean"] - new_results["mean"]) / old_results["mean"]) * 100
            else:
                improvement = 0
            
            results[query["name"]] = {
                "old_implementation": old_results,
                "new_implementation": new_results,
                "improvement_percentage": improvement
            }
        
        # Print results in a readable format
        print("\n\nFHIRPath Performance Benchmark Results:")
        print("=====================================")
        for query_name, result in results.items():
            print(f"\nQuery: {query_name}")
            print(f"  Old Implementation (ms): mean={result['old_implementation']['mean']:.2f}, "
                  f"median={result['old_implementation']['median']:.2f}")
            print(f"  New Implementation (ms): mean={result['new_implementation']['mean']:.2f}, "
                  f"median={result['new_implementation']['median']:.2f}")
            print(f"  Improvement: {result['improvement_percentage']:.2f}%")
        
        # Make sure the results are logged even if the test "fails"
        # But actually assert something to verify the test runs
        for query_name, result in results.items():
            # We don't assert that new is always faster since this might not be true
            # in all environments or with all queries, but we document the results
            assert result["old_implementation"]["mean"] > 0
            assert result["new_implementation"]["mean"] > 0
    
    def test_batch_processing_performance(self, generate_test_data):
        """Test batch processing performance with the new implementation."""
        observations = generate_test_data["observations"]
        
        # Define the extraction function
        def extract_values_old(obs_list):
            results = []
            for obs in obs_list:
                value = FHIRPathExtractor.extract_first(obs, "valueQuantity.value")
                if value is not None:
                    results.append(value)
            return results
        
        def extract_values_new(obs_list):
            adapter = FHIRPathAdapter()
            results = []
            for obs in obs_list:
                value = adapter.extract_first(obs, "valueQuantity.value")
                if value is not None:
                    results.append(value)
            return results
        
        # Run benchmarks for different batch sizes
        batch_sizes = [10, 50, 100, 500]
        results = {}
        
        for size in batch_sizes:
            # Limit to available data
            actual_size = min(size, len(observations))
            
            # Test old implementation
            old_results = benchmark_function(
                extract_values_old,
                TEST_ITERATIONS,
                observations[:actual_size]
            )
            
            # Test new implementation
            new_results = benchmark_function(
                extract_values_new,
                TEST_ITERATIONS,
                observations[:actual_size]
            )
            
            # Calculate improvement
            if old_results["mean"] > 0:
                improvement = ((old_results["mean"] - new_results["mean"]) / old_results["mean"]) * 100
            else:
                improvement = 0
            
            results[f"Batch Size {actual_size}"] = {
                "old_implementation": old_results,
                "new_implementation": new_results,
                "improvement_percentage": improvement
            }
        
        # Print results
        print("\n\nBatch Processing Performance Benchmark Results:")
        print("==============================================")
        for batch_name, result in results.items():
            print(f"\n{batch_name}")
            print(f"  Old Implementation (ms): mean={result['old_implementation']['mean']:.2f}, "
                  f"median={result['old_implementation']['median']:.2f}")
            print(f"  New Implementation (ms): mean={result['new_implementation']['mean']:.2f}, "
                  f"median={result['new_implementation']['median']:.2f}")
            print(f"  Improvement: {result['improvement_percentage']:.2f}%")
        
        # Check that the test ran successfully
        for batch_name, result in results.items():
            assert result["old_implementation"]["mean"] > 0
            assert result["new_implementation"]["mean"] > 0 