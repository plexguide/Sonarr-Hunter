#!/bin/sh
# Startup script for Huntarr-Sonarr that conditionally starts the web UI

# Ensure the configuration directories exist and have proper permissions
mkdir -p /config/settings /config/stateful
chmod -R 755 /config

# Convert to lowercase
ENABLE_WEB_UI=$(echo "${ENABLE_WEB_UI:-true}" | tr '[:upper:]' '[:lower:]')

if [ "$ENABLE_WEB_UI" = "true" ]; then
    echo "Starting with Web UI enabled on port 8988"
    # Start both the web server and the main application
    python web_server.py &
    python main.py
else
    echo "Web UI disabled, starting only the main application"
    # Start only the main application
    python main.py
fi