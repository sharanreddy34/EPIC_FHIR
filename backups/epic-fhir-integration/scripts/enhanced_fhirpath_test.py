#!/usr/bin/env python3
"""
Enhanced FHIRPath test script to verify test data.
This doesn't require any dependencies from the epic_fhir_integration package.
"""

import os
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("enhanced_fhirpath_test")

def main():
    """Enhanced test to verify the structure of test data."""
    # Get test data path from environment or use default
    test_data_path = os.environ.get("EPIC_TEST_DATA_PATH", "test_data")
    
    logger.info(f"Looking for test data in: {test_data_path}")
    
    # Check if patient bundle exists
    patient_bundle_path = os.path.join(test_data_path, "Patient", "bundle.json")
    if not os.path.exists(patient_bundle_path):
        logger.error(f"Patient bundle not found at: {patient_bundle_path}")
        return 1
    
    logger.info(f"Found patient bundle at: {patient_bundle_path}")
    
    # Load patient bundle
    try:
        with open(patient_bundle_path, 'r') as f:
            bundle = json.load(f)
        
        # Verify bundle structure
        if bundle.get("resourceType") != "Bundle":
            logger.error("Invalid bundle: resourceType is not 'Bundle'")
            return 1
        
        entries = bundle.get("entry", [])
        logger.info(f"Bundle contains {len(entries)} entries")
        
        # Process each patient
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            
            # Basic path extraction
            patient_id = resource.get("id", "unknown")
            gender = resource.get("gender", "unknown")
            birthdate = resource.get("birthDate", "unknown")
            active = resource.get("active", False)
            
            # Name extraction
            names = resource.get("name", [])
            name_str = "Unknown"
            if names:
                name = names[0]
                family = name.get("family", "")
                given = name.get("given", [])
                name_str = f"{' '.join(given)} {family}".strip()
                
            # Identifier extraction
            identifiers = resource.get("identifier", [])
            identifier_strs = []
            for identifier in identifiers:
                system = identifier.get("system", "unknown")
                value = identifier.get("value", "unknown")
                identifier_strs.append(f"{system}: {value}")
            
            # Telecom extraction
            telecoms = resource.get("telecom", [])
            telecom_strs = []
            for telecom in telecoms:
                system = telecom.get("system", "unknown")
                value = telecom.get("value", "unknown")
                use = telecom.get("use", "")
                telecom_strs.append(f"{system} ({use}): {value}")
            
            # Address extraction
            addresses = resource.get("address", [])
            address_strs = []
            for address in addresses:
                lines = address.get("line", [])
                city = address.get("city", "")
                state = address.get("state", "")
                postal = address.get("postalCode", "")
                country = address.get("country", "")
                address_str = f"{', '.join(lines)}, {city}, {state} {postal}, {country}"
                address_strs.append(address_str)
            
            # Print patient info
            logger.info(f"Patient {i+1}:")
            logger.info(f"  ID: {patient_id}")
            logger.info(f"  Name: {name_str}")
            logger.info(f"  Gender: {gender}")
            logger.info(f"  Birth Date: {birthdate}")
            logger.info(f"  Active: {active}")
            
            if identifier_strs:
                logger.info("  Identifiers:")
                for id_str in identifier_strs:
                    logger.info(f"    - {id_str}")
            
            if telecom_strs:
                logger.info("  Contact Info:")
                for tel_str in telecom_strs:
                    logger.info(f"    - {tel_str}")
            
            if address_strs:
                logger.info("  Addresses:")
                for addr_str in address_strs:
                    logger.info(f"    - {addr_str}")
            
            # FHIRPath-like extraction examples
            logger.info("FHIRPath-like extractions:")
            logger.info(f"  resource.id: {resource.get('id')}")
            logger.info(f"  resource.name[0].family: {names[0].get('family') if names else None}")
            logger.info(f"  resource.identifier[0].value: {identifiers[0].get('value') if identifiers else None}")
            logger.info(f"  resource.telecom.where(system='phone').value: {next((t.get('value') for t in telecoms if t.get('system') == 'phone'), None)}")
            logger.info(f"  resource.telecom.where(system='email').value: {next((t.get('value') for t in telecoms if t.get('system') == 'email'), None)}")
            
            # FHIRPath boolean operations (simulated)
            has_address = len(addresses) > 0
            has_phone = any(t.get('system') == 'phone' for t in telecoms)
            has_email = any(t.get('system') == 'email' for t in telecoms)
            logger.info("FHIRPath boolean operations:")
            logger.info(f"  resource.address.exists(): {has_address}")
            logger.info(f"  resource.telecom.where(system='phone').exists(): {has_phone}")
            logger.info(f"  resource.telecom.where(system='email').exists(): {has_email}")
            logger.info(f"  resource.gender = 'male': {gender == 'male'}")
        
        logger.info("Test completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error processing bundle: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 