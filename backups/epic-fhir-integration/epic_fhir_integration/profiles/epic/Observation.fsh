Profile: EpicObservation
Parent: Observation
Id: epic-observation
Title: "Epic Observation Profile"
Description: "Profile for Observation resources from Epic FHIR APIs"

* status MS
* category 1..* MS
* code 1..1 MS
* code.coding 1..*
* subject 1..1 MS
* subject only Reference(EpicPatient)
* effective[x] 1..1 MS
* performer 0..* MS

* value[x] 0..1 MS
* value[x] ^slicing.discriminator.type = #type
* value[x] ^slicing.discriminator.path = "$this"
* value[x] ^slicing.rules = #open
* value[x] ^slicing.description = "Slice based on value[x] type"

* value[x] contains
    valueQuantity 0..1 MS and
    valueCodeableConcept 0..1 MS and
    valueString 0..1 MS and
    valueBoolean 0..1 MS and
    valueDateTime 0..1 MS

* valueQuantity.value 1..1 MS
* valueQuantity.unit 0..1 MS
* valueQuantity.system 0..1 MS
* valueQuantity.code 0..1 MS

* valueCodeableConcept.coding 1..*
* valueCodeableConcept.coding.code 1..1
* valueCodeableConcept.coding.system 0..1
* valueCodeableConcept.coding.display 0..1

* component 0..*
* component.code 1..1 MS
* component.code.coding 1..*
* component.value[x] 0..1 MS 