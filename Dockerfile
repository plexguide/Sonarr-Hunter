# Use a lightweight Alpine Linux base image
FROM alpine:latest

# Install required dependencies
RUN apk add --no-cache \
    bash \
    curl \
    jq

# Set default environment variables
ENV API_KEY="your-api-key" \
    API_URL="http://your-sonarr-address:8989" \
    SEARCH_TYPE="both" \
    MAX_MISSING="1" \
    MAX_UPGRADES="5" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true" \
    MONITORED_ONLY="true" \
    STATE_RESET_INTERVAL_HOURS="168" \
    DEBUG_MODE="false"

# Create state directory
RUN mkdir -p /tmp/sonarr-hunter-state

# Copy the script into the container
COPY sonarr-hunter.sh /usr/local/bin/sonarr-hunter.sh

# Make the script executable
RUN chmod +x /usr/local/bin/sonarr-hunter.sh

# Set the default command to run the script
ENTRYPOINT ["/usr/local/bin/sonarr-hunter.sh"]

# Add labels for better container management
LABEL maintainer="PlexGuide" \
      description="Sonarr Hunter - Automates finding missing episodes and quality upgrades" \
      version="5.0" \
      url="https://github.com/plexguide/Sonarr-Hunter"
