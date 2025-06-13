import re
import logging
from typing import Dict, Any, List, Union, Optional, Callable, Type

import yaml
import pyspark.sql
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, expr, lit, coalesce, udf, sha2, concat
from pyspark.sql.types import StringType, DoubleType, StructType, MapType

# Regular expression for stripping HTML tags
HTML_TAG_RE = re.compile(r'<.*?>')

# Optional: If available in environment
try:
    from fhirpathpy import evaluate as fhir_eval
    FHIRPATH_AVAILABLE = True
except ImportError:
    FHIRPATH_AVAILABLE = False
    logging.warning("fhirpathpy not available; using simplified path resolution")

# For jinja2 templates if enabled
try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logging.warning("jinja2 not available; template rendering disabled")

logger = logging.getLogger(__name__)


class FieldExtractor:
    """
    Utility class for extracting fields from nested FHIR resources using path expressions.
    Supports standard dot notation, array indexing, wildcards, and basic conditions.
    """
    
    def extract_value(self, obj: Dict[str, Any], path: str) -> Any:
        """
        Extract a value from a nested object using a path expression.
        
        Args:
            obj: The object to extract from
            path: Path expression (e.g., "code.coding[0].system" or "code.coding[*].code")
            
        Returns:
            The extracted value, or None if not found
        """
        if obj is None or path is None or path == "":
            return None
            
        # Handle wildcards in arrays - e.g., "code.coding[*].code"
        if "[*]" in path:
            base_path, rest = path.split("[*]", 1)
            if rest.startswith("."):
                rest = rest[1:]  # Remove leading dot
                
            # Get the array using the base path
            array = _fhir_get(obj, base_path)
            if not isinstance(array, list) or not array:
                return None
                
            # Extract values from each array element
            results = []
            for item in array:
                value = self.extract_value(item, rest)
                if value is not None:
                    results.append(value)
            
            return results if results else None
        
        # Handle conditional expressions - e.g., "code.coding[?system='http://loinc.org'].code"
        condition_match = re.search(r'\[\?([\w\.]+)=\'([^\']+)\'\]', path)
        if condition_match:
            # Parse the condition
            cond_path_part = path[:condition_match.start()]
            cond_attr = condition_match.group(1)
            cond_value = condition_match.group(2)
            
            # Extract the value after the condition
            if condition_match.end() < len(path) and path[condition_match.end()] == '.':
                result_path = path[condition_match.end()+1:]
            else:
                result_path = ""
            
            # Get the array to filter
            array = _fhir_get(obj, cond_path_part)
            if not isinstance(array, list) or not array:
                return None
            
            # Find the first element that matches the condition
            for item in array:
                item_value = _fhir_get(item, cond_attr)
                if item_value == cond_value:
                    if result_path:
                        return _fhir_get(item, result_path)
                    else:
                        return item
            
            return None
        
        # Standard path extraction for non-special cases
        return _fhir_get(obj, path)


class YAMLMapper:
    """
    Mapper for FHIR resources using YAML-defined mapping specifications.
    
    The mapper can:
    - Load mappings from YAML strings or files
    - Generate Spark UDFs for field extraction
    - Apply mappings to Spark DataFrames
    """
    
    def __init__(self, mapping_data: Dict[str, Any]):
        """
        Initialize with a mapping dictionary.
        
        Args:
            mapping_data: Dictionary with mapping configuration
        """
        self.mapping_data = mapping_data
        self.resource_type = mapping_data.get("resourceType")
        self.mappings = mapping_data.get("mappings", [])
        self.extractor = FieldExtractor()
    
    @classmethod
    def from_string(cls, yaml_string: str) -> 'YAMLMapper':
        """
        Create a mapper from a YAML string.
        
        Args:
            yaml_string: YAML mapping configuration
            
        Returns:
            YAMLMapper instance
        """
        mapping_data = yaml.safe_load(yaml_string)
        return cls(mapping_data)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'YAMLMapper':
        """
        Create a mapper from a YAML file.
        
        Args:
            file_path: Path to YAML mapping file
            
        Returns:
            YAMLMapper instance
        """
        with open(file_path, 'r') as f:
            mapping_data = yaml.safe_load(f)
        return cls(mapping_data)
    
    def generate_extraction_udf(self) -> Callable:
        """
        Generate a Spark UDF that extracts fields according to the mapping.
        
        Returns:
            Spark UDF for field extraction
        """
        extractor = self.extractor
        mappings = self.mappings
        
        # Define the extraction function
        def extract_fields(resource: Dict[str, Any]) -> Dict[str, Any]:
            if resource is None:
                return {}
                
            result = {}
            for mapping in mappings:
                source = mapping.get("source")
                target = mapping.get("target")
                if source and target:
                    result[target] = extractor.extract_value(resource, source)
            return result
        
        # Register as UDF
        return udf(extract_fields, MapType(StringType(), StringType()))
    
    def apply_to_dataframe(self, df: DataFrame) -> DataFrame:
        """
        Apply the mapping to a DataFrame with FHIR resources.
        
        Args:
            df: DataFrame with 'resource' column containing FHIR resources
            
        Returns:
            DataFrame with extracted fields as columns
        """
        # Get the extraction UDF
        extract_udf = self.generate_extraction_udf()
        
        # Apply the UDF to get a struct column with all extracted fields
        result_df = df.withColumn("extracted", extract_udf(col("resource")))
        
        # Convert struct fields to individual columns
        for mapping in self.mappings:
            target = mapping.get("target")
            if target:
                result_df = result_df.withColumn(target, col(f"extracted.{target}"))
        
        # Remove the temporary struct column
        result_df = result_df.drop("extracted")
        
        return result_df


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if text is None:
        return None
    return HTML_TAG_RE.sub('', text)

