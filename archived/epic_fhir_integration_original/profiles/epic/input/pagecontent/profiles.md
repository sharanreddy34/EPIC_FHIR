# Epic FHIR Profiles

## Patient

The [Epic Patient](StructureDefinition-epic-patient.html) profile defines constraints and extensions on the Patient resource to better represent patients in Epic FHIR APIs.

### Key Differences from US Core Patient

* Requires at least one identifier of type MRN
* Requires at least one name with use = "official"
* Requires gender and birthDate
* Supports US Core race and ethnicity extensions
* Defines slices for phone and email telecommunications

## Observation

The [Epic Observation](StructureDefinition-epic-observation.html) profile defines constraints and extensions on the Observation resource to better represent observations in Epic FHIR APIs.

### Key Differences from US Core Observation

* Requires at least one category
* Subject references must be to an EpicPatient resource
* Requires an effective time
* Defines slices for different value types
* Provides clearer expectations for components 