# Use a lightweight Alpine Linux base image
FROM alpine:latest

# Install bash, curl, and jq
RUN apk add --no-cache bash curl jq

# Set default environment variables
ENV API_KEY="your-api-key" \
    API_URL="http://your-sonarr-address:8989" \
    SEARCH_TYPE="both" \
    MAX_MISSING="10" \
    MAX_UPGRADES="10" \
    SLEEP_DURATION="900" \
    RANDOM_SELECTION="true" \
    MONITORED_ONLY="true" \
    STATE_RESET_INTERVAL_HOURS="24"

# Copy the script into the container (adjust the file name if needed)
COPY sonarr-hunter.sh /usr/local/bin/sonarr-hunter.sh
RUN chmod +x /usr/local/bin/sonarr-hunter.sh

# Set the default command to run the script
ENTRYPOINT ["/usr/local/bin/sonarr-hunter.sh"]
