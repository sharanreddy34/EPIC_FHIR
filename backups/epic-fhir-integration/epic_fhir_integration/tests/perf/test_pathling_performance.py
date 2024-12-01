import pytest
import time
import json
import os
from pathlib import Path
import statistics
from typing import List, Dict, Any, Callable
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Pathling components, skip tests if not available
try:
    from epic_fhir_integration.analytics.pathling_service import PathlingService
    PATHLING_AVAILABLE = True
except ImportError:
    logger.warning("Pathling service not available, skipping performance tests")
    PATHLING_AVAILABLE = False

# Test data paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
LARGE_DATASET = FIXTURES_DIR / "large_dataset"

# Number of iterations for each test
TEST_ITERATIONS = 3
# Minimum number of resources to test with
MIN_RESOURCES = 100

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

@pytest.fixture(scope="module")
def prepare_pathling_service():
    """Set up Pathling service for testing."""
    if not PATHLING_AVAILABLE:
        pytest.skip("Pathling service not available")
    
    # Create a temporary directory for Pathling
    os.makedirs(LARGE_DATASET, exist_ok=True)
    
    # Initialize Pathling service
    service = PathlingService()
    
    # Only attempt to start if not already running
    try:
        if not service.is_running():
            service.start()
    except Exception as e:
        pytest.skip(f"Could not start Pathling server: {e}")
    
    # Generate test data if it doesn't exist
    if not (LARGE_DATASET / "Patient").exists():
        try:
            from fhir.resources.patient import Patient
            from fhir.resources.observation import Observation
            
            # Generate patients
            patients = []
            for i in range(MIN_RESOURCES):
                patient = Patient.construct(
                    id=f"patient-{i}",
                    identifier=[
                        {
                            "system": "http://example.org/fhir/identifier/mrn",
                            "value": f"{10000 + i}"
                        }
                    ],
                    gender="male" if i % 2 == 0 else "female",
                    birthDate=f"19{70 + i % 30}-{1 + i % 12}-{1 + i % 28}"
                ).dict()
                patients.append(patient)
            
            # Generate observations
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
                ).dict()
                observations.append(observation)
            
            # Save data to files
            os.makedirs(LARGE_DATASET / "Patient", exist_ok=True)
            with open(LARGE_DATASET / "Patient" / "bundle.json", "w") as f:
                json.dump({"resourceType": "Bundle", "type": "collection", "entry": [
                    {"resource": p} for p in patients
                ]}, f)
            
            os.makedirs(LARGE_DATASET / "Observation", exist_ok=True)
            with open(LARGE_DATASET / "Observation" / "bundle.json", "w") as f:
                json.dump({"resourceType": "Bundle", "type": "collection", "entry": [
                    {"resource": o} for o in observations
                ]}, f)
            
            # Load data into Pathling
            service.import_data(str(LARGE_DATASET))
        
        except Exception as e:
            pytest.skip(f"Could not generate test data: {e}")
    
    yield service
    
    # Clean up - don't stop the Pathling server after tests
    # to avoid startup overhead for multiple test runs
    # service.stop()

