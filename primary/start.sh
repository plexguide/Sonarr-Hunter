#!/bin/sh
# Startup script for Huntarr with always enabled web UI

# Ensure the configuration directories exist and have proper permissions
mkdir -p /config/settings /config/stateful /config/user
chmod -R 755 /config

# Web UI is always enabled
echo "Starting with Web UI enabled on port 9705"

# Start both the web server and the main application
cd /app
python -m primary.web_server &
python -m primary.main