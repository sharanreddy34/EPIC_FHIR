FROM ghcr.io/aehrc/pathling:6.3.0
ENV JAVA_OPTS="-Xms1G -Xmx4G"
# Enable import API
RUN sed -i 's#"importEnabled": false#"importEnabled": true#' \
    /opt/pathling/config/application.yaml

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/fhir/metadata || exit 1

EXPOSE 8080 