#!/bin/bash
# Script to commit the merged fhir_pipeline package

# Add all files to the commit
git add .

# Create a commit with a descriptive message
git commit -m "Namespace consolidation: Merge transform engine into core package

This commit merges the modular transform engine from the separate 
fhir_pipeline directory into the main epic-fhir-integration/fhir_pipeline 
package. The changes include:

1. Added Bronze → Silver transformation capability via YAML-driven mapping
2. Added validation layer with Pydantic schemas
3. Added custom transformer support for resource-specific logic
4. Integrated transforms with the existing FHIR client and auth modules
5. Added comprehensive test coverage for new components
6. Updated documentation to reflect the new architecture

This consolidation eliminates namespace conflicts and provides a single,
cohesive package that handles the full FHIR data pipeline from extraction 
through transformation to gold datasets.

Resolves the double fhir_pipeline import issue."

# Display commit status
git status

echo ""
echo "Commit created. Review the changes and push when ready with:"
echo "git push origin main" 