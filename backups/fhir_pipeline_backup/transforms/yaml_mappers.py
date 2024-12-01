import re
import logging
from typing import Dict, Any, List, Union, Optional

import pyspark.sql
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, expr, lit, coalesce, udf
from pyspark.sql.types import StringType, DoubleType

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

def apply_mapping(df: DataFrame, spec: Dict[str, Any]) -> DataFrame:
    """
    Apply a YAML mapping specification to a DataFrame of FHIR resources.
    
    Args:
        df: DataFrame with 'resource' column containing FHIR resources
        spec: Mapping specification dictionary from YAML
        
    Returns:
        DataFrame with columns mapped according to the specification
    """
    if 'columns' not in spec:
        logger.warning("No columns specified in mapping spec")
        return df
        
    # Create a copy of the DataFrame to avoid modifying the input
    result_df = df
    
    # Add _hash_id column for idempotent writes if not already present
    if '_hash_id' not in df.columns:
        from pyspark.sql.functions import sha2, concat
        result_df = df.withColumn(
            '_hash_id', 
            sha2(concat(col('resource.resourceType'), col('resource.id')), 256)
        )
    
    # Process each column mapping
    for col_name, rule in spec['columns'].items():
        if rule is None:
            logger.warning(f"No mapping rule for column {col_name}")
            continue
            
        # Check rule type and apply appropriate transformation
        if isinstance(rule, str):
            if rule.startswith('{{') and rule.endswith('}}') and JINJA2_AVAILABLE:
                # Jinja2 template
                template_str = rule[2:-2]  # Remove {{ }}
                # Implementation would need Jinja context setup per row
                # Using UDF for demo - in production consider alternatives for performance
                @udf(StringType())
                def render_template(resource):
                    if resource is None:
                        return None
                    template = jinja2.Template(template_str)
                    return template.render(resource=resource)
                
                result_df = result_df.withColumn(col_name, render_template(col('resource')))
                
            elif '|' in rule:
                # Fallback list of paths - take first non-null
                choices = [r.strip() for r in rule.split('|')]
                exprs = [safe_fhir(col('resource'), p) for p in choices]
                result_df = result_df.withColumn(col_name, coalesce(*exprs))
                
            elif rule.startswith('"') and rule.endswith('"'):
                # Literal string
                literal_value = rule[1:-1]  # Remove quotes
                result_df = result_df.withColumn(col_name, lit(literal_value))
                
            elif '.replace(' in rule.lower():
                # String replacement operation
                base_path, replace_part = rule.split('.replace(', 1)
                replace_part = replace_part.rstrip(')')
                find_str, replace_str = replace_part.split(',', 1)
                
                # Clean up any quotes
                find_str = find_str.strip().strip('"\'')
                replace_str = replace_str.strip().strip('"\'')
                
                # Get the base value then apply replacement
                @udf(StringType())
                def replace_udf(resource):
                    value = _fhir_get(resource, base_path)
                    if value is None:
                        return None
                    return str(value).replace(find_str, replace_str)
                    
                result_df = result_df.withColumn(col_name, replace_udf(col('resource')))
                
            else:
                # Direct FHIR path
                if 'text.div' in rule:
                    # Special case for HTML content - strip the HTML
                    @udf(StringType())
                    def get_and_strip(resource):
                        value = _fhir_get(resource, rule)
                        if value is None:
                            return None
                        return _strip_html(str(value))
                        
                    result_df = result_df.withColumn(col_name, get_and_strip(col('resource')))
                else:
                    result_df = result_df.withColumn(col_name, safe_fhir(col('resource'), rule))
    
    # Apply extras configuration if present
    if 'extras' in spec and 'partition_by' in spec['extras']:
        # Note: we're just setting the column here, actual partitioning happens during write
        partition_cols = spec['extras']['partition_by']
        for part_col in partition_cols:
            if part_col.endswith('_year') and part_col not in result_df.columns:
                # Extract year from date column
                source_col = part_col.replace('_year', '')
                if source_col in result_df.columns:
                    result_df = result_df.withColumn(
                        part_col, 
                        expr(f"year({source_col})")
                    )
    
    return result_df 