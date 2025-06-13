#!/bin/bash
# Setup script for Java environment required for Pathling

# Check current Java version
echo "Checking current Java version..."
java -version

# Required Java version for Pathling
REQUIRED_JAVA_VERSION="11"

# Function to check if Java version meets requirements
check_java_version() {
    java_version=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}')
    major_version=$(echo $java_version | cut -d. -f1)
    
    # Handle Java 1.8 style version strings
    if [ "$major_version" == "1" ]; then
        major_version=$(echo $java_version | cut -d. -f2)
    fi
    
    if [ "$major_version" -lt "$REQUIRED_JAVA_VERSION" ]; then
        return 1
    else
        return 0
    fi
}

# Check if current Java version is sufficient
if check_java_version; then
    echo "Current Java version is sufficient for Pathling (Java $REQUIRED_JAVA_VERSION+ required)."
    exit 0
else
    echo "Java version does not meet requirements. Java $REQUIRED_JAVA_VERSION or higher is required."
    
    # Determine OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "Detected macOS. Install Java using Homebrew:"
        echo "1. Install Homebrew if not already installed:"
        echo '   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        echo "2. Install AdoptOpenJDK 11:"
        echo "   brew tap adoptopenjdk/openjdk"
        echo "   brew install --cask adoptopenjdk11"
        echo "   or"
        echo "   brew install openjdk@11"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Detected Linux. Install Java using package manager:"
        echo "For Ubuntu/Debian:"
        echo "   sudo apt-get update"
        echo "   sudo apt-get install openjdk-11-jdk"
        echo "For CentOS/RHEL/Fedora:"
        echo "   sudo yum install java-11-openjdk-devel"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "Detected Windows. Download and install AdoptOpenJDK 11 from:"
        echo "   https://adoptopenjdk.net/releases.html"
    else
        echo "Unsupported OS. Please install Java 11 or higher manually."
    fi
    
    echo ""
    echo "After installation, verify with: java -version"
    echo "Then update JAVA_HOME environment variable to point to the new Java installation."
    
    # Docker alternative
    echo ""
    echo "Alternatively, you can use Docker to run Pathling. A sample docker-compose.yml file will be created."
    
    # Create a sample docker-compose.yml file
    DOCKER_COMPOSE_FILE="docker-compose.yml"
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        cat > "$DOCKER_COMPOSE_FILE" << 'EOL'
version: '3'

services:
  pathling:
    image: aehrc/pathling:6.3.0
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - JAVA_TOOL_OPTIONS=-Xmx4g
EOL
        echo "Created $DOCKER_COMPOSE_FILE for Pathling."
        echo "Run with: docker-compose up -d"
    else
        echo "$DOCKER_COMPOSE_FILE already exists. Not overwriting."
    fi
    
    exit 1
fi 