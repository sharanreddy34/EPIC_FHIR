"""
Utility functions for working with FHIR resources.

This module provides helper functions for common FHIR operations such as reference resolution,
data extraction, and resource manipulation.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_reference(value: Any) -> bool:
    """
    Check if a value is a FHIR reference.
    
    Args:
        value: The value to check
        
    Returns:
        True if the value is a FHIR reference, False otherwise
    """
    if not isinstance(value, dict):
        return False
        
    # Check if the dictionary has a 'reference' key
    if 'reference' not in value:
        return False
        
    # Make sure it's not just an empty reference
    if not value.get('reference'):
        return False
        
    return True

def get_reference_type_and_id(reference: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract the resource type and ID from a FHIR reference.
    
    Args:
        reference: A FHIR reference object
        
    Returns:
        Tuple of (resource_type, resource_id)
    """
    if not is_reference(reference):
        return None, None
        
    ref_string = reference.get('reference', '')
    
    # Handle URLs vs. relative references
    if ref_string.startswith('http'):
        # Extract the path part from the URL
        path = urlparse(ref_string).path
        # Remove any leading/trailing slashes
        path = path.strip('/')
        # Split by slash to get resource type and ID
        parts = path.split('/')
    else:
        # Split the reference by '/'
        parts = ref_string.split('/')
    
    # If the format is like "Patient/123"
    if len(parts) == 2:
        return parts[0], parts[1]
    
    # If the format doesn't match expected pattern
    logger.warning(f"Reference format not recognized: {ref_string}")
    return None, None

