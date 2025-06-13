# Java Requirements for Pathling

## Overview
[Pathling](https://pathling.csiro.au/) is a FHIR analytics tool developed by the Australian e-Health Research Centre. It requires Java to run since it's built on top of Apache Spark.

## Java Version Requirements

- **Minimum Required**: Java 11 or higher
- **Recommended**: Java 17 LTS
- **Current Environment**: Java 8 (version 1.8.0_451) - *Needs upgrade*

## Setup Process

### 1. Install Java 11+ (macOS)

Using Homebrew:
```bash
brew install openjdk@17
```

Using SDKMAN:
```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 17.0.7-tem
```

### 2. Verify Java Installation
```bash
java -version
```

### 3. Set JAVA_HOME Environment Variable
Add to your shell profile (e.g., ~/.zshrc or ~/.bash_profile):
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH=$JAVA_HOME/bin:$PATH
```

### 4. Containerization Option (Docker)

If upgrading Java is not possible due to other project dependencies, consider using Docker:

```bash
docker run -p 8080:8080 aehrc/pathling:latest
```

## Integration Considerations

- **Dependency Management**: Use Java 11+ compatible dependencies
- **API Access**: Pathling exposes a REST API that can be accessed from Python
- **Memory Settings**: Tune Java memory settings for large datasets:
  ```bash
  export JAVA_OPTS="-Xmx4g -XX:+UseG1GC"
  ```

## Testing the Installation

After setting up Java, validate Pathling installation with:

```python
from jpype import startJVM, JClass, getDefaultJVMPath
import jpype.imports
import os

# Set path to Pathling jar file
pathling_jar = os.path.expanduser("~/pathling-cli.jar")

# Start JVM
startJVM(getDefaultJVMPath(), "-ea", f"-Djava.class.path={pathling_jar}")

# Now you can use Pathling Java classes
FhirContext = JClass("org.hl7.fhir.r4.model.FhirContext")
context = FhirContext.forR4()
print("Pathling FHIR context initialized successfully")
```

## Next Steps

1. Download Pathling JAR files
2. Configure Python environment to interact with Java
3. Create and validate a simple prototype 