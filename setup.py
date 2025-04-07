#!/bin/bash
# Setup script for Huntarr-Sonarr Web Interface

# Create directories
mkdir -p templates
mkdir -p utils

# Ensure file destinations exist
touch requirements.txt
touch main.py
touch config.py
touch api.py
touch missing.py
touch upgrade.py
touch state.py
touch web_server.py
touch utils/logger.py
touch utils/__init__.py
touch templates/index.html

echo "Directory structure created successfully!"
echo "Please copy the files from the artifacts into the appropriate locations."
echo "Then build the Docker image with: docker build -t huntarr/4sonarr:latest ."

# Reminder about port exposure
echo "Remember to expose port 8988 when running the Docker container:"
echo "docker run -d --name huntarr-sonarr -p 8988:8988 ... huntarr/4sonarr:latest"