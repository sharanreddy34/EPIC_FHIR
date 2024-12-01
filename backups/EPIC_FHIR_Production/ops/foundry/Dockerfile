# Epic FHIR Integration Foundry container image
#
# This image bundles the Epic FHIR Integration Python wheel together with
# Pathling and the HL7 FHIR validator so that Foundry can run any of the
# provided CLI entry-points in a single container.

# ──────────────────────────────────────────────────────────────────────────────
#  Base image – small-ish Java 11 distro which is also compatible with the
#  upstream Pathling + validator JARs. Foundry currently ships Java 17 so
#  running a lower version is safe.
# ──────────────────────────────────────────────────────────────────────────────
FROM eclipse-temurin:11-jre

# Metadata labels
LABEL org.opencontainers.image.source="https://github.com/your-org/epic-fhir-integration"
LABEL org.opencontainers.image.description="Epic FHIR Integration tools (Python \u002b Pathling \u002b HL7 validator)"

# ----------------------------------------------------------------------
# Install Python 3 + pip in a RUN layer so that we can leverage the
# layer cache when rebuilding the image with new wheels.
# ----------------------------------------------------------------------
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl ca-certificates \
    && python3 -m venv /opt/venv \
    && rm -rf /var/lib/apt/lists/*

# Use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# ----------------------------------------------------------------------
# Copy artefacts produced by the build pipeline.
#  • Python wheel goes first so that downstream changes invalidate fewer layers
#  • Pathling and validator directories come from the repo (ADD keeps layers)
# ----------------------------------------------------------------------
# NOTE: The wheel should have been built beforehand via `python -m build` and
#       placed into the `dist/` directory (see CI job).
COPY dist/*.whl /tmp/wheel/
COPY ops/pathling /opt/pathling
COPY ops/validator /opt/validator

# Install the wheel and analytics extras (PySpark, Pathling bindings)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /tmp/wheel/*.whl \
    && pip install --no-cache-dir "epic-fhir-integration[analytics]" \
    && rm -rf /tmp/wheel

# Put validator.sh into PATH for convenience.
RUN ln -s /opt/validator/validator_cli.jar /usr/local/bin/validator.jar \
    && printf "#!/usr/bin/env bash\nexec java -jar /usr/local/bin/validator.jar \"$@\"\n" > /usr/local/bin/validator.sh \
    && chmod +x /usr/local/bin/validator.sh

# Default environment values – can be overridden in Foundry function YAMLs.
ENV DATA_ROOT=/foundry/objects \
    PATHLING_IMPORT_ENABLED=true \
    LOG_LEVEL=INFO

# Expose Pathling HTTP port for health-checks.
EXPOSE 8080

# Add entrypoint script – kept minimal to avoid failure modes.
COPY ops/foundry/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"] 