def _fhir_get(resource: Dict[str, Any], path: str) -> Any:
    """
    Get a value from a FHIR resource using dot notation path.
    Supports array indexing with [n].
    Falls back to None if path doesn't exist.
    
    Args:
        resource: FHIR resource dictionary
        path: Dot notation path, e.g. "code.coding[0].system"
        
    Returns:
        Value at the path or None if not found
    """
    if resource is None or path is None or path == "":
        return None
        
    parts = path.split('.')
    current = resource
    
    for part in parts:
        # Check for array index
        index_match = re.match(r'([^\[]+)\[(\d+)\]', part)
        
        if index_match:
            field_name, index = index_match.groups()
            index = int(index)
            
            if current is None or field_name not in current:
                return None
                
            array_value = current[field_name]
            if not isinstance(array_value, list) or index >= len(array_value):
                return None
                
            current = array_value[index]
        else:
            # Simple field access
            if current is None or part not in current:
                return None
            current = current[part]
            
    return current

def _process_value(value: Any) -> Any:
    """Process a value for Spark DataFrame compatibility."""
    if isinstance(value, dict) or isinstance(value, list):
        return str(value)  # Convert complex objects to string
    return value

# Register UDF for use in Spark
_fhir_get_udf = udf(lambda resource, path: _process_value(_fhir_get(resource, path)), StringType())

def safe_fhir(resource_col, path: str):
    """
    Create a Spark column expression that safely extracts a value from a FHIR resource.
    Falls back to None if the path doesn't exist.
    
    Args:
        resource_col: Spark Column containing FHIR resource
        path: Dot notation path to extract
        
    Returns:
        Spark Column expression
    """
    return _fhir_get_udf(resource_col, lit(path))

def apply_mapping(df: DataFrame, mapping_spec: Dict[str, Any]) -> DataFrame:
    """
    Apply a mapping specification to a FHIR resource DataFrame.
    
    Args:
        df: Input DataFrame with FHIR resources
        mapping_spec: Mapping specification from YAML
        
    Returns:
        Transformed DataFrame
    """
    # First get schema to detect if we have nested 'resource' or flat structure
    is_flat_schema = 'resourceType' in df.columns
    
    # Add hash_id column
    if is_flat_schema:
        # Use direct resourceType and id fields for flattened schema
        result_df = df.withColumn(
            '_hash_id',
            sha2(concat(col('resourceType'), col('id')), 256)
        )
    else:
        # Use nested resource fields for non-flattened schema
        result_df = df.withColumn(
            '_hash_id',
            sha2(concat(col('resource.resourceType'), col('resource.id')), 256)
        )
    
    # Apply expression mappings
    for target_column, expression in mapping_spec.get("expressions", {}).items():
        if isinstance(expression, str):
            # Handle direct expressions
            if is_flat_schema:
                # Replace any resource. prefixes in the expression
                expression = expression.replace('resource.', '')
            
            result_df = result_df.withColumn(target_column, expr(expression))
        elif isinstance(expression, dict):
            # Handle more complex expressions with additional parameters
            expr_type = expression.get("type")
            if expr_type == "custom":
                result_df = _apply_custom_expression(result_df, target_column, expression)
            elif expr_type == "case":
                result_df = _apply_case_expression(result_df, target_column, expression, is_flat_schema)
    
    # Apply field mappings
    for target_column, source_path in mapping_spec.get("fields", {}).items():
        if isinstance(source_path, str):
            # Direct mapping
            if is_flat_schema:
                # If we have a flat schema, remove 'resource.' prefix if present
                source_path = source_path.replace('resource.', '')
            
            result_df = result_df.withColumn(target_column, col(source_path))
        elif isinstance(source_path, dict):
            # Complex mapping with a path and additional options
            path = source_path.get("path")
            if is_flat_schema:
                path = path.replace('resource.', '')
                
            default_value = source_path.get("default")
            if default_value is not None:
                result_df = result_df.withColumn(
                    target_column,
                    coalesce(col(path), lit(default_value))
                )
            else:
                result_df = result_df.withColumn(target_column, col(path))
    
    # Apply the schema if defined
    if "schema" in mapping_spec:
        # TODO: Implement schema validation and enforcement
        pass
    
    return result_df 