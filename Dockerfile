# Start from a lightweight Python image
FROM python:3.10-slim

COPY ./requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for our script and state files
RUN mkdir -p /app && \
    mkdir -p /tmp/huntarr-radarr-state && \
    mkdir -p /app/data && \
    mkdir -p /config/log && \
    touch /config/log/app.log \
    touch /app/data/processed_upgrade_ids.txt \
    touch /app/data/processed_missing_ids.txt


# Switch working directory
WORKDIR /app

COPY .env /config/.env

# Copy the Python code into the container
COPY . /app

# Make the script executable (optional but good practice)
RUN chmod +x /app/huntarr.py

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

# The script’s entrypoint. It will run your `refresharr.py` when the container starts.
ENTRYPOINT ["python", "refresharr.py"]
