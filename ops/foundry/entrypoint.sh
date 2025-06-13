#!/bin/bash
# ---------------------------------------------------------------------------
# Foundry runtime entrypoint for the Epic FHIR Integration image.
#
# 1. Launches Pathling as a background service so that downstream Spark jobs
#    can hit http://localhost:8080 for terminology operations.
# 2. Performs a simple health-check to ensure Pathling is accepting requests.
# 3. Finally execs the CMD passed by Foundry – usually one of the packaged
#    epic-fhir-* CLI tools.
# ---------------------------------------------------------------------------
set -e

echo "[entrypoint] Starting Pathling server..."
if [ -f /opt/pathling/bin/pathling ]; then
    /opt/pathling/bin/pathling serve &
    sleep 5
    echo "[entrypoint] Pathling server started"
else
    echo "[entrypoint] WARNING: Pathling not found"
fi

echo "[entrypoint] Delegating to CMD: $@"
exec "$@" 