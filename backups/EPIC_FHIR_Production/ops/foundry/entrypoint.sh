#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Foundry runtime entrypoint for the Epic FHIR Integration image.
#
# 1. Launches Pathling as a background service so that downstream Spark jobs
#    can hit http://localhost:8080 for terminology operations.
# 2. Performs a simple health-check to ensure Pathling is accepting requests.
# 3. Finally execs the CMD passed by Foundry – usually one of the packaged
#    epic-fhir-* CLI tools.
# ---------------------------------------------------------------------------
set -euo pipefail

LOG() { echo "[entrypoint] $*"; }

# Launch Pathling in the background if the import toggle is enabled
if [[ "${PATHLING_IMPORT_ENABLED,,}" == "true" ]]; then
  LOG "Starting Pathling server..."
  /opt/pathling/pathling serve &
  PATHLING_PID=$!

  # Wait until Pathling responds to health checks (timeout after 30s)
  LOG "Waiting for Pathling to be ready..."
  TIMEOUT=30
  READY=false
  
  for i in $(seq 1 $TIMEOUT); do
    if curl -s -f http://localhost:8080/fhir/metadata > /dev/null; then
      READY=true
      break
    fi
    sleep 1
    LOG "Waiting for Pathling... ${i}/${TIMEOUT}s"
  done
  
  if [[ "$READY" == "true" ]]; then
    LOG "✓ Pathling server is ready"
  else
    LOG "⚠ Timed out waiting for Pathling to start. Continuing anyway."
  fi
fi

# Log environment info for debugging
LOG "Python version: $(python --version)"
LOG "Environment: DATA_ROOT=${DATA_ROOT}"
LOG "Command: $*"

# Execute the command passed to the container
exec "$@" 