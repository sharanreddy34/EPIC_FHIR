#!/bin/bash

# Create the pathling data directory if it doesn't exist
mkdir -p $(pwd)/pathling-data

# Start the Pathling server using Docker Compose
echo "Starting Pathling server..."
docker-compose -f $(pwd)/epic-fhir-integration/docker-compose.pathling.yml up -d

# Wait for the server to be ready
echo "Waiting for Pathling server to be ready..."
attempt=0
max_attempts=10

while [ $attempt -lt $max_attempts ]; do
    if curl -s -f http://localhost:8080/fhir/metadata > /dev/null; then
        echo "Pathling server is ready at http://localhost:8080/fhir"
        exit 0
    fi
    attempt=$((attempt+1))
    sleep 5
    echo "Retrying... ($attempt/$max_attempts)"
done

echo "Failed to start Pathling server within the timeout period."
exit 1 