#!/bin/bash

# Exit on error
set -e

# Function to check if command succeeded
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1 failed"
        exit 1
    fi
}

echo "Starting GCP Initial Setup..."

# Get the current project ID and number
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
echo "Using project: $PROJECT_ID (number: $PROJECT_NUMBER)"

# Get the current region
REGION=$(gcloud config get-value compute/region)
if [ -z "$REGION" ]; then
    REGION="us-central1"  # Default region if not set
fi
echo "Using region: $REGION"

# 1. Create Cloud Storage bucket
echo "Creating Cloud Storage bucket..."
gsutil mb -l $REGION -p $PROJECT_ID gs://fhir-bulk-dumps
check_success "Created bucket: gs://fhir-bulk-dumps"

# Set uniform bucket-level access
echo "Setting uniform bucket-level access..."
gsutil uniformbucketlevelaccess set on gs://fhir-bulk-dumps
check_success "Set uniform bucket-level access"

# 2. Enable Healthcare API
echo "Enabling Healthcare API..."
gcloud services enable healthcare.googleapis.com
check_success "Enabled Healthcare API"

# 3. Create Healthcare dataset
echo "Creating Healthcare dataset..."
gcloud healthcare datasets create ehr_demo \
    --location=$REGION
check_success "Created dataset: ehr_demo"

# 4. Create FHIR store
echo "Creating FHIR store..."
gcloud healthcare fhir-stores create hospital_r4 \
    --dataset=ehr_demo \
    --version=R4 \
    --location=$REGION
check_success "Created FHIR store: hospital_r4"

# 5. Get the Healthcare Service Agent email
HEALTHCARE_SA="service-${PROJECT_NUMBER}@gcp-sa-healthcare.iam.gserviceaccount.com"

# 6. Grant Storage Object Admin role to Healthcare Service Agent
echo "Granting Storage Object Admin role to Healthcare Service Agent..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$HEALTHCARE_SA" \
    --role="roles/storage.objectAdmin"
check_success "Granted Storage Object Admin role"

echo "
✨ GCP Setup Complete! ✨
- Created bucket: gs://fhir-bulk-dumps
- Enabled Healthcare API
- Created dataset: ehr_demo
- Created FHIR store: hospital_r4
- Configured IAM permissions

Next steps:
1. Verify the bucket exists: gsutil ls gs://fhir-bulk-dumps
2. Verify the FHIR store: gcloud healthcare fhir-stores list --dataset=ehr_demo --location=$REGION
" 