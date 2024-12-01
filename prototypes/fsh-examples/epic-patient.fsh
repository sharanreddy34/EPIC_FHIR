// Epic Patient profile in FHIR Shorthand (FSH)
// This is a simple example for demonstration purposes

Alias: SCT = http://snomed.info/sct
Alias: LOINC = http://loinc.org
Alias: EPIC = urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.0

Profile: EpicPatient
Parent: Patient
Id: epic-patient
Title: "Epic Patient Profile"
Description: "Patient profile for Epic FHIR integration with required identifiers and extensions"

// Require at least one identifier (MRN)
* identifier 1..*

// Set up slicing for different identifier types
* identifier ^slicing.discriminator.type = #pattern
* identifier ^slicing.discriminator.path = "system"
* identifier ^slicing.rules = #open
* identifier ^slicing.description = "Slice based on identifier system"

// MRN slice - Epic Medical Record Number
* identifier contains mrn 1..1
* identifier[mrn].system = "EPIC" (exactly)
* identifier[mrn].type.coding.system = "http://terminology.hl7.org/CodeSystem/v2-0203"
* identifier[mrn].type.coding.code = #MR
* identifier[mrn].value 1..1

// Require active status
* active 1..1 MS

// Require at least one name
* name 1..*
* name.family 1..1 MS
* name.given 1..* MS

// Require gender and birth date
* gender 1..1 MS
* birthDate 1..1 MS

// Add extension for patient consent
* extension contains PatientConsent named consent 0..* MS
* extension[consent].valueCodeableConcept from PatientConsentValueSet (required)

// Define extension
Extension: PatientConsent
Id: patient-consent
Title: "Patient Consent"
Description: "Types of consent provided by the patient"
* value[x] only CodeableConcept

// Define value set for consent types
ValueSet: PatientConsentValueSet
Id: patient-consent-valueset
Title: "Patient Consent Value Set"
Description: "Codes representing different types of patient consent"
* SCT#425691002 "Consent given for electronic record sharing"
* SCT#433621000124101 "Consent given for research participation"
* SCT#428400000 "Consent given for treatment" 