def find_references(resource: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Find all references within a FHIR resource.
    
    Args:
        resource: The FHIR resource to search
        
    Returns:
        List of reference objects found
    """
    references = []
    
    def search_dict(d: Dict[str, Any], path: str = ""):
        """Recursively search a dictionary for references."""
        for key, value in d.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if this is a reference
            if key == "reference" and isinstance(value, str) and value:
                parent = d
                references.append({'path': current_path, 'reference': parent})
                
            # Check if this is a reference object
            elif is_reference(value):
                references.append({'path': current_path, 'reference': value})
                
            # Recurse into nested dictionaries
            elif isinstance(value, dict):
                search_dict(value, current_path)
                
            # Recurse into lists
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        search_dict(item, f"{current_path}[{i}]")
    
    if isinstance(resource, dict):
        search_dict(resource)
        
    return references

def resolve_references(
    client,
    resource: Dict[str, Any],
    max_depth: int = 2,
    include_types: Optional[List[str]] = None,
    exclude_types: Optional[List[str]] = None,
    resolved_resources: Optional[Dict[str, Dict[str, Any]]] = None,
    current_depth: int = 0,
    visited_references: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Resolve references in a FHIR resource up to a specified depth.
    
    Args:
        client: A FHIR client instance
        resource: The resource containing references to resolve
        max_depth: Maximum depth of references to resolve
        include_types: List of resource types to include (if None, all types are included)
        exclude_types: List of resource types to exclude (if None, no types are excluded)
        resolved_resources: Dictionary of already resolved resources to avoid duplicate requests
        current_depth: Current recursion depth (internal use)
        visited_references: Set of already visited references to prevent circular references
        
    Returns:
        Resource with resolved references
    """
    # Initialize tracking structures if not provided
    if resolved_resources is None:
        resolved_resources = {}
    if visited_references is None:
        visited_references = set()
    
    # Don't exceed maximum depth
    if current_depth >= max_depth:
        return resource
    
    # Find all references in the resource
    references = find_references(resource)
    
    # Process each reference
    for ref_info in references:
        ref_obj = ref_info['reference']
        ref_path = ref_info['path']
        
        # Extract resource type and ID
        resource_type, resource_id = get_reference_type_and_id(ref_obj)
        
        # Skip if resource type or ID is missing
        if not resource_type or not resource_id:
            logger.warning(f"Invalid reference at {ref_path}")
            continue
            
        # Generate a unique key for this reference
        ref_key = f"{resource_type}/{resource_id}"
        
        # Skip circular references
        if ref_key in visited_references:
            logger.debug(f"Skipping circular reference: {ref_key}")
            continue
            
        # Skip excluded resource types
        if exclude_types and resource_type in exclude_types:
            logger.debug(f"Skipping excluded resource type: {resource_type}")
            continue
            
        # Skip if not in included types (when include_types is specified)
        if include_types and resource_type not in include_types:
            logger.debug(f"Skipping non-included resource type: {resource_type}")
            continue
        
        # Check if already resolved
        if ref_key in resolved_resources:
            logger.debug(f"Using cached resolution for {ref_key}")
            resolved = resolved_resources[ref_key]
        else:
            # Resolve the reference
            try:
                logger.debug(f"Resolving reference {ref_key}")
                resolved = client.get_resource(resource_type, resource_id)
                resolved_resources[ref_key] = resolved
            except Exception as e:
                logger.warning(f"Failed to resolve reference {ref_key}: {e}")
                continue
        
        # Add the resolved resource to the reference object
        ref_obj['_resolved'] = resolved
        
        # Track this reference as visited
        visited_references.add(ref_key)
        
        # Recursively resolve references in the resolved resource
        if current_depth < max_depth - 1:
            resolve_references(
                client=client,
                resource=resolved,
                max_depth=max_depth,
                include_types=include_types,
                exclude_types=exclude_types,
                resolved_resources=resolved_resources,
                current_depth=current_depth + 1,
                visited_references=visited_references
            )
    
    return resource

def extract_extensions(
    resource: Dict[str, Any],
    flatten: bool = False,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Extract and process extensions from a FHIR resource.
    
    Args:
        resource: FHIR resource containing extensions
        flatten: If True, flattens extensions into a simple key-value structure
        include_metadata: If True, includes metadata about each extension
        
    Returns:
        Dictionary of extracted extensions
    """
    if not isinstance(resource, dict):
        return {}
    
    # Extract all extensions from the resource
    extensions = resource.get('extension', [])
    
    # Create a mapping for Epic-specific extensions
    epic_extension_map = {
        'http://epic.com/fhir/extensions/patient/ethnicity': 'ethnicity',
        'http://epic.com/fhir/extensions/patient/race': 'race',
        'http://epic.com/fhir/extensions/patient/religion': 'religion',
        'http://epic.com/fhir/extensions/observation/result-notes': 'result_notes',
        'http://epic.com/fhir/extensions/document/description': 'document_description',
    }
    
    result = {}
    
    for ext in extensions:
        # Get extension URL (defines the type of extension)
        url = ext.get('url', '')
        
        # Skip if no URL
        if not url:
            continue
        
        # Get a friendly name for the extension if available
        name = epic_extension_map.get(url, '')
        if not name:
            # Create a friendly name from the URL if not in the mapping
            name = url.split('/')[-1]
        
        # Extract the value based on its type
        value = None
        for key in ['valueString', 'valueCode', 'valueInteger', 'valueBoolean', 'valueDecimal', 
                    'valueDate', 'valueDateTime', 'valueQuantity', 'valueReference']:
            if key in ext:
                value = ext[key]
                break
        
        # Handle nested extensions
        if 'extension' in ext and not value:
            nested_exts = ext.get('extension', [])
            nested_values = {}
            
            for nested_ext in nested_exts:
                nested_url = nested_ext.get('url', '')
                if not nested_url:
                    continue
                
                # Extract the nested extension's value
                nested_value = None
                for key in ['valueString', 'valueCode', 'valueInteger', 'valueBoolean', 'valueDecimal', 
                            'valueDate', 'valueDateTime', 'valueQuantity', 'valueReference']:
                    if key in nested_ext:
                        nested_value = nested_ext[key]
                        break
                
                # Add to nested values
                if nested_value is not None:
                    nested_name = nested_url.split('/')[-1]
                    nested_values[nested_name] = nested_value
            
            if nested_values:
                value = nested_values
        
        # Store the extension value
        if flatten:
            # Use a flat structure with dot notation for nested values
            if isinstance(value, dict):
                for k, v in value.items():
                    result[f"{name}.{k}"] = v
            else:
                result[name] = value
        else:
            # Store with metadata
            ext_entry = {'value': value}
            
            if include_metadata:
                ext_entry['url'] = url
                if 'id' in ext:
                    ext_entry['id'] = ext['id']
            
            result[name] = ext_entry
    
    return result 