@pytest.mark.skipif(not PATHLING_AVAILABLE, reason="Pathling service not available")
class TestPathlingPerformance:
    """Performance benchmarks for Pathling analytics."""
    
    def test_aggregation_performance(self, prepare_pathling_service):
        """Test performance of aggregation operations."""
        service = prepare_pathling_service
        
        # Define test aggregations
        test_aggregations = [
            {
                "name": "Simple Count by Gender",
                "subject": "Patient",
                "aggregation": "count()",
                "grouping": "gender"
            },
            {
                "name": "BP Value Statistics",
                "subject": "Observation",
                "aggregation": "statistics($this.where(code.coding.code='8480-6').valueQuantity.value)",
                "grouping": None
            },
            {
                "name": "Count by Type with Filter",
                "subject": "Observation",
                "aggregation": "count()",
                "grouping": "code.coding.code",
                "filter": "effectiveDateTime > @2023-01-01"
            }
        ]
        
        # Run benchmarks
        results = {}
        
        for agg in test_aggregations:
            # Execute the aggregation through PathlingService
            agg_func = lambda: service.aggregate(
                subject=agg["subject"],
                aggregation=agg["aggregation"],
                grouping=agg.get("grouping"),
                filter_expr=agg.get("filter")
            )
            
            # Measure performance
            agg_results = benchmark_function(agg_func, TEST_ITERATIONS)
            results[agg["name"]] = agg_results
        
        # Print results
        print("\n\nPathling Aggregation Performance Results:")
        print("=======================================")
        for agg_name, result in results.items():
            print(f"\nAggregation: {agg_name}")
            print(f"  Execution Time (ms): mean={result['mean']:.2f}, "
                  f"median={result['median']:.2f}, min={result['min']:.2f}, max={result['max']:.2f}")
        
        # Make sure tests actually ran
        for agg_name, result in results.items():
            assert result["mean"] > 0
    
    def test_extraction_performance(self, prepare_pathling_service):
        """Test performance of data extraction operations."""
        service = prepare_pathling_service
        
        # Define test extractions
        test_extractions = [
            {
                "name": "Simple Demographics",
                "source": "Patient",
                "columns": ["id", "gender", "birthDate"]
            },
            {
                "name": "Observation Values",
                "source": "Observation",
                "columns": ["id", "subject.reference", "valueQuantity.value", "effectiveDateTime"]
            },
            {
                "name": "Complex with Function",
                "source": "Patient",
                "columns": ["id", "gender", "birthDate.toString()"]
            }
        ]
        
        # Run benchmarks
        results = {}
        
        for ext in test_extractions:
            # Execute the extraction through PathlingService
            ext_func = lambda: service.extract_dataset(
                source=ext["source"],
                columns=ext["columns"]
            )
            
            # Measure performance
            ext_results = benchmark_function(ext_func, TEST_ITERATIONS)
            results[ext["name"]] = ext_results
        
        # Print results
        print("\n\nPathling Extraction Performance Results:")
        print("======================================")
        for ext_name, result in results.items():
            print(f"\nExtraction: {ext_name}")
            print(f"  Execution Time (ms): mean={result['mean']:.2f}, "
                  f"median={result['median']:.2f}, min={result['min']:.2f}, max={result['max']:.2f}")
        
        # Make sure tests actually ran
        for ext_name, result in results.items():
            assert result["mean"] > 0
    
    def test_measure_evaluation_performance(self, prepare_pathling_service):
        """Test performance of measure evaluation."""
        service = prepare_pathling_service
        
        # Define test measures
        test_measures = [
            {
                "name": "Female Patient Percentage",
                "measure": {
                    "numerator": "Patient.where(gender='female')",
                    "denominator": "Patient"
                }
            },
            {
                "name": "High Blood Pressure Percentage",
                "measure": {
                    "numerator": "Observation.where(code.coding.code='8480-6' and valueQuantity.value > 120)",
                    "denominator": "Observation.where(code.coding.code='8480-6')"
                }
            }
        ]
        
        # Run benchmarks
        results = {}
        
        for measure in test_measures:
            # Execute the measure through PathlingService
            measure_func = lambda: service.evaluate_measure(
                numerator=measure["measure"]["numerator"],
                denominator=measure["measure"]["denominator"]
            )
            
            # Measure performance
            measure_results = benchmark_function(measure_func, TEST_ITERATIONS)
            results[measure["name"]] = measure_results
        
        # Print results
        print("\n\nPathling Measure Evaluation Performance Results:")
        print("===============================================")
        for measure_name, result in results.items():
            print(f"\nMeasure: {measure_name}")
            print(f"  Execution Time (ms): mean={result['mean']:.2f}, "
                  f"median={result['median']:.2f}, min={result['min']:.2f}, max={result['max']:.2f}")
        
        # Make sure tests actually ran
        for measure_name, result in results.items():
            assert result["mean"] > 0 