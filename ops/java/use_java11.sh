#!/bin/bash
# Script to set up and use Java 11 for Pathling and FHIR Validator

# Function to detect OS
detect_os() {
  case "$(uname -s)" in
    Darwin*)  echo "macos" ;;
    Linux*)   echo "linux" ;;
    CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
    *)        echo "unknown" ;;
  esac
}

# Function to check Java version
check_java_version() {
  if command -v java >/dev/null 2>&1; then
    java_version=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}')
    
    # Handle different version formats (1.8 vs 11)
    if [[ $java_version == 1.* ]]; then
      major_version=$(echo $java_version | cut -d. -f2)
    else
      major_version=$(echo $java_version | cut -d. -f1)
    fi
    
    echo "Detected Java version: $java_version (major: $major_version)"
    
    if [ "$major_version" -ge 11 ]; then
      return 0  # Success - Java 11+ detected
    else
      return 1  # Failure - Java version too old
    fi
  else
    echo "Java not found"
    return 2  # Failure - Java not installed
  fi
}

# Main script
os_type=$(detect_os)
echo "Detected OS: $os_type"

# Try to use system Java if it's the right version
if check_java_version; then
  echo "Using system Java (version 11+)"
  return 0
else
  echo "System Java is not version 11+, checking alternatives..."
fi

# Check for platform-specific Java paths
if [ "$os_type" = "macos" ]; then
  # Check Homebrew Java locations
  if [ -d "/opt/homebrew/opt/openjdk@11" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@11"
  elif [ -d "/usr/local/opt/openjdk@11" ]; then
    export JAVA_HOME="/usr/local/opt/openjdk@11"
  # Check macOS Java locations
  elif [ -d "/Library/Java/JavaVirtualMachines" ]; then
    latest_java11=$(find /Library/Java/JavaVirtualMachines -name "jdk-11*" -type d | sort -r | head -n 1)
    if [ -n "$latest_java11" ]; then
      export JAVA_HOME="$latest_java11/Contents/Home"
    fi
  fi
elif [ "$os_type" = "linux" ]; then
  # Common Linux Java 11 locations
  for java_path in \
    "/usr/lib/jvm/java-11-openjdk-amd64" \
    "/usr/lib/jvm/java-11-openjdk" \
    "/usr/lib/jvm/java-11-oracle" \
    "/usr/lib/jvm/temurin-11-jdk" \
    "/opt/jdk-11"
  do
    if [ -d "$java_path" ]; then
      export JAVA_HOME="$java_path"
      break
    fi
  done
fi

# Update PATH if JAVA_HOME was set
if [ -n "$JAVA_HOME" ]; then
  export PATH="$JAVA_HOME/bin:$PATH"
  echo "Using Java from: $JAVA_HOME"
  
  # Verify Java version
  if check_java_version; then
    echo "Successfully configured Java 11+"
    return 0
  else
    echo "Error: Failed to set up Java 11+"
  fi
else
  echo "Error: Could not find Java 11 installation"
  
  # Provide installation instructions
  if [ "$os_type" = "macos" ]; then
    echo "To install Java 11 on macOS, run: brew install openjdk@11"
  elif [ "$os_type" = "linux" ]; then
    echo "To install Java 11 on Ubuntu/Debian, run: sudo apt install openjdk-11-jdk"
    echo "To install Java 11 on CentOS/RHEL, run: sudo yum install java-11-openjdk-devel"
  fi
  
  return 1
fi 