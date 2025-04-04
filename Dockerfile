# Start from a lightweight Python image
FROM python:3.10-slim

# Set default environment variables (non-sensitive only!)
# NOTE: We removed API_KEY to avoid the Dockerfile secrets warning
ENV API_URL="http://your-sonarr-address:7878" \
    SEARCH_TYPE="both" \
    MAX_MISSING="1" \
    MAX_UPGRADES="5" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true" \
    MONITORED_ONLY="true" \
    STATE_RESET_INTERVAL_HOURS="168" \
    DEBUG_MODE="false"

# Create a directory for our script and state files
RUN mkdir -p /app && mkdir -p /tmp/huntarr-radarr-state

# Switch working directory
WORKDIR /app

# Install any Python dependencies you need (requests is needed by huntarr.py)
RUN pip install --no-cache-dir requests

# Copy the Python script into the container
COPY huntarr.py /app/huntarr.py

# Make the script executable (optional but good practice)
RUN chmod +x /app/huntarr.py

# The script’s entrypoint. It will run your `huntarr.py` when the container starts.
ENTRYPOINT ["python", "huntarr.py"]
