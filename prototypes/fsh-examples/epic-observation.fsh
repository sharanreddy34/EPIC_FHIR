// Epic Vital Signs Observation profile in FHIR Shorthand (FSH)

Alias: SCT = http://snomed.info/sct
Alias: LOINC = http://loinc.org
Alias: UCUM = http://unitsofmeasure.org

Profile: EpicVitalSignsObservation
Parent: Observation
Id: epic-vital-signs-observation
Title: "Epic Vital Signs Observation Profile"
Description: "Profile for vital signs observations from Epic, including required elements and terminology bindings"

// Require the vital-signs category
* category 1..*
* category ^slicing.discriminator.type = #pattern
* category ^slicing.discriminator.path = "coding.code"
* category ^slicing.rules = #open
* category ^slicing.description = "Slice based on category code"
* category contains vitalSigns 1..1
* category[vitalSigns].coding 1..*
* category[vitalSigns].coding contains vitalsCode 1..1
* category[vitalSigns].coding[vitalsCode].system = "http://terminology.hl7.org/CodeSystem/observation-category" (exactly)
* category[vitalSigns].coding[vitalsCode].code = #vital-signs (exactly)

// Status must be present and from a restricted set of values
* status 1..1 MS
* status from ObservationStatusActiveValues (required)
* status ^short = "Status of the observation"

// Require code with LOINC
* code 1..1 MS
* code.coding 1..*
* code.coding contains loincCode 1..1
* code.coding[loincCode].system = "http://loinc.org" (exactly)
* code.coding[loincCode].code 1..1
* code.coding[loincCode].code from EpicVitalSignsValueSet (required)

// Require subject to be a reference to a Patient
* subject 1..1 MS
* subject only Reference(EpicPatient)
* subject ^short = "Patient the vital sign is about"

// Require effective date/time
* effective[x] 1..1 MS
* effective[x] only dateTime
* effectiveDateTime ^short = "Date and time when the vital sign was recorded"

// Require a value, either a quantity, codeable concept, or component
* (value[x] or component).exists()

// For blood pressure, components are required
* component MS
* component ^slicing.discriminator.type = #pattern
* component ^slicing.discriminator.path = "code.coding.code"
* component ^slicing.rules = #open
* component ^slicing.description = "Slice based on component code"

// Define value set for vital sign codes
ValueSet: EpicVitalSignsValueSet
Id: epic-vital-signs-valueset
Title: "Epic Vital Signs Value Set"
Description: "LOINC codes for vital signs commonly used in Epic"
* LOINC#8480-6 "Systolic blood pressure"
* LOINC#8462-4 "Diastolic blood pressure"
* LOINC#8867-4 "Heart rate"
* LOINC#8310-5 "Body temperature"
* LOINC#9279-1 "Respiratory rate"
* LOINC#59408-5 "Oxygen saturation in Arterial blood by Pulse oximetry"
* LOINC#39156-5 "Body mass index (BMI) [Ratio]"
* LOINC#85354-9 "Blood pressure panel with all children optional"

// Status values that indicate the observation is active/available
ValueSet: ObservationStatusActiveValues
Id: observation-status-active-values
Title: "Observation Status Active Values"
Description: "Status values that indicate the observation is active and available"
* http://hl7.org/fhir/observation-status#registered "Registered"
* http://hl7.org/fhir/observation-status#preliminary "Preliminary"
* http://hl7.org/fhir/observation-status#final "Final"
* http://hl7.org/fhir/observation-status#amended "Amended" 