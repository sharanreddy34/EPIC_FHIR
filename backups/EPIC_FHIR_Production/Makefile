.PHONY: all clean build wheel pathling-img validator-img foundry-img

# Settings
PYTHON=python3
VENV=.venv
DIST=dist

# Main target: build everything
all: build foundry-img

# Setup virtual environment with required tools
$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip setuptools wheel build
	touch $(VENV)/bin/activate

# Build Python wheel
wheel: $(VENV)/bin/activate
	mkdir -p $(DIST)
	$(VENV)/bin/python -m build --wheel --outdir $(DIST)

# Build all components
build: wheel

# Download Pathling server (for integration with Spark)
pathling-img:
	mkdir -p ops/pathling
	curl -L -o ops/pathling/pathling-server.jar "https://github.com/aehrc/pathling/releases/download/2.1.0/pathling-server.jar" || echo "Pathling download failed - check URL"
	echo '#!/bin/bash\njava -jar pathling-server.jar "$$@"\n' > ops/pathling/pathling
	chmod +x ops/pathling/pathling

# Download HL7 FHIR Validator
validator-img:
	mkdir -p ops/validator
	curl -L -o ops/validator/validator_cli.jar "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/5.6.59/validator_cli.jar" || echo "Validator download failed - check URL"

# Build the Foundry image
foundry-img: wheel pathling-img validator-img
	docker build -t epic-fhir-foundry:latest -f ops/foundry/Dockerfile .

# Clean build artifacts
clean:
	rm -rf $(VENV) $(DIST) *.egg-info
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -exec rm -f {} +
	find . -name "*.pyo" -exec rm -f {} +
	find . -name ".coverage" -exec rm -f {} +
	find . -name "*.log" -exec rm -f {} +

# Test the Foundry image
test-foundry-img: foundry-img
	docker run --rm epic-fhir-foundry:latest epic-fhir --help

# Export the Foundry image as a tar.gz for Foundry import
export-foundry-img: foundry-img
	docker save epic-fhir-foundry:latest | gzip > epic-fhir-foundry.tar.gz
	@echo "Created epic-fhir-foundry.tar.gz for Foundry import" 