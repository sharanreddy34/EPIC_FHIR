Profile: EpicPatient
Parent: Patient
Id: epic-patient
Title: "Epic Patient Profile"
Description: "Profile for Patient resources from Epic FHIR APIs"

* identifier 1..*
* identifier ^slicing.discriminator.type = #pattern
* identifier ^slicing.discriminator.path = "type"
* identifier ^slicing.rules = #open
* identifier ^slicing.description = "Slice based on identifier type"

* identifier contains
    MRN 1..1 MS and
    SSN 0..1 MS

* identifier[MRN].type = http://terminology.hl7.org/CodeSystem/v2-0203#MR
* identifier[MRN].value 1..1 MS
* identifier[MRN].system 1..1 MS

* identifier[SSN].type = http://terminology.hl7.org/CodeSystem/v2-0203#SS
* identifier[SSN].system = "http://hl7.org/fhir/sid/us-ssn"
* identifier[SSN].value 1..1 MS

* name 1..*
* name ^slicing.discriminator.type = #value
* name ^slicing.discriminator.path = "use"
* name ^slicing.rules = #open

* name contains
    official 1..1 MS

* name[official].use = #official
* name[official].family 1..1 MS
* name[official].given 1..* MS

* telecom 0..*
* telecom ^slicing.discriminator.type = #value
* telecom ^slicing.discriminator.path = "system"
* telecom ^slicing.rules = #open

* telecom contains
    phone 0..* MS and
    email 0..* MS

* telecom[phone].system = #phone
* telecom[phone].use 1..1 MS
* telecom[phone].value 1..1 MS

* telecom[email].system = #email
* telecom[email].value 1..1 MS

* gender 1..1 MS
* birthDate 1..1 MS
* address 0..*

* extension contains
    http://hl7.org/fhir/us/core/StructureDefinition/us-core-race named race 0..1 MS and
    http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity named ethnicity 0..1 MS

* communication 0..*
* communication.language 1..1 MS
* communication.preferred 0..1 MS 