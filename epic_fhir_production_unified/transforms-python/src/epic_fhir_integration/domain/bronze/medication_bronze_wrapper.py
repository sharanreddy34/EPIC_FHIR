"""
MedicationRequest Bronze transform wrapper for Palantir Foundry.

This module provides a wrapper around the generic FHIR Bronze transform with a static 
output dataset path for MedicationRequest resources.
"""

from transforms.api import transform_df, incremental, Output, Config

from epic_fhir_integration.bronze.fhir_bronze_transform import compute as generic_compute

# Re-bind the compute function with a static dataset id for MedicationRequest resources
@incremental(snapshot_inputs=True)
@transform_df(
    Output("datasets/bronze/MedicationRequest_Raw_Bronze"),
    Config("max_pages", 50),
    Config("batch_size", 100),
)
def compute(ctx, output, max_pages, batch_size):
    """Extract MedicationRequest FHIR resources from Epic API and write to Bronze dataset.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        max_pages: Maximum number of pages to retrieve.
        batch_size: Batch size for API requests.
    """
    # Call the generic compute function with MedicationRequest resource type
    return generic_compute(ctx, output, "MedicationRequest", max_pages, batch_size) 