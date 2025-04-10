#!/bin/sh
# Startup script for Huntarr with always enabled web UI

# Ensure the configuration directories exist and have proper permissions
mkdir -p /config/settings /config/stateful /config/user
chmod -R 755 /config

# Detect app type from environment or use sonarr as default
APP_TYPE=${APP_TYPE:-sonarr}
echo "Starting Huntarr in ${APP_TYPE} mode"

# Web UI is always enabled in v4
echo "Starting with Web UI enabled on port 8988"

# Start both the web server and the main application
cd /app
python -m primary.web_server &
python -m primary.main