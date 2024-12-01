.PHONY: test test-unit test-integration test-live test-perf test-validation test-auth test-transform test-extract test-all test-with-coverage clean install setup lint docs

# Default test target runs unit and integration tests
test:
	./run_tests.sh -t all

# Set up test environment
setup:
	python -m venv venv
	source venv/bin/activate && pip install -r requirements.txt
	source venv/bin/activate && pip install pytest pytest-cov pytest-asyncio responses delta-spark black ruff

# Run only unit tests
test-unit:
	./run_tests.sh -t unit

# Run integration tests
test-integration:
	./run_tests.sh -t integration

# Run performance and load tests
test-perf:
	./run_tests.sh -t perf

# Run validation tests
test-validation:
	./run_tests.sh -t validation

# Run authentication tests
test-auth:
	./run_tests.sh -t auth

# Run transformation tests
test-transform:
	./run_tests.sh -t transform

# Run extraction pipeline tests
test-extract:
	./run_tests.sh -t extract

# Run live API tests (requires EPIC environment variables)
test-live:
	python -m pytest -xvs tests/live/

# Run tests with coverage report
test-with-coverage:
	./gen_coverage.sh

# Run full test suite with coverage
test-all-with-coverage:
	./run_tests.sh -t all -c

# Clean up output directories and test artifacts
clean:
	rm -rf local_output/
	rm -rf tests/perf/chaos_report.md
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf coverage_report/
	rm -rf test-reports/
	rm -rf __pycache__/
	rm -rf tests/__pycache__/
	rm -rf tests/unit/__pycache__/
	rm -rf tests/integration/__pycache__/
	rm -rf tests/perf/__pycache__/
	rm -rf tests/live/__pycache__/

# Install dependencies
install:
	pip install -r requirements.txt

# Run linting
lint:
	black .
	ruff check .

# Generate documentation
docs:
	mkdir -p docs/html
	pdoc --html --output-dir docs/html fhir_pipeline

# Run full testing suite (except live tests)
test-all:
	./run_tests.sh -t all -c -j

# Make scripts executable
permissions:
	chmod +x run_tests.sh
	chmod +x gen_coverage.sh
	if [ -f check_circular_imports.py ]; then chmod +x check_circular_imports.py; fi 