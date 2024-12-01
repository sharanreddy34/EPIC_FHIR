FROM eclipse-temurin:11-jre
WORKDIR /validator
ADD https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar .
ENTRYPOINT ["java","-jar","/validator/validator_cli.jar"] 