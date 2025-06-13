.PHONY: validator-image pathling-image foundry-img

all: validator-image pathling-image

validator-image:
	docker build -t fhir-validator:latest ops/validator

pathling-image:
	docker build -t epic-pathling:latest ops/pathling

foundry-img:
	docker build -t epic-fhir-foundry:latest -f ops/foundry/Dockerfile . 