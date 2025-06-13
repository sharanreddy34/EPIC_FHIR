"""
Data quality checking for FHIR resources.
"""

from typing import Dict, List, Any, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, count, isnan, when, lit


class DataQualityChecker:
    """
    Checks data quality metrics for FHIR resources.
    
    Provides methods to check for missing values, duplicates,
    value distributions, and data consistency.
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the data quality checker.
        
        Args:
            spark: SparkSession for DataFrame operations
        """
        self.spark = spark
    
    def check_missing_values(self, df: DataFrame, fields: List[str] = None) -> Dict[str, int]:
        """
        Check for missing values in specified fields.
        
        Args:
            df: DataFrame to check
            fields: List of fields to check, or None to check all fields
            
        Returns:
            Dictionary mapping field names to count of missing values
        """
        if fields is None:
            fields = df.columns
        
        result = {}
        for field in fields:
            if field in df.columns:
                # Count nulls for this field
                null_count = df.filter(col(field).isNull()).count()
                result[field] = null_count
            else:
                # Field doesn't exist
                result[field] = "Field not found"
        
        return result
    
    def check_duplicates(self, df: DataFrame, key_fields: List[str]) -> int:
        """
        Check for duplicate records based on key fields.
        
        Args:
            df: DataFrame to check
            key_fields: Fields that should uniquely identify a record
            
        Returns:
            Count of duplicate records
        """
        # Count total rows
        total_rows = df.count()
        
        # Count distinct combinations of key fields
        distinct_count = df.select(key_fields).distinct().count()
        
        # Calculate duplicates
        duplicates = total_rows - distinct_count
        
        return duplicates
    
    def check_value_distribution(self, df: DataFrame, field: str) -> Dict[str, int]:
        """
        Check the distribution of values in a field.
        
        Args:
            df: DataFrame to check
            field: Field to analyze
            
        Returns:
            Dictionary mapping values to their counts
        """
        if field not in df.columns:
            return {"error": "Field not found"}
        
        # Count occurrences of each value
        value_counts = df.groupBy(field).count().collect()
        
        # Convert to dictionary
        distribution = {str(row[field]): row["count"] for row in value_counts}
        
        return distribution
    
    def check_data_consistency(self, df1: DataFrame, df2: DataFrame, 
                              join_field1: str, join_field2: str = None) -> Dict[str, int]:
        """
        Check consistency between two related DataFrames.
        
        Args:
            df1: First DataFrame
            df2: Second DataFrame
            join_field1: Field in first DataFrame for joining
            join_field2: Field in second DataFrame for joining, defaults to join_field1
            
        Returns:
            Dictionary with consistency metrics
        """
        if join_field2 is None:
            join_field2 = join_field1
            
        if join_field1 not in df1.columns:
            return {"error": f"Join field {join_field1} not found in first DataFrame"}
            
        if join_field2 not in df2.columns:
            return {"error": f"Join field {join_field2} not found in second DataFrame"}
        
        # Count records in each DataFrame
        df1_count = df1.count()
        df2_count = df2.count()
        
        # Count joined records
        joined_df = df1.join(df2, df1[join_field1] == df2[join_field2], "inner")
        joined_count = joined_df.count()
        
        # Count records in df1 that don't have a match in df2
        left_only = df1.join(df2, df1[join_field1] == df2[join_field2], "left_anti").count()
        
        # Count records in df2 that don't have a match in df1
        right_only = df2.join(df1, df2[join_field2] == df1[join_field1], "left_anti").count()
        
        return {
            "df1_total": df1_count,
            "df2_total": df2_count,
            "matched": joined_count,
            "df1_unmatched": left_only,
            "df2_unmatched": right_only,
            "match_percentage": round(joined_count / df1_count * 100, 2) if df1_count > 0 else 0
        }
    
    def generate_quality_report(self, df: DataFrame, resource_type: str = None) -> str:
        """
        Generate a comprehensive data quality report.
        
        Args:
            df: DataFrame to analyze
            resource_type: FHIR resource type (for report title)
            
        Returns:
            Formatted quality report as a string
        """
        title = f"Data Quality Report for {resource_type}" if resource_type else "Data Quality Report"
        
        # Get basic stats
        row_count = df.count()
        column_count = len(df.columns)
        
        # Check missing values for all fields
        missing_values = self.check_missing_values(df)
        
        # Calculate completeness percentage
        total_cells = row_count * column_count
        total_missing = sum(count for count in missing_values.values() if isinstance(count, int))
        completeness = round((1 - total_missing / total_cells) * 100, 2) if total_cells > 0 else 0
        
        # Format the report
        report = [
            title,
            "=" * len(title),
            f"Row count: {row_count}",
            f"Column count: {column_count}",
            f"Data completeness: {completeness}%",
            "",
            "Missing values by field:",
        ]
        
        for field, count in missing_values.items():
            if isinstance(count, int):
                percentage = round(count / row_count * 100, 2) if row_count > 0 else 0
                report.append(f"  {field}: {count} ({percentage}%)")
            else:
                report.append(f"  {field}: {count}")
        
        return "\n".join(report) 